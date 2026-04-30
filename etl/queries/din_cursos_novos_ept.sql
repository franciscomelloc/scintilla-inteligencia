-- Indicador: din_cursos_novos_ept
-- Recortes: total_estado + rede_estadual
-- Definição: par (id_escola, id_curso_educ_profissional) que aparece em 2024 e
-- não existia em 2020-2023.

WITH pares_por_ano AS (
  SELECT DISTINCT
    ano,
    rede,
    id_escola,
    id_curso_educ_profissional AS id_curso
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND sigla_uf = '{UF}'
    AND id_curso_educ_profissional IS NOT NULL
),

pares_2024 AS (
  SELECT rede, id_escola, id_curso
  FROM pares_por_ano
  WHERE ano = 2024
),

pares_anterior AS (
  SELECT DISTINCT id_escola, id_curso
  FROM pares_por_ano
  WHERE ano BETWEEN 2020 AND 2023
),

novos AS (
  SELECT p.*
  FROM pares_2024 p
  LEFT JOIN pares_anterior a
    ON p.id_escola = a.id_escola AND p.id_curso = a.id_curso
  WHERE a.id_escola IS NULL
),

pares_2023 AS (
  SELECT rede, id_escola, id_curso
  FROM pares_por_ano
  WHERE ano = 2023
),

pares_existem_2024 AS (
  SELECT id_escola, id_curso
  FROM pares_por_ano
  WHERE ano = 2024
),

descontinuados AS (
  SELECT p.*
  FROM pares_2023 p
  LEFT JOIN pares_existem_2024 a
    ON p.id_escola = a.id_escola AND p.id_curso = a.id_curso
  WHERE a.id_escola IS NULL
)

SELECT
  (SELECT COUNT(*) FROM novos) AS cursos_novos_total,
  (SELECT COUNT(*) FROM novos WHERE rede = 'estadual') AS cursos_novos_estadual,
  (SELECT COUNT(*) FROM descontinuados) AS cursos_descontinuados_total,
  (SELECT COUNT(*) FROM descontinuados WHERE rede = 'estadual') AS cursos_descontinuados_estadual;
