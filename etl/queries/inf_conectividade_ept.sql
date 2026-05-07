-- Indicador: inf_conectividade_ept
-- Recortes: total_estado + rede_estadual
-- Output: pirâmide de 4 tiers (sem internet → banda larga + uso aluno)
-- Campos: internet (boolean), banda_larga (boolean), internet_alunos (boolean)

WITH escolas_classificadas AS (
  SELECT
    ano,
    rede,
    CASE
      WHEN banda_larga = 1 AND internet_alunos = 1 THEN 'banda_larga_com_uso_aluno'
      WHEN banda_larga = 1 THEN 'banda_larga_sem_uso_aluno'
      WHEN internet = 1 THEN 'internet_basica_sem_banda_larga'
      ELSE 'sem_internet'
    END AS tier
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE ano BETWEEN 2020 AND 2024
    AND sigla_uf = @uf
    AND COALESCE(quantidade_matricula_medio_tecnico, 0) > 0
)

SELECT
  ano,
  ROUND(100.0 * COUNTIF(tier = 'banda_larga_com_uso_aluno') / NULLIF(COUNT(*), 0), 2) AS pct_t1_total,
  ROUND(100.0 * COUNTIF(tier = 'banda_larga_sem_uso_aluno') / NULLIF(COUNT(*), 0), 2) AS pct_t2_total,
  ROUND(100.0 * COUNTIF(tier = 'internet_basica_sem_banda_larga') / NULLIF(COUNT(*), 0), 2) AS pct_t3_total,
  ROUND(100.0 * COUNTIF(tier = 'sem_internet') / NULLIF(COUNT(*), 0), 2) AS pct_t4_total,
  ROUND(100.0 * COUNTIF(rede = '2' AND tier = 'banda_larga_com_uso_aluno') /
        NULLIF(COUNTIF(rede = '2'), 0), 2) AS pct_t1_estadual,
  ROUND(100.0 * COUNTIF(rede = '2' AND tier = 'banda_larga_sem_uso_aluno') /
        NULLIF(COUNTIF(rede = '2'), 0), 2) AS pct_t2_estadual,
  ROUND(100.0 * COUNTIF(rede = '2' AND tier = 'internet_basica_sem_banda_larga') /
        NULLIF(COUNTIF(rede = '2'), 0), 2) AS pct_t3_estadual,
  ROUND(100.0 * COUNTIF(rede = '2' AND tier = 'sem_internet') /
        NULLIF(COUNTIF(rede = '2'), 0), 2) AS pct_t4_estadual
FROM escolas_classificadas
GROUP BY ano
ORDER BY ano;
