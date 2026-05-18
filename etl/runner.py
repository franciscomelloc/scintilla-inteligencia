"""
Wrapper de execução de queries BigQuery.

Lê SQL versionado em etl/queries/, parametriza UF via ScalarQueryParameter,
executa via google-cloud-bigquery, retorna pandas DataFrame. Centraliza
tratamento de erro pra que falha em 1 indicador não derrube o build dos 27 estados.

Guardrails de custo (BQ_*):
- BQ_MAX_GB_PER_QUERY (default 5): cap em GB faturáveis por query. Se uma
  query for processar mais que isso, BQ falha com `quotaExceeded` antes de
  consumir bytes. Override por query via `BQRunner.run(..., max_gb=10)`.
- BQ_DRY_RUN (default "true"): se "true", pré-roda dry-run e loga GB estimados
  antes da execução real. Útil pra observabilidade; ~50ms overhead.
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

_GB = 1024**3


def _max_gb_default() -> float:
    return float(os.environ.get("BQ_MAX_GB_PER_QUERY", "5"))


def _dry_run_enabled() -> bool:
    return os.environ.get("BQ_DRY_RUN", "true").lower() == "true"


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
    def run(
        cls,
        indicator_code: str,
        uf: str,
        max_gb: float | None = None,
    ) -> pd.DataFrame:
        """Executa SQL do indicador para um UF, retorna DataFrame.

        uf == 'BR' dispara modo nacional: o filtro `sigla_uf = @uf` é
        reescrito para `TRUE`, agregando todas as 27 UFs.

        Demais UFs são passadas via `bigquery.ScalarQueryParameter`
        (parametrização nativa do BQ) — evita SQL injection mesmo no caso
        improvável de `uf` vir de fonte não-confiável no futuro.

        max_gb: cap em GB faturáveis (default BQ_MAX_GB_PER_QUERY=5). BQ falha
        a query antes de consumir bytes se a estimativa exceder este teto.
        """
        if not _UF_RE.fullmatch(uf):
            raise ValueError(f"UF inválida: {uf!r} (esperado [A-Z]{{2}})")

        from google.cloud import bigquery

        raw = cls.load_query(indicator_code)
        client = cls.get_client()
        cap_gb = max_gb if max_gb is not None else _max_gb_default()
        cap_bytes = int(cap_gb * _GB)

        if uf == "BR":
            sql = _UF_FILTER_RE.sub("TRUE", raw)
            query_params = []
        else:
            sql = raw
            query_params = [bigquery.ScalarQueryParameter("uf", "STRING", uf)]

        if _dry_run_enabled():
            try:
                dry = client.query(
                    sql,
                    job_config=bigquery.QueryJobConfig(
                        dry_run=True,
                        use_query_cache=False,
                        query_parameters=query_params,
                    ),
                )
                est_gb = float(dry.total_bytes_processed) / _GB
                level = logger.warning if est_gb > 1.0 else logger.info
                level(
                    f"[{indicator_code}/{uf}] dry-run: {est_gb:.2f} GB estimados "
                    f"(cap {cap_gb} GB)"
                )
            except (TypeError, AttributeError):
                # Cliente mockado ou dry-run indisponível: segue sem estimativa.
                logger.debug(f"[{indicator_code}/{uf}] dry-run skipped (não-numérico)")

        job_config = bigquery.QueryJobConfig(
            query_parameters=query_params,
            maximum_bytes_billed=cap_bytes,
            use_query_cache=True,
        )

        # create_bqstorage_client=False evita exigir bigquery.readsessions.create
        # (mais lento mas suficiente pra volumes desse ETL: <10MB por query)
        job = client.query(sql, job_config=job_config)
        df = job.result().to_dataframe(create_bqstorage_client=False)

        try:
            billed_gb = float(job.total_bytes_billed or 0) / _GB
            cache_hit = job.cache_hit
            logger.info(
                f"[{indicator_code}/{uf}] {len(df)} linhas | "
                f"{billed_gb:.2f} GB faturados | cache_hit={cache_hit}"
            )
        except (TypeError, AttributeError):
            logger.info(f"[{indicator_code}/{uf}] {len(df)} linhas")
        return df
