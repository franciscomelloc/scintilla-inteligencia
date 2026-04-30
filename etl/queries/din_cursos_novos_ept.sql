-- Indicador: din_cursos_novos_ept
-- Janela: pares (id_escola, id_curso) que aparecem em 2020 e não existiam em 2016-2019.
-- Descontinuados: existiam em 2019 e sumiram em 2020.
-- (matricula table tem 2020 como ano mais recente em BD)

WITH pares_por_ano AS (
  SELECT DISTINCT
    ano,
    rede,
    id_escola,
    id_curso_educ_profissional AS id_curso
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2016 AND 2020
    AND sigla_uf = '{UF}'
    AND id_curso_educ_profissional IS NOT NULL
),

pares_atual AS (
  SELECT rede, id_escola, id_curso
  FROM pares_por_ano
  WHERE ano = 2020
),

pares_anterior AS (
  SELECT DISTINCT id_escola, id_curso
  FROM pares_por_ano
  WHERE ano BETWEEN 2016 AND 2019
),

novos AS (
  SELECT p.*
  FROM pares_atual p
  LEFT JOIN pares_anterior a
    ON p.id_escola = a.id_escola AND p.id_curso = a.id_curso
  WHERE a.id_escola IS NULL
),

pares_anterior_recente AS (
  SELECT rede, id_escola, id_curso
  FROM pares_por_ano
  WHERE ano = 2019
),

descontinuados AS (
  SELECT p.*
  FROM pares_anterior_recente p
  LEFT JOIN pares_atual a
    ON p.id_escola = a.id_escola AND p.id_curso = a.id_curso
  WHERE a.id_escola IS NULL
)

SELECT
  (SELECT COUNT(*) FROM novos) AS cursos_novos_total,
  (SELECT COUNT(*) FROM novos WHERE rede = '2') AS cursos_novos_estadual,
  (SELECT COUNT(*) FROM descontinuados) AS cursos_descontinuados_total,
  (SELECT COUNT(*) FROM descontinuados WHERE rede = '2') AS cursos_descontinuados_estadual;
