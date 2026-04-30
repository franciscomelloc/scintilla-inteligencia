-- Indicador: mer_renda_jovens_pnad
-- Renda mediana mensal de jovens 18-29 por nível de formação (4 níveis)
-- VD3005 (INT64): mapeamento empírico em PNAD recente:
--   <12 = sem EM completo
--   12  = EM completo
--   13-16 = Superior (incompleto/completo, especialização, mestrado, doutorado)
-- V3007 = '1': concluiu curso técnico de nível médio
-- VD4019: rendimento habitual mensal do trabalho principal

WITH base AS (
  SELECT
    V1028 AS peso,
    VD4019 AS renda,
    CASE
      WHEN VD3005 < 12 THEN 'sem_em'
      WHEN VD3005 = 12 AND V3007 = '1' THEN 'em_tec'
      WHEN VD3005 = 12 AND (V3007 != '1' OR V3007 IS NULL) THEN 'em_reg'
      WHEN VD3005 >= 13 THEN 'superior'
      ELSE 'outro'
    END AS bucket
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = '{UF}'
    AND ano BETWEEN 2021 AND 2025
    AND V2009 BETWEEN 18 AND 29
    AND VD4019 IS NOT NULL
    AND VD4019 > 0
    AND V1028 IS NOT NULL
    AND VD3005 IS NOT NULL
)

SELECT
  bucket,
  APPROX_QUANTILES(renda, 100)[OFFSET(50)] AS mediana_renda,
  AVG(renda) AS media_renda,
  SUM(peso) AS n_ponderado,
  COUNT(*) AS n_amostra
FROM base
WHERE bucket != 'outro'
GROUP BY bucket
ORDER BY bucket;
