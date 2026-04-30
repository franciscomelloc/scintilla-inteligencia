-- Indicador: cob_distribuicao_dependencia
-- Recortes: apenas total_estado (é o próprio recorte sendo decomposto)
-- Output: 4 fatias somando 100% (federal/estadual/municipal/privada)
-- Fonte: br_inep_censo_escolar.escola (campos agregados quantidade_matricula_medio_tecnico
-- + quantidade_matricula_eja_medio_tecnico)

WITH matriculas_ept AS (
  SELECT
    ano,
    rede,
    SUM(COALESCE(quantidade_matricula_medio_tecnico, 0)
        + COALESCE(quantidade_matricula_eja_medio_tecnico, 0)) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE ano BETWEEN 2020 AND 2024
    AND sigla_uf = '{UF}'
  GROUP BY ano, rede
),

por_ano AS (
  SELECT
    ano,
    SUM(IF(rede = 'federal', qtd, 0)) AS federal,
    SUM(IF(rede = 'estadual', qtd, 0)) AS estadual,
    SUM(IF(rede = 'municipal', qtd, 0)) AS municipal,
    SUM(IF(rede = 'privada', qtd, 0)) AS privada,
    SUM(qtd) AS total
  FROM matriculas_ept
  GROUP BY ano
)

SELECT
  ano,
  ROUND(federal * 100.0 / NULLIF(total, 0), 2) AS pct_federal,
  ROUND(estadual * 100.0 / NULLIF(total, 0), 2) AS pct_estadual,
  ROUND(municipal * 100.0 / NULLIF(total, 0), 2) AS pct_municipal,
  ROUND(privada * 100.0 / NULLIF(total, 0), 2) AS pct_privada,
  total AS total_matriculas
FROM por_ano
ORDER BY ano;
