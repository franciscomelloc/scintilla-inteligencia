"""
Wrapper de execução de queries BigQuery.

Lê SQL versionado em etl/queries/, parametriza UF via ScalarQueryParameter,
executa via google-cloud-bigquery, retorna pandas DataFrame. Centraliza
tratamento de erro pra que falha em 1 indicador não derrube o build dos 27 estados.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
QUERIES_DIR = ROOT / "etl" / "queries"

# Allowlist UF: 27 siglas dos estados + 'BR' (pseudo-UF agregado nacional).
# Defesa em profundidade: mesmo após migrar pra ScalarQueryParameter, validamos
# antes pra garantir que não passamos string arbitrária a `bigquery.Client.query`.
_UF_RE = re.compile(r"^[A-Z]{2}$")

# Reescreve filtros de UF para agregação nacional. Captura "sigla_uf = @uf"
# com prefixo de alias opcional (e.sigla_uf, i.sigla_uf, d.sigla_uf, s.sigla_uf)
# e substitui por TRUE — preserva a estrutura WHERE/AND da query.
_UF_FILTER_RE = re.compile(r"(?:\w+\.)?sigla_uf\s*=\s*@uf")


class BQRunner:
    """Cliente BQ singleton com cache de queries."""

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            from google.cloud import bigquery

            project = os.environ.get("GCP_BILLING_PROJECT")
            if not project:
                raise RuntimeError("GCP_BILLING_PROJECT env var não definido")
            cls._client = bigquery.Client(project=project)
            logger.info(f"BQ client inicializado em {project}")
        return cls._client

    @classmethod
    def load_query(cls, indicator_code: str) -> str:
        path = QUERIES_DIR / f"{indicator_code}.sql"
        if not path.exists():
            raise FileNotFoundError(f"Query não encontrada: {path}")
        return path.read_text(encoding="utf-8")

    @classmethod
    def run(cls, indicator_code: str, uf: str) -> pd.DataFrame:
        """Executa SQL do indicador para um UF, retorna DataFrame.

        uf == 'BR' dispara modo nacional: o filtro `sigla_uf = @uf` é
        reescrito para `TRUE`, agregando todas as 27 UFs.

        Demais UFs são passadas via `bigquery.ScalarQueryParameter`
        (parametrização nativa do BQ) — evita SQL injection mesmo no caso
        improvável de `uf` vir de fonte não-confiável no futuro.
        """
        if not _UF_RE.fullmatch(uf):
            raise ValueError(f"UF inválida: {uf!r} (esperado [A-Z]{{2}})")

        from google.cloud import bigquery

        raw = cls.load_query(indicator_code)
        client = cls.get_client()
        logger.debug(f"[{indicator_code}/{uf}] executando query")

        if uf == "BR":
            sql = _UF_FILTER_RE.sub("TRUE", raw)
            job_config = bigquery.QueryJobConfig()
        else:
            sql = raw
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("uf", "STRING", uf)]
            )

        # create_bqstorage_client=False evita exigir bigquery.readsessions.create
        # (mais lento mas suficiente pra volumes desse ETL: <10MB por query)
        df = (
            client.query(sql, job_config=job_config)
            .result()
            .to_dataframe(create_bqstorage_client=False)
        )
        logger.info(f"[{indicator_code}/{uf}] {len(df)} linhas")
        return df
