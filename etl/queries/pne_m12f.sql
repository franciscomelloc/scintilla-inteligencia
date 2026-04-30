-- Indicador: pne_m12f
-- PNE Meta 12.f · % da população 18-24 com formação técnica concluída
-- V3007 = '1' significa que o curso de qualificação concluído é técnico de nível médio
-- V1028 = peso amostral; V2007 = sexo (1=M,2=F); V2010 = cor/raça (1 Branca, 2 Preta, 3 Amarela, 4 Parda, 5 Indígena)

WITH base AS (
  SELECT
    ano,
    V1028 AS peso,
    CASE WHEN V3007 = '1' THEN 1 ELSE 0 END AS concluiu_tec,
    V2007 AS sexo,
    V2010 AS raca
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = '{UF}'
    AND ano BETWEEN 2021 AND 2025
    AND V2009 BETWEEN 18 AND 24
    AND V1028 IS NOT NULL
)

SELECT
  ano,
  SUM(peso * concluiu_tec) / NULLIF(SUM(peso), 0) * 100 AS pct_total,
  SUM(IF(sexo='1', peso * concluiu_tec, 0)) / NULLIF(SUM(IF(sexo='1', peso, 0)), 0) * 100 AS pct_homens,
  SUM(IF(sexo='2', peso * concluiu_tec, 0)) / NULLIF(SUM(IF(sexo='2', peso, 0)), 0) * 100 AS pct_mulheres,
  SUM(IF(raca='1', peso * concluiu_tec, 0)) / NULLIF(SUM(IF(raca='1', peso, 0)), 0) * 100 AS pct_brancos,
  SUM(IF(raca IN ('2','4'), peso * concluiu_tec, 0)) / NULLIF(SUM(IF(raca IN ('2','4'), peso, 0)), 0) * 100 AS pct_pretos_pardos,
  SUM(peso) AS pop_18_24_total
FROM base
GROUP BY ano
ORDER BY ano;
