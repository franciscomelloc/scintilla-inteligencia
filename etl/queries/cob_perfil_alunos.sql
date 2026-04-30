-- Indicador: cob_perfil_alunos
-- Perfil dos matriculados em EPT — faixa etária, sexo (matricula) + modalidade (escola).
-- Usa dois CTEs independentes — eles podem cobrir anos diferentes (matricula vai até 2020, escola até 2024).

WITH ept_matricula AS (
  SELECT
    ano,
    idade,
    sexo
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE sigla_uf = '{UF}'
    AND ano = (
      SELECT MAX(ano)
      FROM `basedosdados.br_inep_censo_escolar.matricula`
      WHERE sigla_uf = '{UF}'
        AND id_curso_educ_profissional IS NOT NULL
    )
    AND id_curso_educ_profissional IS NOT NULL
),

modalidade AS (
  SELECT
    ano,
    SUM(COALESCE(quantidade_matricula_medio_tecnico, 0)) AS qtd_integrada,
    SUM(COALESCE(quantidade_matricula_profissional_tecnica_concomitante, 0)) AS qtd_concomitante,
    SUM(COALESCE(quantidade_matricula_profissional_tecnica_subsequente, 0)) AS qtd_subsequente,
    SUM(COALESCE(quantidade_matricula_eja_medio_tecnico, 0)) AS qtd_eja_tecnico
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = '{UF}'
    AND ano = (
      SELECT MAX(ano)
      FROM `basedosdados.br_inep_censo_escolar.escola`
      WHERE sigla_uf = '{UF}'
    )
  GROUP BY ano
),

perfil AS (
  SELECT
    ano AS ano_perfil,
    COUNT(*) AS total,
    COUNTIF(idade BETWEEN 15 AND 17) AS faixa_15_17,
    COUNTIF(idade BETWEEN 18 AND 24) AS faixa_18_24,
    COUNTIF(idade >= 25) AS faixa_25_mais,
    COUNTIF(sexo = '1') AS masc,
    COUNTIF(sexo = '2') AS fem
  FROM ept_matricula
  GROUP BY ano
)

SELECT
  p.ano_perfil AS ano,
  p.total,
  p.faixa_15_17, p.faixa_18_24, p.faixa_25_mais,
  p.masc, p.fem,
  m.qtd_integrada, m.qtd_concomitante, m.qtd_subsequente, m.qtd_eja_tecnico,
  m.ano AS ano_modalidade
FROM perfil p
CROSS JOIN modalidade m;
