-- Indicador: qua_ideb_escolas_ept
-- Recortes: total_estado + rede_estadual
-- IDEB é bianual (anos pares) — sparkline terá gaps null nos anos ímpares

WITH escolas_com_ept AS (
  SELECT DISTINCT
    id_escola,
    sigla_uf,
    dependencia_administrativa,
    ano
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2017 AND 2023
    AND tipo_oferta IN ('integrada', 'concomitante')  -- subsequente puro não tem IDEB-EM
    AND sigla_uf = '{UF}'
)

SELECT
  i.ano,
  -- total_estado: média ponderada por matrículas EM
  AVG(i.ideb) AS ideb_total_estado,
  AVG(CASE WHEN ept.dependencia_administrativa = 2 THEN i.ideb END) AS ideb_rede_estadual
FROM `basedosdados.br_inep_ideb.escola` i
LEFT JOIN escolas_com_ept ept
  ON i.id_escola = ept.id_escola AND i.ano = ept.ano
WHERE i.ano IN (2017, 2019, 2021, 2023)
  AND i.etapa_ensino = 'ensino_medio'
  AND i.sigla_uf = '{UF}'
GROUP BY i.ano
ORDER BY i.ano;
