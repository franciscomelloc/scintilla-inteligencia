-- Indicador: cob_eixos_cobertos
-- Recortes: total_estado + rede_estadual
-- Output: matriculas EPT por id_curso_educ_profissional. Mapeamento curso→eixo
-- aplicado em Python via etl/reference/cnct_curso_eixo.csv após a query.
--
-- O id_curso_educ_profissional é null quando matrícula não é EPT.

SELECT
  ano,
  rede,
  id_curso_educ_profissional AS id_curso,
  COUNT(*) AS qtd_matriculas
FROM `basedosdados.br_inep_censo_escolar.matricula`
WHERE ano BETWEEN 2020 AND 2024
  AND sigla_uf = '{UF}'
  AND id_curso_educ_profissional IS NOT NULL
GROUP BY ano, rede, id_curso_educ_profissional
ORDER BY ano, rede, qtd_matriculas DESC;
