-- Indicador: mer_saldo_caged_tecnicos
-- Recortes: apenas total_estado
-- Filtro: CBO 3xxxx (Técnicos de Nível Médio)
-- Backfill: 2020+ (Novo CAGED via eSocial)
-- A coluna saldo_movimentacao já é positivo (admissão) ou negativo (desligamento) por linha

WITH agg AS (
  SELECT
    ano,
    cbo_2002,
    SUM(saldo_movimentacao) AS saldo
  FROM `basedosdados.br_me_caged.microdados_movimentacao`
  WHERE ano BETWEEN 2020 AND 2026
    AND sigla_uf = '{UF}'
    AND cbo_2002 LIKE '3%'
  GROUP BY ano, cbo_2002
)

SELECT
  ano,
  SUM(saldo) AS saldo_12m,
  ARRAY_AGG(
    STRUCT(cbo_2002 AS cbo, saldo)
    ORDER BY ABS(saldo) DESC LIMIT 3
  ) AS top_3_subfamilias
FROM agg
GROUP BY ano
ORDER BY ano;
