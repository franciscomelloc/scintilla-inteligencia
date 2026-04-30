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
    ("basedosdados", "br_inep_saeb", "escola"),
    ("basedosdados", "br_inep_enem", "microdados"),
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

    # Discovery: existe SISTEC ou Plataforma Nilo Peçanha em algum dataset BD?
    logger.info("Discovery: SISTEC / Nilo Peçanha / qualificação na BD")
    discovery_query = """
    SELECT schema_name
    FROM `basedosdados.INFORMATION_SCHEMA.SCHEMATA`
    WHERE LOWER(schema_name) LIKE '%mec%'
       OR LOWER(schema_name) LIKE '%setec%'
       OR LOWER(schema_name) LIKE '%inep%'
       OR LOWER(schema_name) LIKE '%educacao%'
       OR LOWER(schema_name) LIKE '%educac%'
    ORDER BY schema_name
    """
    try:
        schemas = [row.schema_name for row in client.query(discovery_query).result()]
        report["education_schemas"] = schemas
        logger.info(f"Schemas educacionais encontrados: {schemas}")

        # Pra cada schema potencial, listar tabelas que possam conter SISTEC/PNP/qualificação
        sistec_hits = []
        for schema in schemas:
            try:
                tbl_query = f"""
                SELECT table_name
                FROM `basedosdados.{schema}.INFORMATION_SCHEMA.TABLES`
                ORDER BY table_name
                """
                tables = [row.table_name for row in client.query(tbl_query).result()]
                report[f"tables_in_{schema}"] = tables
                for t in tables:
                    if any(k in t.lower() for k in ["sistec", "pec", "nilo", "qualif", "fic", "subsequ", "pronatec", "setec"]):
                        sistec_hits.append(f"{schema}.{t}")
            except Exception as e:
                report[f"tables_in_{schema}"] = {"error": str(e)}
        report["sistec_pnp_hits"] = sistec_hits
        logger.info(f"Hits SISTEC/PNP/qualif/FIC: {sistec_hits}")
    except Exception as e:
        logger.error(f"Discovery falhou: {e}")
        report["discovery_error"] = str(e)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "bd_schema_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Relatório salvo em {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
