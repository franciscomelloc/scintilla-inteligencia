-- Indicador: cob_distribuicao_dependencia
-- Recortes: apenas total_estado (é o próprio recorte sendo decomposto)
--
-- Output: 4 fatias somando 100% (federal/estadual/municipal/privada+SistemaS)
-- Sistema S agregado em "privada" no MVP (lookup canônico fica para v2)

WITH matriculas AS (
  SELECT
    ano,
    dependencia_administrativa,
    COUNT(*) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
  GROUP BY ano, dependencia_administrativa
),

totals AS (
  SELECT ano, SUM(qtd) AS total
  FROM matriculas
  GROUP BY ano
)

SELECT
  m.ano,
  100.0 * SUM(CASE WHEN m.dependencia_administrativa = 1 THEN m.qtd ELSE 0 END) / t.total AS pct_federal,
  100.0 * SUM(CASE WHEN m.dependencia_administrativa = 2 THEN m.qtd ELSE 0 END) / t.total AS pct_estadual,
  100.0 * SUM(CASE WHEN m.dependencia_administrativa = 3 THEN m.qtd ELSE 0 END) / t.total AS pct_municipal,
  100.0 * SUM(CASE WHEN m.dependencia_administrativa = 4 THEN m.qtd ELSE 0 END) / t.total AS pct_privada_e_sistema_s
FROM matriculas m
JOIN totals t USING (ano)
GROUP BY m.ano, t.total
ORDER BY m.ano;
