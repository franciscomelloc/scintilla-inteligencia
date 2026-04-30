"""
Wrapper de execução de queries BigQuery.

Lê SQL versionado em etl/queries/, substitui {UF}, executa via google-cloud-bigquery,
retorna pandas DataFrame. Centraliza tratamento de erro pra que falha em 1 indicador
não derrube o build dos 27 estados.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
QUERIES_DIR = ROOT / "etl" / "queries"


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
    def run(cls, indicator_code: str, uf: str) -> "pd.DataFrame":
        """Executa SQL do indicador para um UF, retorna DataFrame."""
        sql = cls.load_query(indicator_code).replace("{UF}", uf)
        client = cls.get_client()
        logger.debug(f"[{indicator_code}/{uf}] executando query")
        # create_bqstorage_client=False evita exigir bigquery.readsessions.create
        # (mais lento mas suficiente pra volumes desse ETL: <10MB por query)
        df = client.query(sql).result().to_dataframe(create_bqstorage_client=False)
        logger.info(f"[{indicator_code}/{uf}] {len(df)} linhas")
        return df
