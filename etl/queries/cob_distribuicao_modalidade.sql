-- Indicador: cob_distribuicao_modalidade
-- Recortes: total_estado + rede_estadual
-- Output: 3 valores (integrada/concomitante/subsequente) que somam 100%

WITH matriculas AS (
  SELECT
    ano,
    dependencia_administrativa,
    tipo_oferta,
    COUNT(*) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
  GROUP BY ano, dependencia_administrativa, tipo_oferta
)

SELECT
  ano,
  -- total_estado
  100.0 * SUM(CASE WHEN tipo_oferta = 'integrada' THEN qtd ELSE 0 END) / SUM(qtd) AS pct_integrada_total,
  100.0 * SUM(CASE WHEN tipo_oferta = 'concomitante' THEN qtd ELSE 0 END) / SUM(qtd) AS pct_concomitante_total,
  100.0 * SUM(CASE WHEN tipo_oferta = 'subsequente' THEN qtd ELSE 0 END) / SUM(qtd) AS pct_subsequente_total,
  -- rede_estadual
  100.0 * SUM(CASE WHEN dependencia_administrativa = 2 AND tipo_oferta = 'integrada' THEN qtd ELSE 0 END) /
    NULLIF(SUM(CASE WHEN dependencia_administrativa = 2 THEN qtd ELSE 0 END), 0) AS pct_integrada_estadual,
  100.0 * SUM(CASE WHEN dependencia_administrativa = 2 AND tipo_oferta = 'concomitante' THEN qtd ELSE 0 END) /
    NULLIF(SUM(CASE WHEN dependencia_administrativa = 2 THEN qtd ELSE 0 END), 0) AS pct_concomitante_estadual,
  100.0 * SUM(CASE WHEN dependencia_administrativa = 2 AND tipo_oferta = 'subsequente' THEN qtd ELSE 0 END) /
    NULLIF(SUM(CASE WHEN dependencia_administrativa = 2 THEN qtd ELSE 0 END), 0) AS pct_subsequente_estadual
FROM matriculas
GROUP BY ano
ORDER BY ano;
