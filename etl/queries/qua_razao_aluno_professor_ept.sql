-- Indicador: qua_razao_aluno_professor_ept
-- Recortes: total_estado + rede_estadual
-- Polaridade: INVERSA (razão menor é melhor)
-- Definição: alunos EPT / docentes que dão aula em turmas com pelo menos 1 matrícula EPT.

WITH turmas_ept AS (
  SELECT DISTINCT
    ano,
    rede,
    id_turma,
    id_escola
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2016 AND 2020
    AND sigla_uf = '{UF}'
    AND id_curso_educ_profissional IS NOT NULL
),

alunos_por_ano AS (
  SELECT
    ano,
    rede,
    COUNT(*) AS qtd_alunos
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2016 AND 2020
    AND sigla_uf = '{UF}'
    AND id_curso_educ_profissional IS NOT NULL
  GROUP BY ano, rede
),

docentes_por_ano AS (
  SELECT
    d.ano,
    t.rede,
    COUNT(DISTINCT d.id_docente) AS qtd_docentes
  FROM `basedosdados.br_inep_censo_escolar.docente` d
  INNER JOIN turmas_ept t
    ON d.id_turma = t.id_turma AND d.ano = t.ano
  WHERE d.sigla_uf = '{UF}'
  GROUP BY d.ano, t.rede
)

SELECT
  COALESCE(a.ano, d.ano) AS ano,
  ROUND(SUM(a.qtd_alunos) * 1.0 / NULLIF(SUM(d.qtd_docentes), 0), 2) AS razao_total_estado,
  ROUND(SUM(IF(a.rede = '2', a.qtd_alunos, 0)) * 1.0 /
        NULLIF(SUM(IF(d.rede = '2', d.qtd_docentes, 0)), 0), 2) AS razao_rede_estadual
FROM alunos_por_ano a
FULL OUTER JOIN docentes_por_ano d USING (ano, rede)
GROUP BY ano
ORDER BY ano;
