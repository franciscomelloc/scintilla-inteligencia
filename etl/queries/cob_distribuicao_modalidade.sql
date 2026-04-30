-- Indicador: cob_distribuicao_modalidade
-- Recortes: total_estado + rede_estadual
-- Output: matriculas EPT por etapa_ensino. Classificação em integrada/concomitante/subsequente
-- aplicada em Python a partir do dicionário INEP (estável entre anos).
--
-- Filtro EPT: id_curso_educ_profissional IS NOT NULL captura todas as matrículas que têm
-- curso técnico associado (cobre integrada+concomitante+subsequente+FIC+EJA-tec).

SELECT
  ano,
  rede,
  etapa_ensino,
  COUNT(*) AS qtd_matriculas
FROM `basedosdados.br_inep_censo_escolar.matricula`
WHERE ano BETWEEN 2016 AND 2020
  AND sigla_uf = '{UF}'
  AND id_curso_educ_profissional IS NOT NULL
GROUP BY ano, rede, etapa_ensino
ORDER BY ano, rede, qtd_matriculas DESC;
