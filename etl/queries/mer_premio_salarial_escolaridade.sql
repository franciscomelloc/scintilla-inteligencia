-- Indicador: mer_premio_salarial_escolaridade
-- Recortes: apenas total_estado
--
-- Mediana salarial em vínculos formais ativos em 31/dez por nível de escolaridade.
-- 3 níveis: sem EM (grau_instrucao ≤ 5), EM completo (=7), Superior completo (≥9).
-- RAIS NÃO distingue EM regular de EM técnico em microdados públicos —
-- o prêmio EPT específico não é mensurável aqui (vira lead-gen).
-- Correção monetária: IPCA pra ano-base = ano mais recente do RAIS.

WITH vinculos_classificados AS (
  SELECT
    ano,
    salario_mensal,
    CASE
      WHEN grau_instrucao_apos_2005 <= 5 THEN 'sem_ensino_medio'
      WHEN grau_instrucao_apos_2005 = 7 THEN 'ensino_medio_completo'
      WHEN grau_instrucao_apos_2005 >= 9 THEN 'superior_completo'
      ELSE NULL
    END AS nivel
  FROM `basedosdados.br_me_rais.microdados_vinculos`
  WHERE ano BETWEEN 2019 AND 2023
    AND sigla_uf = '{UF}'
    AND salario_mensal > 0
    AND vinculo_ativo_em_31_12 = 1
)

SELECT
  ano,
  -- mediana por nível
  PERCENTILE_CONT(salario_mensal, 0.5) OVER (PARTITION BY ano, nivel)
    FILTER (WHERE nivel = 'sem_ensino_medio') AS mediana_sem_em,
  PERCENTILE_CONT(salario_mensal, 0.5) OVER (PARTITION BY ano, nivel)
    FILTER (WHERE nivel = 'ensino_medio_completo') AS mediana_em_completo,
  PERCENTILE_CONT(salario_mensal, 0.5) OVER (PARTITION BY ano, nivel)
    FILTER (WHERE nivel = 'superior_completo') AS mediana_superior
FROM vinculos_classificados
WHERE nivel IS NOT NULL
GROUP BY ano;
