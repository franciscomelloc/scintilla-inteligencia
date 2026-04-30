-- Indicador: cob_eixos_cobertos
-- Recortes: total_estado + rede_estadual
--
-- Mapeamento curso técnico → eixo tecnológico via CSV em etl/reference/cnct_curso_eixo.csv
-- (carregado pelo build.py e passado como parâmetro à query, ou JOIN com tabela auxiliar
--  se carregada como dataset BigQuery)
--
-- Output: count distinct eixos com ≥1 matrícula no ano + lista nominal + top-3 por matrícula

WITH matriculas_com_eixo AS (
  SELECT
    m.ano,
    m.dependencia_administrativa,
    cnct.eixo_tecnologico,
    COUNT(*) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.matricula` m
  JOIN `<projeto>.reference.cnct_curso_eixo` cnct
    ON m.id_curso = cnct.id_curso  -- substituir <projeto> pelo dataset onde reference vai estar
  WHERE m.ano BETWEEN 2020 AND 2024
    AND m.tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND m.sigla_uf = '{UF}'
  GROUP BY m.ano, m.dependencia_administrativa, cnct.eixo_tecnologico
)

SELECT
  ano,
  COUNT(DISTINCT eixo_tecnologico) AS qtd_eixos_total_estado,
  COUNT(DISTINCT CASE WHEN dependencia_administrativa = 2 THEN eixo_tecnologico END) AS qtd_eixos_rede_estadual,
  ARRAY_AGG(DISTINCT eixo_tecnologico ORDER BY eixo_tecnologico) AS eixos_total_estado,
  ARRAY_AGG(DISTINCT CASE WHEN dependencia_administrativa = 2 THEN eixo_tecnologico END IGNORE NULLS) AS eixos_rede_estadual
FROM matriculas_com_eixo
GROUP BY ano
ORDER BY ano;
