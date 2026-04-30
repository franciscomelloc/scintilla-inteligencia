-- Indicador: din_crescimento_matriculas_5y
-- Recortes: total_estado + rede_estadual
-- Janela fixa: Censo mais recente vs 5 anos anteriores
-- Output: pct change overall, por rede, e decomposição por modalidade.
-- Modalidade aqui depende da classificação por etapa_ensino — feita em Python.
-- SQL retorna contagens; Python calcula deltas.

WITH matriculas AS (
  SELECT
    ano,
    rede,
    etapa_ensino,
    COUNT(*) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano IN (2015, 2020)
    AND sigla_uf = '{UF}'
    AND id_curso_educ_profissional IS NOT NULL
  GROUP BY ano, rede, etapa_ensino
)

SELECT
  ano,
  rede,
  etapa_ensino,
  qtd
FROM matriculas
ORDER BY ano, rede, qtd DESC;
