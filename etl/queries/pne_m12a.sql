-- Indicador: pne_m12a
-- PNE Meta 12.a · % do EM em integrada+concomitante
-- Numerador: matrículas em EM-técnico (integrada) + Profissional Técnica concomitante
-- Denominador: matrículas EM total (cap em 100% pra rede federal/IF que tem mais técnicos que EM regular)

WITH agg AS (
  SELECT
    ano,
    rede,
    SUM(COALESCE(quantidade_matricula_medio_tecnico, 0)
        + COALESCE(quantidade_matricula_profissional_tecnica_concomitante, 0)) AS num,
    SUM(COALESCE(quantidade_matricula_medio, 0)
        + COALESCE(quantidade_matricula_profissional_tecnica_concomitante, 0)) AS den
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = '{UF}'
    AND ano BETWEEN 2020 AND 2024
  GROUP BY ano, rede
),

por_rede AS (
  SELECT ano,
    SUM(num) AS num_total,
    SUM(den) AS den_total,
    SUM(IF(rede='1', num, 0)) AS num_federal,
    SUM(IF(rede='1', den, 0)) AS den_federal,
    SUM(IF(rede='2', num, 0)) AS num_estadual,
    SUM(IF(rede='2', den, 0)) AS den_estadual,
    SUM(IF(rede='3', num, 0)) AS num_municipal,
    SUM(IF(rede='3', den, 0)) AS den_municipal,
    SUM(IF(rede='4', num, 0)) AS num_privada,
    SUM(IF(rede='4', den, 0)) AS den_privada
  FROM agg
  GROUP BY ano
)

SELECT
  ano,
  ROUND(LEAST(100.0, 100.0 * num_total / NULLIF(den_total, 0)), 2) AS pct_total,
  ROUND(LEAST(100.0, 100.0 * num_estadual / NULLIF(den_estadual, 0)), 2) AS pct_estadual,
  ROUND(LEAST(100.0, 100.0 * num_federal / NULLIF(den_federal, 0)), 2) AS pct_federal,
  ROUND(LEAST(100.0, 100.0 * num_municipal / NULLIF(den_municipal, 0)), 2) AS pct_municipal,
  ROUND(LEAST(100.0, 100.0 * num_privada / NULLIF(den_privada, 0)), 2) AS pct_privada
FROM por_rede
ORDER BY ano;
