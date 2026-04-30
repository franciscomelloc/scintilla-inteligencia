-- Indicador: mer_premio_salarial_escolaridade
-- Recortes: apenas total_estado
-- Mediana salarial RAIS por nível de escolaridade (3 níveis).
-- Caveat: RAIS não distingue EM regular de EM técnico → prêmio EPT específico vira lead-gen.
-- Codes grau_instrucao_apos_2005 (RAIS): 01=Analfabeto..06=Médio incompleto, 07=Médio completo,
-- 08=Superior incompleto..11=Doutorado.
-- Mediana via APPROX_QUANTILES (BQ standard).

WITH vinculos AS (
  SELECT
    ano,
    valor_remuneracao_media,
    CASE
      WHEN grau_instrucao_apos_2005 IN ('1','2','3','4','5','6') THEN 'sem_em'
      WHEN grau_instrucao_apos_2005 = '7' THEN 'em_completo'
      WHEN grau_instrucao_apos_2005 IN ('8','9','10','11') THEN 'superior'
      ELSE NULL
    END AS nivel
  FROM `basedosdados.br_me_rais.microdados_vinculos`
  WHERE ano BETWEEN 2019 AND 2023
    AND sigla_uf = '{UF}'
    AND valor_remuneracao_media > 0
    AND vinculo_ativo_3112 = '1'
)

SELECT
  ano,
  APPROX_QUANTILES(IF(nivel = 'sem_em', valor_remuneracao_media, NULL), 100 IGNORE NULLS)[OFFSET(50)] AS mediana_sem_em,
  APPROX_QUANTILES(IF(nivel = 'em_completo', valor_remuneracao_media, NULL), 100 IGNORE NULLS)[OFFSET(50)] AS mediana_em_completo,
  APPROX_QUANTILES(IF(nivel = 'superior', valor_remuneracao_media, NULL), 100 IGNORE NULLS)[OFFSET(50)] AS mediana_superior,
  COUNTIF(nivel = 'sem_em') AS n_sem_em,
  COUNTIF(nivel = 'em_completo') AS n_em_completo,
  COUNTIF(nivel = 'superior') AS n_superior
FROM vinculos
WHERE nivel IS NOT NULL
GROUP BY ano
ORDER BY ano;
