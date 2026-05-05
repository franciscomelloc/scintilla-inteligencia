-- Indicador: cob_perfil_alunos
-- Perfil sociodemográfico das escolas que oferecem EPT — sexo, raça/cor, idade.
--
-- Fonte: tabela `escola` com agregados sociodemográficos por escola.
-- A tabela `matricula` (que tinha sexo/idade por aluno) foi descontinuada na
-- BD após 2020. Aqui usamos os agregados de `escola`, filtrando escolas que
-- ofertam EPT (etapa_ensino_profissional_tecnica = 1) e somando seus contadores.
--
-- LIMITAÇÃO METODOLÓGICA: agregados são da escola toda, não exclusivamente
-- da matrícula EPT. Em escolas mistas (EM propedêutico + técnico), o perfil
-- captura também alunos não-EPT da mesma escola. Mais fiel para escolas
-- 100% técnicas (Senai, IFs, escolas estaduais técnicas dedicadas).

WITH escolas_ept AS (
  SELECT
    ano,
    rede,
    quantidade_matricula_medio_tecnico,
    quantidade_matricula_profissional_tecnica_concomitante,
    quantidade_matricula_profissional_tecnica_subsequente,
    quantidade_matricula_feminino,
    quantidade_matricula_masculino,
    quantidade_matricula_nao_declarada,
    quantidade_matricula_branca,
    quantidade_matricula_preta,
    quantidade_matricula_parda,
    quantidade_matricula_amarela,
    quantidade_matricula_indigena,
    quantidade_matricula_idade_15_17,
    quantidade_matricula_idade_18,
    quantidade_matricula_medio_tecnico
      + quantidade_matricula_profissional_tecnica_concomitante
      + quantidade_matricula_profissional_tecnica_subsequente
      + quantidade_matricula_eja_medio_tecnico AS qtd_ept_escola,
    quantidade_matricula_educacao_basica AS qtd_total_escola
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = '{UF}'
    AND ano = (
      SELECT MAX(ano)
      FROM `basedosdados.br_inep_censo_escolar.escola`
      WHERE sigla_uf = '{UF}'
    )
    AND etapa_ensino_profissional_tecnica = 1
    AND COALESCE(quantidade_matricula_educacao_basica, 0) > 0
)

SELECT
  ano,
  rede,
  COUNT(*) AS qtd_escolas_ept,
  SUM(qtd_ept_escola) AS total_matriculas_ept,
  SUM(qtd_total_escola) AS total_matriculas_escolas_ept,
  SUM(quantidade_matricula_feminino) AS qtd_fem,
  SUM(quantidade_matricula_masculino) AS qtd_masc,
  SUM(quantidade_matricula_nao_declarada) AS qtd_sexo_nd,
  SUM(quantidade_matricula_branca) AS qtd_branca,
  SUM(quantidade_matricula_preta) AS qtd_preta,
  SUM(quantidade_matricula_parda) AS qtd_parda,
  SUM(quantidade_matricula_amarela) AS qtd_amarela,
  SUM(quantidade_matricula_indigena) AS qtd_indigena,
  SUM(quantidade_matricula_idade_15_17) AS qtd_idade_15_17,
  SUM(quantidade_matricula_idade_18) AS qtd_idade_18_mais
FROM escolas_ept
GROUP BY ano, rede
ORDER BY ano, rede;
