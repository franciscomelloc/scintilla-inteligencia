"""
Discovery script — confirma valores reais em colunas categóricas.

Uso: GCP_BILLING_PROJECT=... uv run python -m etl.diagnose
Saída: output/diagnose_report.json
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

DISCOVERY_QUERIES = {
    "censo_escola_rede_values_2024": """
        SELECT rede, COUNT(*) AS n
        FROM `basedosdados.br_inep_censo_escolar.escola`
        WHERE ano = 2024 AND sigla_uf = 'MG'
        GROUP BY rede ORDER BY n DESC
    """,
    "censo_matricula_anos_disponiveis": """
        SELECT ano, COUNT(*) AS n
        FROM `basedosdados.br_inep_censo_escolar.matricula`
        WHERE sigla_uf = 'MG'
        GROUP BY ano ORDER BY ano DESC LIMIT 10
    """,
    "censo_escola_anos_disponiveis": """
        SELECT ano, COUNT(*) AS n
        FROM `basedosdados.br_inep_censo_escolar.escola`
        WHERE sigla_uf = 'MG'
        GROUP BY ano ORDER BY ano DESC LIMIT 10
    """,
    "matricula_etapa_ensino_ept": """
        SELECT etapa_ensino, COUNT(*) AS n
        FROM `basedosdados.br_inep_censo_escolar.matricula`
        WHERE sigla_uf = 'MG' AND ano = 2023
          AND id_curso_educ_profissional IS NOT NULL
        GROUP BY etapa_ensino ORDER BY n DESC
    """,
    "pnad_v3002_values": """
        SELECT V3002, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE sigla_uf = 'MG' AND ano = 2024 AND V2009 BETWEEN 15 AND 29
        GROUP BY V3002 ORDER BY n DESC
    """,
    "pnad_vd4002_values": """
        SELECT VD4002, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE sigla_uf = 'MG' AND ano = 2024 AND V2009 BETWEEN 15 AND 29
        GROUP BY VD4002 ORDER BY n DESC
    """,
    "ideb_ensino_values": """
        SELECT ensino, anos_escolares, COUNT(*) AS n
        FROM `basedosdados.br_inep_ideb.escola`
        WHERE sigla_uf = 'MG' AND ano = 2023
        GROUP BY ensino, anos_escolares ORDER BY n DESC
    """,
    "indicadores_educacionais_anos": """
        SELECT ano, COUNT(*) AS n
        FROM `basedosdados.br_inep_indicadores_educacionais.escola`
        GROUP BY ano ORDER BY ano DESC LIMIT 10
    """,
    "rais_grau_instrucao_values": """
        SELECT grau_instrucao_apos_2005, COUNT(*) AS n
        FROM `basedosdados.br_me_rais.microdados_vinculos`
        WHERE sigla_uf = 'MG' AND ano = 2023
        GROUP BY grau_instrucao_apos_2005 ORDER BY n DESC LIMIT 15
    """,
    "rais_vinculo_ativo_3112": """
        SELECT vinculo_ativo_3112, COUNT(*) AS n
        FROM `basedosdados.br_me_rais.microdados_vinculos`
        WHERE sigla_uf = 'MG' AND ano = 2023
        GROUP BY vinculo_ativo_3112 ORDER BY n DESC
    """,
    "pnad_v3009a_18_20_2024_2025": """
        SELECT ano, V3009A, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano IN (2024, 2025) AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
        GROUP BY ano, V3009A ORDER BY ano DESC, n DESC LIMIT 30
    """,
    "pnad_vd3004_18_20_2024_2025": """
        SELECT ano, VD3004, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano IN (2024, 2025) AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
        GROUP BY ano, VD3004 ORDER BY ano DESC, n DESC LIMIT 30
    """,
    "pnad_vd4007_18_20_2024_2025": """
        SELECT ano, VD4007, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano IN (2024, 2025) AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
        GROUP BY ano, VD4007 ORDER BY ano DESC, n DESC LIMIT 30
    """,
    "pnad_v3002_v3009a_vd3004_cross_18_20": """
        SELECT V3002, V3009A, VD3004, COUNT(*) AS n,
               SUM(V1028) AS pop_ponderada
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
          AND V3009A IN ('10', '11', '12', '13')
        GROUP BY V3002, V3009A, VD3004
        ORDER BY n DESC LIMIT 30
    """,
}


def main() -> int:
    project = os.environ.get("GCP_BILLING_PROJECT")
    if not project:
        logger.error("GCP_BILLING_PROJECT env var não definido")
        return 1

    from google.cloud import bigquery

    client = bigquery.Client(project=project)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}

    for name, sql in DISCOVERY_QUERIES.items():
        logger.info(f"running {name}")
        try:
            df = client.query(sql).result().to_dataframe(create_bqstorage_client=False)
            report[name] = df.to_dict(orient="records")
        except Exception as e:
            logger.error(f"{name} failed: {e}")
            report[name] = {"error": str(e)[:500]}

    out = OUTPUT_DIR / "diagnose_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    logger.info(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
