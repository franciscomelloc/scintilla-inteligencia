-- Indicador: mer_desfecho_29_pnad
-- Recortes: apenas total_estado, decomposto em 4 grupos raca x sexo
-- Replica adaptada da Figura 19 do atlas Scintilla "Juventudes em Movimento":
-- distribuicao da subcoorte de 29 anos (ultimo ano do Estatuto da Juventude)
-- por nivel de especializacao da ocupacao principal (CBO 2002), estudando-
-- nao-ocupado, e sem trabalho e sem estudo.
--
-- 5 desfechos disjuntos (soma 100% por grupo demografico):
-- - alta: ocupado, CBO grande grupo (GG) 1 ou 2 (membros do poder publico,
--         dirigentes, profissionais das ciencias e artes)
-- - media: ocupado, CBO GG 3 ou 4 (tecnicos nivel medio, servicos administrativos)
-- - baixa: ocupado, CBO GG 0 ou 5-9 (forcas armadas, servicos, agropecuaria,
--          producao industrial, manutencao)
-- - estudando: nao ocupado + cursa qualquer nivel (V3002='1')
-- - neet: nao ocupado + nao cursa
--
-- 4 grupos demograficos (raca x sexo): HB, HN, MB, MN.
-- Amarela, Indigena e Ignorada (1% da coorte) suprimidas conforme atlas.
--
-- Variaveis PNAD usadas:
--   V2007 sexo (1=H, 2=M)
--   V2009 idade
--   V2010 raca (1=branca, 2=preta, 3=amarela, 4=parda, 5=indigena, 9=ignorada)
--   V1028 peso pessoal pos-estratificado
--   V3002 frequenta escola atualmente ('1'=Sim)
--   VD4002 condicao de ocupacao ('1'=Ocupado)
--   V4010 CBO 2002 da ocupacao principal (4 digitos). GG = primeiro digito.
--
-- Pool dos 4 trimestres do ano mais recente da PNAD-C.
-- Minimo n=50 por grupo demografico (corte IBGE). UFs com bottleneck < 50
-- entram com supressao por grupo no JSON.

WITH pnad AS (
  SELECT
    ano,
    trimestre,
    V2007 AS sexo,
    V2009 AS idade,
    V2010 AS raca,
    V1028 AS peso,
    V3002,
    VD4002,
    V4010,
    SAFE_CAST(SUBSTR(LPAD(V4010, 4, '0'), 1, 1) AS INT64) AS cbo_gg
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE sigla_uf = @uf
    AND V1028 IS NOT NULL
    AND V2009 = 29
),

ano_mais_recente AS (
  SELECT MAX(ano) AS ano_ref FROM pnad WHERE ano IS NOT NULL
),

categorizado AS (
  SELECT
    p.ano,
    p.trimestre,
    p.sexo,
    -- Raca reduzida: 1=branca, 2/4=negra (preta+parda); 3/5/9 NULL (suprimidos)
    CASE
      WHEN p.raca = '1' THEN 'branca'
      WHEN p.raca IN ('2', '4') THEN 'negra'
      ELSE NULL
    END AS raca,
    p.peso,
    CASE
      -- Ocupado, alta especializacao (CBO GG 1-2)
      WHEN p.VD4002 = '1' AND p.cbo_gg IN (1, 2) THEN 'alta'
      -- Ocupado, media especializacao (CBO GG 3-4)
      WHEN p.VD4002 = '1' AND p.cbo_gg IN (3, 4) THEN 'media'
      -- Ocupado, baixa especializacao (CBO GG 0, 5-9)
      WHEN p.VD4002 = '1' THEN 'baixa'
      -- Nao ocupado, cursando qualquer nivel
      WHEN COALESCE(p.VD4002, '0') != '1' AND p.V3002 = '1' THEN 'estudando'
      -- Nao ocupado, nao cursa nada
      ELSE 'neet'
    END AS desfecho
  FROM pnad p
)

SELECT
  c.ano,
  c.sexo,
  c.raca,
  c.desfecho,
  SUM(c.peso) AS pop_ponderada,
  COUNT(*) AS n_amostral
FROM categorizado c
WHERE c.ano = (SELECT ano_ref FROM ano_mais_recente)
  AND c.raca IS NOT NULL
GROUP BY c.ano, c.sexo, c.raca, c.desfecho
ORDER BY c.ano, c.sexo, c.raca, c.desfecho;
