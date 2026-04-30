-- Indicador: qua_ideb_escolas_ept
-- Recortes: total_estado + rede_estadual
-- IDEB é bianual (anos ímpares pra EM: 2017, 2019, 2021, 2023)

WITH escolas_com_ept AS (
  SELECT DISTINCT
    e.id_escola,
    e.rede,
    e.ano
  FROM `basedosdados.br_inep_censo_escolar.escola` e
  WHERE e.ano IN (2017, 2019, 2021, 2023)
    AND e.sigla_uf = '{UF}'
    AND COALESCE(e.quantidade_matricula_medio_tecnico, 0) > 0
)

SELECT
  i.ano,
  ROUND(AVG(i.ideb), 2) AS ideb_total_estado,
  ROUND(AVG(IF(ept.rede = 'estadual', i.ideb, NULL)), 2) AS ideb_rede_estadual
FROM `basedosdados.br_inep_ideb.escola` i
INNER JOIN escolas_com_ept ept
  ON i.id_escola = ept.id_escola AND i.ano = ept.ano
WHERE i.ano IN (2017, 2019, 2021, 2023)
  AND i.ensino = 'medio'
  AND i.sigla_uf = '{UF}'
GROUP BY i.ano
ORDER BY i.ano;
