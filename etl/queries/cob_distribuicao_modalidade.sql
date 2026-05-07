-- Indicador: cob_distribuicao_modalidade
-- Recortes: total_estado + rede_estadual
-- Output: matriculas EPT por etapa_ensino. Classificação em integrada/concomitante/subsequente
-- aplicada em Python a partir do dicionário INEP (estável entre anos).
--
-- Filtro EPT: id_curso_educacao_profissional IS NOT NULL captura todas as matrículas que têm
-- curso técnico associado (cobre integrada+concomitante+subsequente+FIC+EJA-tec).
--
-- Fonte: tabela `turma` (matricula descontinuada após 2020 na BD).

SELECT
  ano,
  rede,
  etapa_ensino,
  SUM(quantidade_matriculas) AS qtd_matriculas
FROM `basedosdados.br_inep_censo_escolar.turma`
WHERE ano BETWEEN 2020 AND 2024
  AND sigla_uf = @uf
  AND id_curso_educacao_profissional IS NOT NULL
  AND quantidade_matriculas IS NOT NULL
GROUP BY ano, rede, etapa_ensino
ORDER BY ano, rede, qtd_matriculas DESC;
