-- Indicador: qua_ingresso_es_pnad
-- % jovens 18-29 com EM completo cursando ES, com EPT (V3007=1) vs sem EPT
-- VD3005: nível instrução concluído (12 = EM completo, 13-16 = Superior incompleto/completo)
-- V3009A: curso atual (12=Superior graduação, 13=Especialização, 14=Mestrado, 15=Doutorado, 16=...)
-- Janela 5 anos (2021-2025) para ter amostra mínima em estados pequenos

WITH base AS (
  SELECT
    V1028 AS peso,
    V2009 AS idade,
    VD3005 AS nivel,
    V3007,
    V3009A,
    CASE
      WHEN V3009A IN ('12','13','14','15','16') THEN 1
      ELSE 0
    END AS em_es,
    CASE WHEN V3007 = '1' THEN 'tec' ELSE 'reg' END AS grupo
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = '{UF}'
    AND ano BETWEEN 2021 AND 2025
    AND V2009 BETWEEN 18 AND 29
    AND V1028 IS NOT NULL
    AND VD3005 >= 12  -- EM completo ou mais
)

SELECT
  grupo,
  SUM(peso * em_es) / NULLIF(SUM(peso), 0) * 100 AS pct_em_es,
  SUM(peso) AS pop_total,
  COUNT(*) AS n_amostra
FROM base
GROUP BY grupo
ORDER BY grupo;
