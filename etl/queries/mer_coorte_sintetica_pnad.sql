-- Indicador: mer_coorte_sintetica_pnad
-- Recortes: apenas total_estado
-- Coorte sintética PNAD Contínua: jovens 18-19 anos com EM completo em
-- Q1 de um ano X são acompanhados como turma 19-20 em Q1 do ano X+1.
-- A PNAD trimestral é amostra rotativa por design — não é tracking
-- individual. A "coorte sintética" cruza duas ondas independentes da
-- amostra com o mesmo perfil populacional.
--
-- Saída: 6 caminhos disjuntos calculados em cada onda (categorização que
-- separa "trabalha + estuda superior" de "só estuda" — necessário porque
-- ~70% dos universitários 18-24 brasileiros são economicamente ativos):
-- - so_formal: ocupado com carteira/militar/estatutário, não cursa superior
-- - so_informal: ocupado sem carteira, não cursa superior
-- - formal_estuda: ocupado com carteira E cursando superior
-- - informal_estuda: ocupado sem carteira E cursando superior
-- - so_estuda: cursando superior sem trabalhar
-- - neet: não ocupado e não frequenta escola
-- (residual "outro" capturado mas tipicamente <2%: cursando EJA-médio, fora do
--  filtro VD3004>=5 mas que escapou; ou ocupado sem definição clara de carteira.)
--
-- Variáveis PNAD usadas:
--   V2007 sexo (1=H, 2=M)
--   V2009 idade
--   V1028 peso pessoal pós-estratificado
--   V3002 frequenta escola atualmente — codes na BD: '1'=NÃO frequenta,
--          '2'=frequenta. ATENÇÃO: codificação invertida vs convenção
--          comum (1=Sim/2=Não). Confirmado via diagnose: jovens com
--          V3009A='10' (cursando graduação) sempre têm V3002='2'.
--   V3009A nível atual de ensino — codes encontrados na BD via diagnose
--          (etl/diagnose.py query pnad_v3009a_18_20_2024_2025):
--          7=Médio regular, 8=Médio EJA, 10=Superior graduação,
--          11=Especialização, 12=Mestrado, 13=Doutorado.
--          Filtro 10-13 = "cursando ensino superior" (graduação + pós).
--   VD3004 nível mais elevado alcançado (5='Médio completo', 6='Superior incompleto',
--          7='Superior completo'). Filtro 5-7 inclui quem cursa superior agora.
--   VD4002 condição de ocupação (1=Ocupado, 2=Desocupado)
--   VD4007 posição na ocupação — codes 1-4 na BD (agregados oficiais):
--          1=Empregado com carteira, 2=Doméstico, 3=Empregado sem carteira,
--          4=Estatutário/militar. Formal estrito = ('1','4'); doméstico ('2')
--          é ambíguo (carteira opcional) — classificado como informal por
--          conservadorismo.
--
-- Rigor:
-- - Pesa por V1028 (peso pessoal pós-estratificado oficial).
-- - n_amostral nominal reportado (sem peso) pra controle de variância.
-- - Mínimo n=50 (corte usual de IBGE pra abertura UF/categoria); abaixo,
--   a métrica é suprimida e flag amostra_insuficiente=true.
-- - "EM completo" inclui EM regular + EM técnico misturados — limitação
--   estrutural da PNAD trimestral (não há variável que isole técnico).

WITH pnad AS (
  SELECT
    ano,
    trimestre,
    V2007 AS sexo,
    V2009 AS idade,
    V1028 AS peso,
    V3002,
    V3009A,
    VD3004,
    VD4002,
    VD4007
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = '{UF}'
    AND trimestre = 1
    AND V1028 IS NOT NULL
    AND V2009 BETWEEN 18 AND 20
    AND VD3004 IN ('5', '6', '7')   -- EM completo ou mais
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
    -- 6 caminhos disjuntos (mutuamente exclusivos, soma <= 100%)
    CASE
      -- Cursando superior + trabalha
      WHEN p.V3002 = '2' AND p.V3009A IN ('10', '11', '12', '13')
           AND p.VD4002 = '1' AND p.VD4007 IN ('1', '4') THEN 'formal_estuda'
      WHEN p.V3002 = '2' AND p.V3009A IN ('10', '11', '12', '13')
           AND p.VD4002 = '1' THEN 'informal_estuda'
      -- Cursando superior sem trabalhar
      WHEN p.V3002 = '2' AND p.V3009A IN ('10', '11', '12', '13') THEN 'so_estuda'
      -- Trabalha sem cursar superior
      WHEN p.VD4002 = '1' AND p.VD4007 IN ('1', '4') THEN 'so_formal'
      WHEN p.VD4002 = '1' THEN 'so_informal'
      -- Não trabalha, não cursa superior, não frequenta nada
      WHEN COALESCE(p.VD4002, '0') != '1' AND COALESCE(p.V3002, '0') != '2' THEN 'neet'
      ELSE 'outro'
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
