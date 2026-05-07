-- Indicador: mer_aderencia_eixo_cbo
-- Recortes: apenas total_estado
-- Calcula a aderência entre OFERTA (matrículas EPT por eixo CNCT) e
-- DEMANDA (saldo CAGED em CBO 3xxxx mapeada ao eixo) por estado.
--
-- Pergunta-resposta: o sistema EPT estadual está formando técnicos
-- nos eixos onde o mercado realmente contrata? Onde está formando
-- a mais (over-supply, egresso vai pra concorrência subempregada)?
-- Onde está formando a menos (under-supply, gargalo de mão-de-obra)?
--
-- Output: 1 linha por eixo, com:
--   eixo_id, eixo_nome
--   oferta_n: matrículas EPT 2020 no eixo (Censo Escolar)
--   oferta_pct: % do total estadual de matrículas EPT
--   demanda_saldo: saldo CAGED 12m em CBO 3xxxx do eixo
--   demanda_n_admissoes: admissões CAGED 12m em CBO 3xxxx do eixo
--   demanda_pct: % do total estadual de saldo CAGED em CBO 3xxxx
--   gap_pp: oferta_pct - demanda_pct (positivo = over-supply)
--
-- Mapping eixo → CBO documentado em etl/reference/eixo_cnct_to_cbo3.md.
-- Eixos sem demanda CBO 3xxxx mensurável (2 Educ Social, 8 Militar)
-- ficam com demanda_n=0 e flag sem_demanda=true. Eixo 9 (Prod
-- Alimentícia) tem CBO 325205 (Téc Alimentos) + 325005 (Enólogo)
-- como CBOs técnicas formais — captura pequena mas mensurável.
--
-- Mapping algorítmico INEP: eixo_id = DIV(id_curso_educ_profissional, 1000).
-- Verificado contra Caderno de Conceitos INEP 2022 (pp. 93-99).
--
-- Rigor:
-- - Censo Escolar usa último ano disponível na BD (2020).
-- - CAGED usa último ano disponível.
-- - Eixos com matrículas < 100 OU saldo absoluto < 30 ficam suprimidos
--   em flag amostra_insuficiente=true mas linha aparece no output.
-- - Excluído subgrupo CBO 33xxxx (Técnicos da educação) — coerência
--   com mer_demanda_cbo_top e mer_demanda_mesorregiao.
-- - Salário não entra aqui (focar em volume; salário fica em
--   mer_demanda_cbo_top).

WITH censo_oferta AS (
  -- Tabela `turma` (último ano disponível 2024) tem `quantidade_matriculas`
  -- por turma e id_curso_educacao_profissional. A tabela `matricula` foi
  -- descontinuada na BD em 2020. Usar `turma` resolve a defasagem
  -- (1 ano vs CAGED 2025 em vez de 5 anos).
  SELECT
    DIV(SAFE_CAST(id_curso_educacao_profissional AS INT64), 1000) AS eixo_id,
    SUM(quantidade_matriculas) AS n_matriculas
  FROM `basedosdados.br_inep_censo_escolar.turma`
  WHERE sigla_uf = @uf
    AND ano = (
      SELECT MAX(ano)
      FROM `basedosdados.br_inep_censo_escolar.turma`
      WHERE sigla_uf = @uf AND id_curso_educacao_profissional IS NOT NULL
    )
    AND id_curso_educacao_profissional IS NOT NULL
    AND quantidade_matriculas IS NOT NULL
  GROUP BY eixo_id
),

oferta_total AS (
  SELECT SUM(n_matriculas) AS total_matriculas FROM censo_oferta
),

caged_base AS (
  -- Filtro: CBO 3xxxx (Técnicos Nível Médio), exceto 33xxxx
  -- (Técnicos da educação — exclusão acordada com mer_demanda_cbo_top).
  -- Recorte estritamente técnico-formal — coerência metodológica entre
  -- eixos. Demanda operacional (CBO 5xxxx-9xxxx) é majoritariamente
  -- atendida por FIC do Sistema S (SENAI/SENAR/SENAC), fora do escopo
  -- da rede EPT estadual. Cruzar EPT com CBO operacional confunde
  -- demanda EPT com demanda por trabalho qualificado em geral.
  --   Eixo 8 Militar: CAGED não cobre FFAA (estatutário) — sem solução.
  --   Eixo 2 Educ/Social: CBO 33xxxx filtrado — sem dado mensurável.
  SELECT
    cbo_2002,
    saldo_movimentacao
  FROM `basedosdados.br_me_caged.microdados_movimentacao`
  WHERE sigla_uf = @uf
    AND ano = (
      SELECT MAX(ano) FROM `basedosdados.br_me_caged.microdados_movimentacao`
    )
    AND cbo_2002 IS NOT NULL
    AND cbo_2002 LIKE '3%'
    AND cbo_2002 NOT LIKE '33%'
),

caged_eixo AS (
  -- Mapping CBO → eixo INEP. Cada CBO em UM único eixo.
  -- Documentado em etl/reference/eixo_cnct_to_cbo3.md.
  SELECT
    CASE
      -- Eixo 13 Segurança (CBO específico, prioridade alta)
      WHEN cbo_2002 = '351605' THEN 13
      -- Eixo 5 Turismo (CBO específico, prioridade alta)
      WHEN cbo_2002 = '354820' THEN 5
      -- Eixo 9 Produção Alimentícia — CBOs técnicas formais
      --   325205 = Téc Alimentos (egresso CNCT 9120 Téc Alimentos)
      --   325005 = Enólogo (egresso CNCT 9127 Téc Vitivinicultura)
      -- Precede o catch-all '325%' → eixo 1 (Saúde) abaixo.
      WHEN cbo_2002 IN ('325205', '325005') THEN 9
      -- Eixo 1 Ambiente e Saúde
      WHEN cbo_2002 LIKE '321%' OR cbo_2002 LIKE '322%' OR cbo_2002 LIKE '323%'
           OR cbo_2002 LIKE '324%' OR cbo_2002 LIKE '325%' OR cbo_2002 LIKE '326%'
        THEN 1
      -- Eixo 3 Controle e Processos Industriais
      WHEN cbo_2002 LIKE '311%' OR cbo_2002 LIKE '313%' THEN 3
      -- Eixo 6 Informação e Comunicação
      WHEN cbo_2002 LIKE '317%' THEN 6
      -- Eixo 7 Infraestrutura
      WHEN cbo_2002 LIKE '312%' OR cbo_2002 LIKE '318%' THEN 7
      -- Eixo 10 Produção Cultural e Design
      WHEN cbo_2002 LIKE '374%' OR cbo_2002 LIKE '376%' THEN 10
      -- Eixo 11 Produção Industrial
      WHEN cbo_2002 LIKE '314%' OR cbo_2002 LIKE '300%' THEN 11
      -- Eixo 12 Recursos Naturais
      WHEN cbo_2002 LIKE '301%' THEN 12
      -- Eixo 4 Gestão e Negócios (catch-all 35x e 391x, exceto 351605/354820)
      WHEN cbo_2002 LIKE '351%' OR cbo_2002 LIKE '352%' OR cbo_2002 LIKE '353%'
           OR cbo_2002 LIKE '354%' OR cbo_2002 LIKE '391%'
        THEN 4
      ELSE NULL  -- CBO sem eixo CNCT correspondente
    END AS eixo_id,
    saldo_movimentacao
  FROM caged_base
),

demanda_eixo AS (
  SELECT
    eixo_id,
    SUM(saldo_movimentacao) AS saldo,
    COUNTIF(saldo_movimentacao > 0) AS n_admissoes
  FROM caged_eixo
  WHERE eixo_id IS NOT NULL
  GROUP BY eixo_id
),

demanda_total AS (
  -- Demanda agregada usa ADMISSÕES, não saldo. Saldo subdimensiona
  -- setores de alta rotatividade (Gestão, Vendas, Comércio) — esses
  -- têm muitas admissões e muitas demissões, saldo baixo. Admissões
  -- captura "oportunidades de entrada" pra egressos EPT — proxy correto
  -- de demanda de formação. Saldo continua reportado como info.
  SELECT SUM(n_admissoes) AS total_admissoes FROM demanda_eixo
),

eixos AS (
  -- 13 eixos canônicos. Cross-join garante que todo eixo apareça
  -- mesmo sem oferta ou demanda.
  SELECT eixo_id, eixo_nome FROM UNNEST([
    STRUCT(1  AS eixo_id, 'Ambiente e Saúde' AS eixo_nome),
    STRUCT(2  AS eixo_id, 'Desenvolvimento Educacional e Social' AS eixo_nome),
    STRUCT(3  AS eixo_id, 'Controle e Processos Industriais' AS eixo_nome),
    STRUCT(4  AS eixo_id, 'Gestão e Negócios' AS eixo_nome),
    STRUCT(5  AS eixo_id, 'Turismo, Hospitalidade e Lazer' AS eixo_nome),
    STRUCT(6  AS eixo_id, 'Informação e Comunicação' AS eixo_nome),
    STRUCT(7  AS eixo_id, 'Infraestrutura' AS eixo_nome),
    STRUCT(8  AS eixo_id, 'Militar' AS eixo_nome),
    STRUCT(9  AS eixo_id, 'Produção Alimentícia' AS eixo_nome),
    STRUCT(10 AS eixo_id, 'Produção Cultural e Design' AS eixo_nome),
    STRUCT(11 AS eixo_id, 'Produção Industrial' AS eixo_nome),
    STRUCT(12 AS eixo_id, 'Recursos Naturais' AS eixo_nome),
    STRUCT(13 AS eixo_id, 'Segurança' AS eixo_nome)
  ])
)

SELECT
  e.eixo_id,
  e.eixo_nome,
  COALESCE(o.n_matriculas, 0) AS oferta_n,
  CASE WHEN ot.total_matriculas > 0
    THEN ROUND(100.0 * COALESCE(o.n_matriculas, 0) / ot.total_matriculas, 2)
    ELSE NULL END AS oferta_pct,
  COALESCE(d.saldo, 0) AS demanda_saldo,
  COALESCE(d.n_admissoes, 0) AS demanda_n_admissoes,
  CASE WHEN dt.total_admissoes > 0
    THEN ROUND(100.0 * COALESCE(d.n_admissoes, 0) / dt.total_admissoes, 2)
    ELSE NULL END AS demanda_pct,
  (SELECT MAX(ano)
     FROM `basedosdados.br_inep_censo_escolar.turma`
     WHERE sigla_uf = @uf AND id_curso_educacao_profissional IS NOT NULL
  ) AS ano_oferta_censo,
  (SELECT MAX(ano) FROM `basedosdados.br_me_caged.microdados_movimentacao`)
    AS ano_demanda_caged
FROM eixos e
LEFT JOIN censo_oferta o USING (eixo_id)
LEFT JOIN demanda_eixo d USING (eixo_id)
CROSS JOIN oferta_total ot
CROSS JOIN demanda_total dt
ORDER BY e.eixo_id;
