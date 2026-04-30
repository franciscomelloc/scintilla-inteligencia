-- Indicador: mer_saldo_caged_tecnicos
-- Recortes: apenas total_estado (mercado de trabalho não tem rede)
-- Filtro: CBO 3xxxx (Técnicos de Nível Médio) — definição canônica da CBO 2002
-- Janela: 12 meses rolantes terminando no mês mais recente disponível
-- Backfill: começa em 2020 (Novo CAGED via eSocial)

WITH movimentacao AS (
  SELECT
    EXTRACT(YEAR FROM data_admissao_desligamento) AS ano,
    cbo_2002,
    SUM(CASE WHEN tipo_movimentacao = 'admissao' THEN 1 ELSE -1 END) AS saldo
  FROM `basedosdados.br_me_caged.microdados_movimentacao`
  WHERE EXTRACT(YEAR FROM data_admissao_desligamento) BETWEEN 2020 AND 2026
    AND sigla_uf = '{UF}'
    AND CAST(cbo_2002 AS STRING) LIKE '3%'  -- família 3xxxx
  GROUP BY ano, cbo_2002
)

SELECT
  ano,
  SUM(saldo) AS saldo_12m_total,
  -- top 3 subfamílias CBO 3xxxx por contribuição absoluta ao saldo
  ARRAY_AGG(
    STRUCT(cbo_2002 AS cbo, saldo)
    ORDER BY ABS(saldo) DESC LIMIT 3
  ) AS top_3_subfamilias
FROM movimentacao
GROUP BY ano
ORDER BY ano;
