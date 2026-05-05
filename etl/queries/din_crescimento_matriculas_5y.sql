-- Indicador: din_crescimento_matriculas_5y
-- Janela fixa: Censo mais recente vs 5 anos anteriores
-- Output: pct change overall, por rede, e decomposição por modalidade.
-- Modalidade aqui depende da classificação por etapa_ensino — feita em Python.
-- SQL retorna contagens; Python calcula deltas.
--
-- Fonte: tabela `turma` (matricula descontinuada após 2020 na BD).
-- Janela atualizada: 2019 vs 2024 (5 anos).

WITH matriculas AS (
  SELECT
    ano,
    rede,
    etapa_ensino,
    SUM(quantidade_matriculas) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.turma`
  WHERE ano IN (2019, 2024)
    AND sigla_uf = '{UF}'
    AND id_curso_educacao_profissional IS NOT NULL
    AND quantidade_matriculas IS NOT NULL
  GROUP BY ano, rede, etapa_ensino
)

SELECT
  ano,
  rede,
  etapa_ensino,
  qtd
FROM matriculas
ORDER BY ano, rede, qtd DESC;
