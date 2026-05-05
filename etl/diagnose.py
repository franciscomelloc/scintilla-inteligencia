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
    "pnad_v3001_v3002_v3003_v3009A_18_20": """
        SELECT V3001, V3002, V3003, V3009A, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
        GROUP BY V3001, V3002, V3003, V3009A
        ORDER BY n DESC LIMIT 30
    """,
    "pnad_v3002_eq_1_breakdown": """
        SELECT V3002, V3003, V3009, V3009A, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V3002 = '1'
        GROUP BY V3002, V3003, V3009, V3009A
        ORDER BY n DESC LIMIT 20
    """,
    "pnad_vd4002_vd4007_v4009_full_18_20": """
        SELECT VD4002, VD4007, V4009, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
        GROUP BY VD4002, VD4007, V4009
        ORDER BY n DESC LIMIT 50
    """,
    "pnad_v4019_v4012_v4029_18_20": """
        SELECT V4019, V4012, V4029, V4032, COUNT(*) AS n
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND VD4002 = '1'
        GROUP BY V4019, V4012, V4029, V4032
        ORDER BY n DESC LIMIT 30
    """,
    # Sanity check: pop ponderada total 18-20 BR vs subset com EM completo
    # vs subset cursando superior. Permite comparar com benchmarks INEP/PNAD.
    "pnad_base_size_18_20_2025_br": """
        SELECT
          'todos_18_20' AS recorte, COUNT(*) AS n,
          SUM(V1028) AS pop
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
        UNION ALL
        SELECT
          'com_em_completo' AS recorte, COUNT(*) AS n,
          SUM(V1028) AS pop
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
          AND VD3004 IN ('5','6','7')
        UNION ALL
        SELECT
          'cursando_superior' AS recorte, COUNT(*) AS n,
          SUM(V1028) AS pop
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
          AND V3002 = '2' AND V3009A IN ('10','11','12','13')
    """,
    # Tenta variáveis V3003A, V3002A pra encontrar curso ATUAL quando
    # V3002='1'. Diagnose anterior mostrou V3009A SEMPRE null com V3002=1.
    "pnad_v3003a_18_20_v3002_1": """
        SELECT V3003A, COUNT(*) AS n, SUM(V1028) AS pop
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V3002 = '1' AND V1028 IS NOT NULL
        GROUP BY V3003A ORDER BY n DESC LIMIT 30
    """,
    # Inspeciona schema completo: lista todas colunas na tabela
    "pnad_columns_with_v300_v301": """
        SELECT column_name
        FROM `basedosdados.br_ibge_pnadc.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = 'microdados'
          AND (column_name LIKE 'V300%' OR column_name LIKE 'V301%' OR column_name LIKE 'VD30%')
        ORDER BY column_name
    """,
    # Confirma população absoluta cursando vs concluído vs nunca:
    # Brasil 18-20 deve ter ~9M pessoas. Taxa líquida superior 18-24=25%.
    # Se >35% aparece como "cursando", semântica está errada.
    "pnad_v3002_1_taxa_freq": """
        SELECT V2009, COUNT(*) AS n, SUM(V1028) AS pop_pond,
          SUM(IF(V3002='1', V1028, 0)) AS pop_freq,
          SUM(IF(V3002='2', V1028, 0)) AS pop_nfreq
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
        GROUP BY V2009 ORDER BY V2009
    """,
    # Enumera códigos distintos id_curso_educ_profissional na BD (último
    # ano disponível = 2020, BD não importou 2021+). Permite avaliar se
    # mapping manual é viável (~250 = tratável).
    "censo_id_curso_distinct_2020": """
        SELECT id_curso_educ_profissional, COUNT(*) AS n_matriculas
        FROM `basedosdados.br_inep_censo_escolar.matricula`
        WHERE ano = 2020
          AND id_curso_educ_profissional IS NOT NULL
        GROUP BY id_curso_educ_profissional
        ORDER BY n_matriculas DESC
    """,
    # Inspeciona se BD tem diretório oficial id_curso_educ_profissional →
    # eixo tecnológico. Se sim, evita popular CSV manual.
    "censo_curso_educ_profissional_columns": """
        SELECT table_name, column_name
        FROM `basedosdados.br_inep_censo_escolar.INFORMATION_SCHEMA.COLUMNS`
        WHERE LOWER(column_name) LIKE '%eixo%'
           OR LOWER(column_name) LIKE '%curso_educ%'
           OR LOWER(table_name) LIKE '%curso%'
        ORDER BY table_name, column_name
    """,
    # Verifica se há tabela diretório curso → eixo na BD
    "bd_diretorios_cnct": """
        SELECT table_name
        FROM `basedosdados.br_bd_diretorios_brasil.INFORMATION_SCHEMA.TABLES`
        WHERE LOWER(table_name) LIKE '%cnct%'
           OR LOWER(table_name) LIKE '%curso_tec%'
           OR LOWER(table_name) LIKE '%eixo%'
    """,
    # Re-check anos disponíveis Censo Escolar — BD pode ter sido atualizada.
    "censo_matricula_anos_full_2025": """
        SELECT ano, COUNT(*) AS n_matriculas,
               SUM(IF(id_curso_educ_profissional IS NOT NULL, 1, 0)) AS n_ept
        FROM `basedosdados.br_inep_censo_escolar.matricula`
        GROUP BY ano ORDER BY ano DESC LIMIT 15
    """,
    # CBO 84xxxx (trabalhadores indústria alimentícia/bebidas) MG —
    # potencial mapping pra Eixo 9 Produção Alimentícia. Top por
    # admissões pra ver volumes reais.
    "caged_cbo84_mg_top": """
        SELECT cbo_2002, COUNTIF(saldo_movimentacao > 0) AS n_admissoes,
               SUM(saldo_movimentacao) AS saldo_12m
        FROM `basedosdados.br_me_caged.microdados_movimentacao`
        WHERE sigla_uf = 'MG'
          AND ano = (SELECT MAX(ano) FROM `basedosdados.br_me_caged.microdados_movimentacao`)
          AND cbo_2002 IS NOT NULL
          AND (cbo_2002 LIKE '84%' OR cbo_2002 LIKE '76%')
        GROUP BY cbo_2002
        HAVING n_admissoes >= 100
        ORDER BY n_admissoes DESC
        LIMIT 20
    """,
    # CBO 5xxxx em MG — cuidadores, atendentes (potencial Eixo 2 Educ/Social)
    "caged_cbo5_mg_top": """
        SELECT cbo_2002, COUNTIF(saldo_movimentacao > 0) AS n_admissoes,
               SUM(saldo_movimentacao) AS saldo_12m
        FROM `basedosdados.br_me_caged.microdados_movimentacao`
        WHERE sigla_uf = 'MG'
          AND ano = (SELECT MAX(ano) FROM `basedosdados.br_me_caged.microdados_movimentacao`)
          AND cbo_2002 IS NOT NULL
          AND (cbo_2002 LIKE '514%' OR cbo_2002 LIKE '516%' OR cbo_2002 LIKE '517%')
        GROUP BY cbo_2002
        HAVING n_admissoes >= 100
        ORDER BY n_admissoes DESC
        LIMIT 20
    """,
    # Red team aderência: top cursos EPT MG 2020 por matrícula. Valida
    # se Eixo 3 > Eixo 4 em MG é real ou contaminação do mapping.
    "censo_top_cursos_mg_2020": """
        SELECT id_curso_educ_profissional AS id_curso,
               DIV(SAFE_CAST(id_curso_educ_profissional AS INT64), 1000) AS eixo_id,
               COUNT(*) AS n_matriculas
        FROM `basedosdados.br_inep_censo_escolar.matricula`
        WHERE ano = 2020
          AND sigla_uf = 'MG'
          AND id_curso_educ_profissional IS NOT NULL
        GROUP BY id_curso, eixo_id
        ORDER BY n_matriculas DESC
        LIMIT 30
    """,
    # Sanity: oferta agregada por eixo MG 2020 vs cob_eixos_cobertos
    # já em prod (mesmo Censo). Bate?
    "censo_eixos_mg_2020_agg": """
        SELECT DIV(SAFE_CAST(id_curso_educ_profissional AS INT64), 1000) AS eixo_id,
               COUNT(*) AS n
        FROM `basedosdados.br_inep_censo_escolar.matricula`
        WHERE ano = 2020 AND sigla_uf = 'MG'
          AND id_curso_educ_profissional IS NOT NULL
        GROUP BY eixo_id ORDER BY eixo_id
    """,
    # Top CBO 3xxxx MG por ADMISSÕES (não saldo) — proxy alternativo
    # de demanda. Ver se ranking muda.
    "caged_cbo3_mg_admissoes_top": """
        SELECT cbo_2002, COUNTIF(saldo_movimentacao > 0) AS n_admissoes,
               SUM(saldo_movimentacao) AS saldo_12m
        FROM `basedosdados.br_me_caged.microdados_movimentacao`
        WHERE sigla_uf = 'MG'
          AND ano = (SELECT MAX(ano) FROM `basedosdados.br_me_caged.microdados_movimentacao`)
          AND cbo_2002 IS NOT NULL AND cbo_2002 LIKE '3%'
          AND cbo_2002 NOT LIKE '33%'
        GROUP BY cbo_2002
        HAVING n_admissoes >= 100
        ORDER BY n_admissoes DESC
        LIMIT 30
    """,
    # Top 30 CBO 3xxxx BR por saldo CAGED + descrição. Permite revisar
    # caso a caso quais excluir como "não-EPT" (professores leigos,
    # auxiliares escolares, atletas, etc).
    "caged_cbo3_top30_br": """
        WITH base AS (
          SELECT cbo_2002, SUM(saldo_movimentacao) AS saldo_12m,
                 COUNTIF(saldo_movimentacao > 0) AS n_admissoes
          FROM `basedosdados.br_me_caged.microdados_movimentacao`
          WHERE ano = (SELECT MAX(ano) FROM `basedosdados.br_me_caged.microdados_movimentacao`)
            AND cbo_2002 IS NOT NULL AND cbo_2002 LIKE '3%'
          GROUP BY cbo_2002
        )
        SELECT b.cbo_2002, c.descricao, b.saldo_12m, b.n_admissoes
        FROM base b
        LEFT JOIN `basedosdados.br_bd_diretorios_brasil.cbo_2002` c
          ON b.cbo_2002 = c.cbo_2002
        ORDER BY ABS(b.saldo_12m) DESC
        LIMIT 30
    """,
    # Cross V3009A x VD3004 sem filtro de base. Verifica se V3009A='10'
    # aparece com VD3004 que NÃO seja '5','6','7' (e.g. EM incompleto)
    # — caso afirmativo, sugere que V3009A captura "ever attended" e
    # pessoa pode ter abandonado EM ainda em superior. Improvável mas
    # worth checking.
    "pnad_v3009a_vd3004_sem_base_18_20": """
        SELECT V3002, V3009A, VD3004, COUNT(*) AS n,
               SUM(V1028) AS pop
        FROM `basedosdados.br_ibge_pnadc.microdados`
        WHERE ano = 2025 AND trimestre = 1 AND V2009 BETWEEN 18 AND 20
          AND V1028 IS NOT NULL
        GROUP BY V3002, V3009A, VD3004
        ORDER BY n DESC LIMIT 50
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
