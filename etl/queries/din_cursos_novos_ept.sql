-- Indicador: din_cursos_novos_ept
-- Recortes: total_estado + rede_estadual
--
-- Definição: par escola+curso que aparece pela primeira vez na janela observada (N-2 a N).
-- Excluir reaberturas (par que existia em N-3 ou antes, pausou e voltou).
-- Saldo líquido = novos − descontinuados.

WITH pares_por_ano AS (
  SELECT DISTINCT
    ano,
    dependencia_administrativa,
    id_escola,
    id_curso
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
),

novos AS (
  -- pares em 2024 que não existiam em 2022 nem 2023 nem antes
  SELECT
    p2024.dependencia_administrativa,
    p2024.id_escola,
    p2024.id_curso
  FROM pares_por_ano p2024
  LEFT JOIN pares_por_ano p_anterior
    ON p2024.id_escola = p_anterior.id_escola
    AND p2024.id_curso = p_anterior.id_curso
    AND p_anterior.ano IN (2020, 2021, 2022, 2023)
  WHERE p2024.ano = 2024 AND p_anterior.id_escola IS NULL
),

descontinuados AS (
  -- pares em 2023 que não aparecem em 2024 (e existiram antes)
  SELECT
    p2023.dependencia_administrativa,
    p2023.id_escola,
    p2023.id_curso
  FROM pares_por_ano p2023
  LEFT JOIN pares_por_ano p2024
    ON p2023.id_escola = p2024.id_escola
    AND p2023.id_curso = p2024.id_curso
    AND p2024.ano = 2024
  WHERE p2023.ano = 2023 AND p2024.id_escola IS NULL
)

SELECT
  COUNT(DISTINCT (id_escola, id_curso)) FROM novos AS cursos_novos_total,
  COUNT(DISTINCT CASE WHEN dependencia_administrativa = 2 THEN (id_escola, id_curso) END) FROM novos AS cursos_novos_estadual,
  COUNT(DISTINCT (id_escola, id_curso)) FROM descontinuados AS cursos_descontinuados_total,
  COUNT(DISTINCT CASE WHEN dependencia_administrativa = 2 THEN (id_escola, id_curso) END) FROM descontinuados AS cursos_descontinuados_estadual;

-- Nota: a sintaxe acima é simplificada — em produção, separar em CTEs ou queries distintas.
-- BigQuery exige UNION ALL ou subqueries para combinar contagens de tabelas diferentes.
