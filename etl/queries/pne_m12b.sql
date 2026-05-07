-- Indicador: pne_m12b
-- PNE Meta 12.b · expandir +60% as matrículas em cursos subsequentes
-- Saída: matrículas subsequentes por ano 2020-2024 + total estadual

SELECT
  ano,
  SUM(COALESCE(quantidade_matricula_profissional_tecnica_subsequente, 0)) AS qtd_subsequente_total,
  SUM(IF(rede='2', COALESCE(quantidade_matricula_profissional_tecnica_subsequente, 0), 0)) AS qtd_subsequente_estadual
FROM `basedosdados.br_inep_censo_escolar.escola`
WHERE sigla_uf = @uf
  AND ano BETWEEN 2020 AND 2024
GROUP BY ano
ORDER BY ano;
