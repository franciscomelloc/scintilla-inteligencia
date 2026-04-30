-- Indicador: din_crescimento_matriculas_5y
-- Recortes: total_estado + rede_estadual
-- Janela fixa: Censo mais recente vs 5 anos anteriores (não móvel)
-- Decomposição por modalidade e por dependência

WITH matriculas AS (
  SELECT
    ano,
    dependencia_administrativa,
    tipo_oferta,
    COUNT(*) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano IN (2019, 2024)
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
  GROUP BY ano, dependencia_administrativa, tipo_oferta
),

agregados AS (
  SELECT
    ano,
    dependencia_administrativa,
    tipo_oferta,
    SUM(qtd) AS total
  FROM matriculas
  GROUP BY ano, dependencia_administrativa, tipo_oferta
)

SELECT
  -- total_estado overall
  100.0 * (
    SUM(CASE WHEN ano = 2024 THEN total ELSE 0 END) -
    SUM(CASE WHEN ano = 2019 THEN total ELSE 0 END)
  ) / NULLIF(SUM(CASE WHEN ano = 2019 THEN total ELSE 0 END), 0) AS crescimento_5y_total,

  -- rede_estadual overall
  100.0 * (
    SUM(CASE WHEN ano = 2024 AND dependencia_administrativa = 2 THEN total ELSE 0 END) -
    SUM(CASE WHEN ano = 2019 AND dependencia_administrativa = 2 THEN total ELSE 0 END)
  ) / NULLIF(SUM(CASE WHEN ano = 2019 AND dependencia_administrativa = 2 THEN total ELSE 0 END), 0) AS crescimento_5y_estadual,

  -- decomposição por modalidade (total_estado)
  100.0 * (
    SUM(CASE WHEN ano = 2024 AND tipo_oferta = 'integrada' THEN total ELSE 0 END) -
    SUM(CASE WHEN ano = 2019 AND tipo_oferta = 'integrada' THEN total ELSE 0 END)
  ) / NULLIF(SUM(CASE WHEN ano = 2019 AND tipo_oferta = 'integrada' THEN total ELSE 0 END), 0) AS crescimento_integrada,
  100.0 * (
    SUM(CASE WHEN ano = 2024 AND tipo_oferta = 'concomitante' THEN total ELSE 0 END) -
    SUM(CASE WHEN ano = 2019 AND tipo_oferta = 'concomitante' THEN total ELSE 0 END)
  ) / NULLIF(SUM(CASE WHEN ano = 2019 AND tipo_oferta = 'concomitante' THEN total ELSE 0 END), 0) AS crescimento_concomitante,
  100.0 * (
    SUM(CASE WHEN ano = 2024 AND tipo_oferta = 'subsequente' THEN total ELSE 0 END) -
    SUM(CASE WHEN ano = 2019 AND tipo_oferta = 'subsequente' THEN total ELSE 0 END)
  ) / NULLIF(SUM(CASE WHEN ano = 2019 AND tipo_oferta = 'subsequente' THEN total ELSE 0 END), 0) AS crescimento_subsequente
FROM agregados;
