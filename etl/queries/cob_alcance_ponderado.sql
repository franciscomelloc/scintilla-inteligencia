-- Indicador: cob_alcance_ponderado
-- % das matrículas EM em município com pelo menos 1 escola técnica
-- Top 5 municípios com maior pop EM e SEM oferta EPT
-- Proxy: matrículas EM por município ≈ população em idade escolar

WITH escola_agg AS (
  SELECT
    ano,
    id_municipio,
    SUM(COALESCE(quantidade_matricula_medio, 0)) AS qtd_em,
    SUM(COALESCE(quantidade_matricula_profissional_tecnica, 0)
        + COALESCE(quantidade_matricula_medio_tecnico, 0)
        + COALESCE(quantidade_matricula_eja_medio_tecnico, 0)) AS qtd_ept
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = @uf
    AND ano = (
      SELECT MAX(ano)
      FROM `basedosdados.br_inep_censo_escolar.escola`
      WHERE sigla_uf = @uf
    )
  GROUP BY ano, id_municipio
),

municipio_nome AS (
  SELECT id_municipio, nome
  FROM `basedosdados.br_bd_diretorios_brasil.municipio`
),

cobertura AS (
  SELECT
    ano,
    SUM(IF(qtd_ept > 0, qtd_em, 0)) AS qtd_em_em_munis_com_ept,
    SUM(qtd_em) AS qtd_em_total
  FROM escola_agg
  GROUP BY ano
),

top5_sem_oferta_arr AS (
  SELECT
    ARRAY_AGG(STRUCT(municipio, pop_em_proxy) ORDER BY pop_em_proxy DESC LIMIT 5) AS top5
  FROM (
    SELECT
      m.nome AS municipio,
      e.qtd_em AS pop_em_proxy
    FROM escola_agg e
    LEFT JOIN municipio_nome m ON m.id_municipio = e.id_municipio
    WHERE e.qtd_ept = 0 AND e.qtd_em > 0
  )
)

SELECT
  c.ano,
  c.qtd_em_em_munis_com_ept,
  c.qtd_em_total,
  t.top5 AS top5_sem_oferta
FROM cobertura c
CROSS JOIN top5_sem_oferta_arr t;
