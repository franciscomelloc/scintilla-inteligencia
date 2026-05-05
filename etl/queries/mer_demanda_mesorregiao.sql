-- Indicador: mer_demanda_mesorregiao
-- Recortes: apenas total_estado
-- Saldo CAGED em CBO 3xxxx (Técnicos de Nível Médio) por mesorregião do
-- estado nos últimos 12 meses de dados. Inclui salário mediano de admissão
-- e share da mesorregião no total estadual.
--
-- Para BR (modo nacional): a query agrega TODAS as mesorregiões do país.
-- Geometria do estado fica perdida no caso BR (mesorregiões de UFs
-- diferentes não têm relação geográfica direta). Frontend deve exibir BR
-- como ranking nacional de mesorregiões, não como mapa.
--
-- Rigor:
-- - JOIN com diretório municipal da BD (oficial IBGE).
-- - Salário mediano só em admissões (saldo_movimentacao > 0).
-- - Piso de 50 admissões/mesorregião pra mediana — abaixo, salário fica null
--   (caveat: amostra insuficiente).
-- - Mesorregiões com saldo absoluto < 30 são suprimidas do output (ruído).

WITH base AS (
  SELECT
    c.ano,
    c.id_municipio,
    c.cbo_2002,
    c.saldo_movimentacao,
    c.salario_mensal
  FROM `basedosdados.br_me_caged.microdados_movimentacao` c
  WHERE c.sigla_uf = '{UF}'
    AND c.cbo_2002 IS NOT NULL
    AND c.cbo_2002 LIKE '3%'
    AND c.id_municipio IS NOT NULL
),

ano_mais_recente AS (
  SELECT MAX(ano) AS ano_max FROM base
),

municipio AS (
  SELECT id_municipio, id_mesorregiao, nome_mesorregiao, sigla_uf
  FROM `basedosdados.br_bd_diretorios_brasil.municipio`
),

agg AS (
  SELECT
    m.id_mesorregiao,
    m.nome_mesorregiao,
    m.sigla_uf AS sigla_uf_meso,
    SUM(b.saldo_movimentacao) AS saldo_12m,
    COUNTIF(b.saldo_movimentacao > 0) AS n_admissoes,
    APPROX_QUANTILES(
      IF(b.saldo_movimentacao > 0 AND b.salario_mensal > 0, b.salario_mensal, NULL),
      100 IGNORE NULLS
    ) AS sal_quantis
  FROM base b
  JOIN municipio m USING (id_municipio)
  CROSS JOIN ano_mais_recente a
  WHERE b.ano = a.ano_max
  GROUP BY m.id_mesorregiao, m.nome_mesorregiao, m.sigla_uf
  HAVING ABS(saldo_12m) >= 30
)

SELECT
  (SELECT ano_max FROM ano_mais_recente) AS ano_referencia,
  id_mesorregiao,
  nome_mesorregiao,
  sigla_uf_meso,
  saldo_12m,
  n_admissoes,
  IF(n_admissoes >= 50, sal_quantis[OFFSET(50)], NULL) AS salario_mediano,
  IF(n_admissoes >= 50, sal_quantis[OFFSET(25)], NULL) AS salario_p25,
  IF(n_admissoes >= 50, sal_quantis[OFFSET(75)], NULL) AS salario_p75
FROM agg
ORDER BY saldo_12m DESC
LIMIT 30;
