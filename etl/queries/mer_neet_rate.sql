-- Indicador: mer_neet_rate
-- Recortes: apenas total_estado
-- Polaridade: INVERSA (NEET menor é melhor)
-- PNAD Contínua código:
--   V2009 = idade
--   V2007 = sexo (1=Homem, 2=Mulher)
--   V3002 = frequenta escola (1=Sim, 2=Não)
--   VD4002 = condição de ocupação (1=Ocupado, 2=Desocupado)
--   VD4001 = condição força trabalho (1=PEA, 2=PNEA)
--   V1028 = peso pessoal pós-estratificado
-- NEET = (não frequenta escola) AND (não está ocupado)
-- Janela: média anual (4 trimestres) pra reduzir ruído.

WITH pnad AS (
  SELECT
    ano,
    V2009 AS idade,
    V2007 AS sexo,
    V1028 AS peso,
    CASE
      WHEN COALESCE(V3002, '0') != '1' AND COALESCE(VD4002, '0') != '1' THEN 1
      ELSE 0
    END AS neet,
    CASE
      WHEN COALESCE(V3002, '0') != '1' AND VD4001 = '1' AND COALESCE(VD4002, '0') != '1' THEN 1
      ELSE 0
    END AS neet_buscando
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE ano BETWEEN 2020 AND 2025
    AND V2009 BETWEEN 15 AND 29
    AND sigla_uf = '{UF}'
    AND V1028 IS NOT NULL
)

SELECT
  ano,
  ROUND(100.0 * SUM(neet * peso) / NULLIF(SUM(peso), 0), 2) AS neet_rate_total,
  ROUND(100.0 * SUM(IF(idade BETWEEN 15 AND 17, neet * peso, 0)) /
        NULLIF(SUM(IF(idade BETWEEN 15 AND 17, peso, 0)), 0), 2) AS neet_15_17,
  ROUND(100.0 * SUM(IF(idade BETWEEN 18 AND 24, neet * peso, 0)) /
        NULLIF(SUM(IF(idade BETWEEN 18 AND 24, peso, 0)), 0), 2) AS neet_18_24,
  ROUND(100.0 * SUM(IF(idade BETWEEN 25 AND 29, neet * peso, 0)) /
        NULLIF(SUM(IF(idade BETWEEN 25 AND 29, peso, 0)), 0), 2) AS neet_25_29,
  ROUND(100.0 * SUM(IF(sexo = '1', neet * peso, 0)) /
        NULLIF(SUM(IF(sexo = '1', peso, 0)), 0), 2) AS neet_homens,
  ROUND(100.0 * SUM(IF(sexo = '2', neet * peso, 0)) /
        NULLIF(SUM(IF(sexo = '2', peso, 0)), 0), 2) AS neet_mulheres,
  ROUND(100.0 * SUM(neet_buscando * peso) / NULLIF(SUM(neet * peso), 0), 2) AS pct_buscando,
  ROUND(100.0 * SUM((neet - neet_buscando) * peso) / NULLIF(SUM(neet * peso), 0), 2) AS pct_inativos
FROM pnad
GROUP BY ano
ORDER BY ano;
