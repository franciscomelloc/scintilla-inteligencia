-- Indicador: inf_conectividade_ept
-- Recortes: total_estado + rede_estadual
-- Output: pirâmide de 4 tiers (sem internet → banda larga + uso aluno)
--
-- Campos esperados em `escola`: in_internet, in_banda_larga, in_internet_alunos
-- Confirmar nomes pós-GCP — alguns mudaram em ondas pós-2022.

WITH escolas_ept AS (
  SELECT DISTINCT id_escola, ano
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
),

escolas_classificadas AS (
  SELECT
    e.ano,
    e.dependencia_administrativa,
    -- tiers (mutually exclusive, mais alto vence)
    CASE
      WHEN e.in_banda_larga = 1 AND e.in_internet_alunos = 1 THEN 'banda_larga_com_uso_aluno'
      WHEN e.in_banda_larga = 1 THEN 'banda_larga_sem_uso_aluno'
      WHEN e.in_internet = 1 THEN 'internet_basica_sem_banda_larga'
      ELSE 'sem_internet'
    END AS tier
  FROM `basedosdados.br_inep_censo_escolar.escola` e
  JOIN escolas_ept ept USING (id_escola, ano)
)

SELECT
  ano,
  100.0 * COUNT(CASE WHEN tier = 'banda_larga_com_uso_aluno' THEN 1 END) / COUNT(*) AS pct_t1_total,
  100.0 * COUNT(CASE WHEN tier = 'banda_larga_sem_uso_aluno' THEN 1 END) / COUNT(*) AS pct_t2_total,
  100.0 * COUNT(CASE WHEN tier = 'internet_basica_sem_banda_larga' THEN 1 END) / COUNT(*) AS pct_t3_total,
  100.0 * COUNT(CASE WHEN tier = 'sem_internet' THEN 1 END) / COUNT(*) AS pct_t4_total,
  -- mesma estrutura para rede_estadual
  100.0 * COUNT(CASE WHEN dependencia_administrativa = 2 AND tier = 'banda_larga_com_uso_aluno' THEN 1 END) /
    NULLIF(COUNT(CASE WHEN dependencia_administrativa = 2 THEN 1 END), 0) AS pct_t1_estadual,
  100.0 * COUNT(CASE WHEN dependencia_administrativa = 2 AND tier = 'banda_larga_sem_uso_aluno' THEN 1 END) /
    NULLIF(COUNT(CASE WHEN dependencia_administrativa = 2 THEN 1 END), 0) AS pct_t2_estadual,
  100.0 * COUNT(CASE WHEN dependencia_administrativa = 2 AND tier = 'internet_basica_sem_banda_larga' THEN 1 END) /
    NULLIF(COUNT(CASE WHEN dependencia_administrativa = 2 THEN 1 END), 0) AS pct_t3_estadual,
  100.0 * COUNT(CASE WHEN dependencia_administrativa = 2 AND tier = 'sem_internet' THEN 1 END) /
    NULLIF(COUNT(CASE WHEN dependencia_administrativa = 2 THEN 1 END), 0) AS pct_t4_estadual
FROM escolas_classificadas
GROUP BY ano
ORDER BY ano;
