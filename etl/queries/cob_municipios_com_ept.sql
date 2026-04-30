-- Indicador: cob_municipios_com_ept
-- Recortes: total_estado + rede_estadual
-- numerador: count(distinct mun com ≥1 escola que ofereça matrícula EPT no ano)
-- denominador: total municípios do UF (br_bd_diretorios_brasil.municipio)

WITH escolas_com_ept AS (
  SELECT DISTINCT
    id_municipio,
    rede,
    ano
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE ano BETWEEN 2020 AND 2024
    AND sigla_uf = '{UF}'
    AND (COALESCE(quantidade_matricula_medio_tecnico, 0)
         + COALESCE(quantidade_matricula_eja_medio_tecnico, 0)) > 0
),

total_mun_uf AS (
  SELECT COUNT(DISTINCT id_municipio) AS total
  FROM `basedosdados.br_bd_diretorios_brasil.municipio`
  WHERE sigla_uf = '{UF}'
)

SELECT
  e.ano,
  ROUND(100.0 * COUNT(DISTINCT e.id_municipio) / t.total, 2) AS pct_total_estado,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN e.rede = 'estadual' THEN e.id_municipio END) / t.total, 2) AS pct_rede_estadual,
  t.total AS total_municipios
FROM escolas_com_ept e
CROSS JOIN total_mun_uf t
GROUP BY e.ano, t.total
ORDER BY e.ano;
