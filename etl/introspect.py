"""
Introspecção de schema das tabelas Base dos Dados que vamos usar.

Lista nomes de coluna via INFORMATION_SCHEMA pra calibrar SQLs depois.
Saída: output/bd_schema_report.json com colunas + tipos por tabela.

Uso: uv run python etl/introspect.py
Requer: GCP_BILLING_PROJECT no env + auth GCP via gcloud ou GOOGLE_APPLICATION_CREDENTIALS.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"

TABLES_TO_INSPECT = [
    ("basedosdados", "br_inep_censo_escolar", "matricula"),
    ("basedosdados", "br_inep_censo_escolar", "escola"),
    ("basedosdados", "br_inep_censo_escolar", "docente"),
    ("basedosdados", "br_inep_indicadores_educacionais", "escola"),
    ("basedosdados", "br_inep_ideb", "escola"),
    ("basedosdados", "br_me_caged", "microdados_movimentacao"),
    ("basedosdados", "br_me_rais", "microdados_vinculos"),
    ("basedosdados", "br_ibge_pnadc", "microdados"),
    ("basedosdados", "br_bd_diretorios_brasil", "municipio"),
]


def fetch_columns(client, project: str, dataset: str, table: str) -> list[dict[str, Any]]:
    """Consulta INFORMATION_SCHEMA.COLUMNS pra uma tabela específica."""
    query = f"""
    SELECT column_name, data_type, is_partitioning_column, ordinal_position
    FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{table}'
    ORDER BY ordinal_position
    """
    try:
        rows = list(client.query(query).result())
        return [
            {
                "name": row.column_name,
                "type": row.data_type,
                "partition": row.is_partitioning_column == "YES",
                "position": row.ordinal_position,
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"falha em {project}.{dataset}.{table}: {e}")
        return [{"error": str(e)}]


def main() -> int:
    billing = os.environ.get("GCP_BILLING_PROJECT")
    if not billing:
        logger.error("GCP_BILLING_PROJECT não definido no env")
        return 1

    try:
        from google.cloud import bigquery
    except ImportError:
        logger.error("google-cloud-bigquery não instalado. Rode: uv add google-cloud-bigquery")
        return 1

    client = bigquery.Client(project=billing)
    logger.info(f"Cliente BQ inicializado com billing project: {billing}")

    report: dict[str, Any] = {
        "billing_project": billing,
        "tables": {},
    }

    for project, dataset, table in TABLES_TO_INSPECT:
        full_name = f"{project}.{dataset}.{table}"
        logger.info(f"Introspecting {full_name}")
        cols = fetch_columns(client, project, dataset, table)
        report["tables"][full_name] = cols

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "bd_schema_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Relatório salvo em {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
