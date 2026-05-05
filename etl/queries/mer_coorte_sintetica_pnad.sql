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
--   V3002 frequenta escola (1=Sim)
--   V3009A nível atual de ensino (5='Superior - graduação', 6='Especialização',
--          7='Mestrado', 8='Doutorado')
--   VD3004 nível mais elevado alcançado (5='Médio completo', 6='Superior incompleto',
--          7='Superior completo')
--   VD4002 condição de ocupação (1=Ocupado, 2=Desocupado)
--   VD4007 tipo de empregador / posição (1='Empregado com carteira',
--          7='Trab. doméstico com carteira', 8='Militar', 9='Estatutário';
--          demais = informal/conta-própria)
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
      WHEN p.V3002 = '1' AND p.V3009A IN ('5', '6', '7', '8')
           AND p.VD4002 = '1' AND p.VD4007 IN ('1', '7', '8', '9') THEN 'formal_estuda'
      WHEN p.V3002 = '1' AND p.V3009A IN ('5', '6', '7', '8')
           AND p.VD4002 = '1' THEN 'informal_estuda'
      -- Cursando superior sem trabalhar
      WHEN p.V3002 = '1' AND p.V3009A IN ('5', '6', '7', '8') THEN 'so_estuda'
      -- Trabalha sem cursar superior
      WHEN p.VD4002 = '1' AND p.VD4007 IN ('1', '7', '8', '9') THEN 'so_formal'
      WHEN p.VD4002 = '1' THEN 'so_informal'
      -- Não trabalha, não cursa superior, não frequenta nada
      WHEN COALESCE(p.VD4002, '0') != '1' AND COALESCE(p.V3002, '0') != '1' THEN 'neet'
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
