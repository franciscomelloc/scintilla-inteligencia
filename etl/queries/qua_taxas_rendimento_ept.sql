-- Indicador: qua_taxas_rendimento_ept
-- Recortes: total_estado + rede_estadual
-- 3 sub-valores: aprovação, reprovação, abandono — na ÚLTIMA SÉRIE de cada modalidade
--
-- Pendência: tentar usar primeiro `br_inep_indicadores_educacionais` (cálculo oficial INEP).
-- Fallback se não tem corte modal EPT: calcular via Censo Escolar bruto agregando situacao_aluno.
-- A consulta abaixo é o fallback (mais flexível).

WITH ultima_serie AS (
  -- identifica matrículas na última série de cada modalidade EPT
  SELECT
    ano,
    dependencia_administrativa,
    tipo_oferta,
    situacao_aluno,
    COUNT(*) AS qtd
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
    AND etapa_ensino IN (
      -- códigos de "última série" por modalidade — validar pós-GCP
      27, 28,  -- 3ª série EM EPT integrada (placeholder)
      30, 31   -- última fase concomitante/subsequente (placeholder)
    )
  GROUP BY ano, dependencia_administrativa, tipo_oferta, situacao_aluno
)

SELECT
  ano,
  tipo_oferta,
  -- total_estado
  100.0 * SUM(CASE WHEN situacao_aluno IN ('aprovado', 'concluinte') THEN qtd ELSE 0 END) /
    NULLIF(SUM(qtd), 0) AS pct_aprovacao_total,
  100.0 * SUM(CASE WHEN situacao_aluno = 'reprovado' THEN qtd ELSE 0 END) /
    NULLIF(SUM(qtd), 0) AS pct_reprovacao_total,
  100.0 * SUM(CASE WHEN situacao_aluno IN ('abandono', 'transferido') THEN qtd ELSE 0 END) /
    NULLIF(SUM(qtd), 0) AS pct_abandono_total,
  -- rede_estadual
  100.0 * SUM(CASE WHEN dependencia_administrativa = 2 AND situacao_aluno IN ('aprovado', 'concluinte') THEN qtd ELSE 0 END) /
    NULLIF(SUM(CASE WHEN dependencia_administrativa = 2 THEN qtd ELSE 0 END), 0) AS pct_aprovacao_estadual,
  100.0 * SUM(CASE WHEN dependencia_administrativa = 2 AND situacao_aluno = 'reprovado' THEN qtd ELSE 0 END) /
    NULLIF(SUM(CASE WHEN dependencia_administrativa = 2 THEN qtd ELSE 0 END), 0) AS pct_reprovacao_estadual,
  100.0 * SUM(CASE WHEN dependencia_administrativa = 2 AND situacao_aluno IN ('abandono', 'transferido') THEN qtd ELSE 0 END) /
    NULLIF(SUM(CASE WHEN dependencia_administrativa = 2 THEN qtd ELSE 0 END), 0) AS pct_abandono_estadual
FROM ultima_serie
GROUP BY ano, tipo_oferta
ORDER BY ano, tipo_oferta;
