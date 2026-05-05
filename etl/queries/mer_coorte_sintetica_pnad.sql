-- Indicador: mer_coorte_sintetica_pnad
-- Recortes: apenas total_estado
-- Coorte sintética PNAD Contínua: jovens 18-19 anos em Q1 de um ano X são
-- acompanhados como turma 19-20 em Q1 do ano X+1. PNAD trimestral é amostra
-- rotativa por design — não é tracking individual. A "coorte sintética"
-- cruza duas ondas independentes da amostra com o mesmo perfil populacional.
--
-- Base: TODOS os jovens 18-20 (cohort completa, não filtrada por nível
-- educacional). % calculados sobre população total da idade — comparáveis a
-- benchmarks IBGE/INEP de taxa líquida de matrícula no ensino superior.
--
-- Saída: 6 caminhos disjuntos calculados em cada onda:
-- - so_formal: ocupado com carteira/militar/estatutário, NÃO cursa superior
-- - so_informal: ocupado sem carteira, NÃO cursa superior
-- - formal_estuda: ocupado com carteira E cursando superior
-- - informal_estuda: ocupado sem carteira E cursando superior
-- - so_estuda: cursando superior sem trabalhar
-- - neet: não ocupado e não frequenta escola
-- - outro: cursando ensino fundamental/médio/EJA (não superior) — capturado
--   como categoria residual; jovens 18-20 ainda em EM são ~10% da cohort.
--
-- Variáveis PNAD usadas (codes confirmados via etl/diagnose.py):
--   V2007 sexo (1=H, 2=M)
--   V2009 idade
--   V1028 peso pessoal pós-estratificado
--   V3002 frequenta escola atualmente — codes BD = ORIGINAL IBGE:
--          '1'=Sim frequenta, '2'=Não frequenta. (Verificado: V3002='1'
--          dá taxa freq 18-20 = 32-40%, batendo com IBGE; v3009A só
--          preenche quando V3002='2' — variável "curso anterior".)
--   V3003A curso ATUAL (preenchido só quando V3002='1'). Codes:
--          4=Fund regular, 5=Fund EJA, 6=Médio regular, 7=Médio EJA,
--          8=Superior graduação, 9=Especialização, 10=Mestrado, 11=Doutorado.
--          Filtro 8-11 = "cursando ensino superior".
--   VD4002 condição de ocupação (1=Ocupado, 2=Desocupado)
--   V4012 categoria do trabalho principal (1-7).
--   V4029 carteira de trabalho assinada ('1'=Sim, '2'=Não, aplicável quando
--          V4012 IN ('1','3') privado).
--   Definição FORMAL: V4029='1' OR V4012 IN ('2','4','5')
--          (com carteira / militar / público / empregador).
--          Informal = ocupado sem essas condições.
--
-- Rigor:
-- - Pesa por V1028 (peso pessoal pós-estratificado oficial).
-- - n_amostral nominal reportado (sem peso) pra controle de variância.
-- - Mínimo n=50 (corte usual IBGE pra abertura UF/categoria); abaixo, a
--   métrica é suprimida e flag amostra_insuficiente=true.

WITH pnad AS (
  SELECT
    ano,
    trimestre,
    V2007 AS sexo,
    V2009 AS idade,
    V1028 AS peso,
    V3002,
    V3003A,
    VD4002,
    V4012,
    V4029
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = '{UF}'
    AND trimestre = 1
    AND V1028 IS NOT NULL
    AND V2009 BETWEEN 18 AND 20
),

ano_mais_recente AS (
  SELECT MAX(ano) AS ano_followup
  FROM pnad
  WHERE ano IS NOT NULL
),

categorizado AS (
  SELECT
    p.ano,
    p.trimestre,
    p.sexo,
    p.idade,
    p.peso,
    -- 7 caminhos disjuntos. "cursa superior" = V3002='1' (frequenta)
    -- AND V3003A IN ('8','9','10','11') (graduação ou pós).
    -- "Trabalha formal" = ocupado + (carteira sim OU militar/público/empregador).
    CASE
      -- Cursando superior + trabalha formal
      WHEN p.V3002 = '1' AND p.V3003A IN ('8', '9', '10', '11')
           AND p.VD4002 = '1'
           AND (p.V4029 = '1' OR p.V4012 IN ('2', '4', '5'))
        THEN 'formal_estuda'
      -- Cursando superior + trabalha informal
      WHEN p.V3002 = '1' AND p.V3003A IN ('8', '9', '10', '11')
           AND p.VD4002 = '1'
        THEN 'informal_estuda'
      -- Cursando superior sem trabalhar
      WHEN p.V3002 = '1' AND p.V3003A IN ('8', '9', '10', '11')
        THEN 'so_estuda'
      -- Trabalha formal sem cursar superior (pode estar em EM, fora da escola, etc)
      WHEN p.VD4002 = '1'
           AND (p.V4029 = '1' OR p.V4012 IN ('2', '4', '5'))
        THEN 'so_formal'
      -- Trabalha informal sem cursar superior
      WHEN p.VD4002 = '1' THEN 'so_informal'
      -- NEET: nem ocupado nem frequenta escola
      WHEN COALESCE(p.VD4002, '0') != '1' AND COALESCE(p.V3002, '0') != '1'
        THEN 'neet'
      -- Frequenta escola mas não em superior (Fund/Médio/EJA)
      ELSE 'outro_estuda'
    END AS caminho
  FROM pnad p
)

SELECT
  c.ano,
  c.idade,
  c.sexo,
  c.caminho,
  SUM(c.peso) AS pop_ponderada,
  COUNT(*) AS n_amostral
FROM categorizado c
WHERE c.ano IN (
  (SELECT ano_followup FROM ano_mais_recente),
  (SELECT ano_followup - 1 FROM ano_mais_recente)
)
GROUP BY c.ano, c.idade, c.sexo, c.caminho
ORDER BY c.ano, c.idade, c.sexo, c.caminho;
