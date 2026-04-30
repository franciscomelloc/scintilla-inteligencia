-- Indicador: cob_municipios_com_ept
-- Recortes: total_estado + rede_estadual
--
-- numerador = count(distinct mun com ≥1 escola que ofereça matrícula EPT no ano)
-- denominador = total municípios do UF

WITH escolas_com_ept AS (
  SELECT DISTINCT
    e.id_municipio,
    e.dependencia_administrativa,
    m.ano
  FROM `basedosdados.br_inep_censo_escolar.escola` e
  JOIN `basedosdados.br_inep_censo_escolar.matricula` m
    ON e.id_escola = m.id_escola AND e.ano = m.ano
  WHERE m.ano BETWEEN 2020 AND 2024
    AND m.tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND e.sigla_uf = '{UF}'
),

total_mun_uf AS (
  SELECT COUNT(DISTINCT id_municipio) AS total
  FROM `basedosdados.br_bd_diretorios_brasil.municipio`
  WHERE sigla_uf = '{UF}'
)

SELECT
  e.ano,
  100.0 * COUNT(DISTINCT e.id_municipio) / t.total AS pct_total_estado,
  100.0 * COUNT(DISTINCT CASE WHEN e.dependencia_administrativa = 2 THEN e.id_municipio END) / t.total AS pct_rede_estadual
FROM escolas_com_ept e
CROSS JOIN total_mun_uf t
GROUP BY e.ano, t.total
ORDER BY e.ano;
