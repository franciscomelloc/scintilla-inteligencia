-- Indicador: mer_demanda_cbo_top
-- Recortes: apenas total_estado
-- Top 10 ocupações técnicas (CBO 3xxxx) por saldo CAGED nos últimos 12 meses
-- de dados disponíveis. Inclui salário mediano de admissão (P25/P50/P75) e
-- número de admissões.
--
-- Rigor:
-- - Salário mediano apenas em ADMISSÕES (saldo_movimentacao > 0), não em
--   desligamentos. Salário de desligamento mistura efeitos diferentes
--   (rescisão, antiguidade) e não responde "quanto o mercado paga novo".
-- - APPROX_QUANTILES com IGNORE NULLS — exclui registros sem salário.
-- - Janela de 12 meses corridos usando o último ano disponível (não soma
--   anos parciais — caveat se ano corrente tem <12 meses ainda).
-- - LEFT JOIN com diretório CBO 2002 da BD; se o JOIN não casar, descrição
--   vem null (processador trata como fallback).
--
-- Caveat estrutural: CBO 3xxxx ("Técnicos de Nível Médio") é definição
-- estatística do IBGE/MTE — inclui ocupações que exigem formação técnica
-- formal. Não captura técnicos que entram em CBO 7xxxx (operacionais
-- qualificados). Comparação com Censo Escolar EPT é descritiva, não causal.

WITH base AS (
  SELECT
    ano,
    cbo_2002,
    saldo_movimentacao,
    salario_mensal
  FROM `basedosdados.br_me_caged.microdados_movimentacao`
  WHERE sigla_uf = '{UF}'
    AND cbo_2002 IS NOT NULL
    AND cbo_2002 LIKE '3%'
),

ano_mais_recente AS (
  SELECT MAX(ano) AS ano_max
  FROM base
),

agg AS (
  SELECT
    b.cbo_2002,
    SUM(b.saldo_movimentacao) AS saldo_12m,
    COUNTIF(b.saldo_movimentacao > 0) AS n_admissoes,
    COUNTIF(b.saldo_movimentacao < 0) AS n_desligamentos,
    APPROX_QUANTILES(
      IF(b.saldo_movimentacao > 0 AND b.salario_mensal > 0, b.salario_mensal, NULL),
      100 IGNORE NULLS
    ) AS sal_quantis
  FROM base b
  CROSS JOIN ano_mais_recente a
  WHERE b.ano = a.ano_max
  GROUP BY b.cbo_2002
  HAVING n_admissoes >= 10  -- piso de 10 admissões pra mediana ser estável
)

SELECT
  (SELECT ano_max FROM ano_mais_recente) AS ano_referencia,
  agg.cbo_2002,
  -- Descrição via diretório CBO da BD; se ausente, fica null (processador trata)
  cbo_dir.descricao AS cbo_descricao,
  agg.saldo_12m,
  agg.n_admissoes,
  agg.n_desligamentos,
  agg.sal_quantis[OFFSET(25)] AS salario_p25,
  agg.sal_quantis[OFFSET(50)] AS salario_mediano,
  agg.sal_quantis[OFFSET(75)] AS salario_p75
FROM agg
LEFT JOIN `basedosdados.br_bd_diretorios_brasil.cbo_2002` cbo_dir
  ON cbo_dir.cbo_2002 = agg.cbo_2002
ORDER BY agg.saldo_12m DESC
LIMIT 15;
