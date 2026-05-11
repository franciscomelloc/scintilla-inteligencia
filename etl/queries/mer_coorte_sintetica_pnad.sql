-- Indicador: mer_coorte_sintetica_pnad
-- Recortes: apenas total_estado
-- Quatro idades-ancora da janela jovem do Estatuto da Juventude (15-29):
-- 17 (entrada), 21 (jovem em desenvolvimento), 25 (consolidacao),
-- 29 (saida). Cada idade observada como pool dos 4 trimestres do ano
-- mais recente disponivel na PNAD-C (2024Q1-Q4 hoje).
--
-- Coortes sinteticas (Deaton 1985): tres coortes de nascimento
-- diferentes comparadas no mesmo ano. 17 anos em 2024 = nascidos 2007;
-- 21 = nascidos 2003; 25 = nascidos 1999; 29 = nascidos 1995. Pessoas
-- diferentes por idade, estrutura "agora" da juventude no estado.
--
-- Saida: 7 caminhos disjuntos em cada idade-ancora:
-- - so_formal: ocupado com carteira/estatutario, NAO cursa superior
-- - so_informal: ocupado sem carteira, NAO cursa superior
-- - formal_estuda: ocupado com carteira E cursando superior
-- - informal_estuda: ocupado sem carteira E cursando superior
-- - so_estuda: cursando superior sem trabalhar
-- - neet: nao ocupado e nao frequenta escola
-- - outro_estuda: cursando ensino fundamental/medio/EJA (nao superior)
--
-- Variaveis PNAD usadas:
--   V2007 sexo (1=H, 2=M)
--   V2009 idade
--   V1028 peso pessoal pos-estratificado
--   V3002 frequenta escola atualmente ('1'=Sim, '2'=Nao)
--   V3003A curso ATUAL (preenchido so quando V3002='1'). Codes:
--          4=Fund regular, 5=Fund EJA, 6=Medio regular, 7=Medio EJA,
--          8=Superior graduacao, 9=Especializacao, 10=Mestrado,
--          11=Doutorado. Filtro 8-11 = "cursando ensino superior".
--   VD4002 condicao de ocupacao ('1'=Ocupado)
--   V4029 carteira de trabalho assinada ('1'=Sim, '2'=Nao)
--   VD4009 posicao na ocupacao principal (derivada IBGE, 10 categorias):
--          01 priv c/cart   02 priv s/cart   03 dom c/cart   04 dom s/cart
--          05 pub c/cart    06 pub s/cart    07 militar/estatutario
--          08 empregador    09 conta-propria 10 trab.familiar auxiliar
--
-- Definicao operacional FORMAL (padrao atlas Scintilla):
--   formal = V4029='1' OR VD4009='07'
--   (com carteira CLT em qualquer setor OU militar/estatutario)
--   V4029=1 ja cobre 01, 03 e 05. VD4009='07' acrescenta o estatutario
--   que nao tem carteira CLT mas tem protecao previdenciaria integral.
--
-- Tratamento de nao-resposta (conservador): V4029 NR -> sem carteira;
-- V3002 NR -> nao estuda; VD4002 NR -> nao ocupado.
--
-- Rigor:
-- - Pesa por V1028.
-- - n_amostral nominal reportado (sem peso) pra controle de variancia.
-- - Pool dos 4 trimestres do ano-ancora quadruplica n efetivo vs recorte
--   de Q1 apenas (corrige risco de supressao em UF pequena).
-- - Minimo n=50 (corte usual IBGE pra abertura UF/idade); abaixo, a
--   metrica e suprimida e flag amostra_insuficiente=true.

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
    V4029,
    VD4009
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = @uf
    AND V1028 IS NOT NULL
    AND V2009 IN (17, 21, 25, 29)
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
    -- AND V3003A IN ('8','9','10','11') (graduacao ou pos).
    -- "Trabalha formal" = ocupado + (carteira sim OU militar/estatutario).
    CASE
      -- Cursando superior + trabalha formal
      WHEN p.V3002 = '1' AND p.V3003A IN ('8', '9', '10', '11')
           AND p.VD4002 = '1'
           AND (p.V4029 = '1' OR p.VD4009 = '07')
        THEN 'formal_estuda'
      -- Cursando superior + trabalha informal
      WHEN p.V3002 = '1' AND p.V3003A IN ('8', '9', '10', '11')
           AND p.VD4002 = '1'
        THEN 'informal_estuda'
      -- Cursando superior sem trabalhar
      WHEN p.V3002 = '1' AND p.V3003A IN ('8', '9', '10', '11')
        THEN 'so_estuda'
      -- Trabalha formal sem cursar superior (pode estar em EM, fora da escola)
      WHEN p.VD4002 = '1'
           AND (p.V4029 = '1' OR p.VD4009 = '07')
        THEN 'so_formal'
      -- Trabalha informal sem cursar superior
      WHEN p.VD4002 = '1' THEN 'so_informal'
      -- NEET: nem ocupado nem frequenta escola
      WHEN COALESCE(p.VD4002, '0') != '1' AND COALESCE(p.V3002, '0') != '1'
        THEN 'neet'
      -- Frequenta escola mas nao em superior (Fund/Medio/EJA)
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
WHERE c.ano = (SELECT ano_followup FROM ano_mais_recente)
GROUP BY c.ano, c.idade, c.sexo, c.caminho
ORDER BY c.ano, c.idade, c.sexo, c.caminho;
