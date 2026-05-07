-- Indicador: qua_razao_aluno_professor_ept
-- Recortes: total_estado + rede_estadual
-- Polaridade: INVERSA (razão menor é melhor)
-- Definição: alunos EPT / docentes EPT, agregado por escola.
--
-- Fonte: tabela `escola` com agregados de docente e matrícula por etapa.
-- A tabela `docente` foi descontinuada na BD após 2020 (mesma janela de
-- `matricula`). Migração para `escola` agregada, que segue ativa até 2024.
--
-- LIMITAÇÃO METODOLÓGICA: contagem de docentes do `escola` conta cada docente
-- por escola onde ele atua. Se um docente leciona em 2 escolas, é contado 2x
-- (não há deduplicação a nível UF). Idem para alunos: cada matrícula é uma
-- contagem (sem dedup por id_aluno). Razão é boa para benchmark inter-UF
-- (mesmo viés em todas as UFs).

WITH escolas_ept AS (
  SELECT
    ano,
    rede,
    quantidade_matricula_medio_tecnico
      + quantidade_matricula_profissional_tecnica_concomitante
      + quantidade_matricula_profissional_tecnica_subsequente
      + quantidade_matricula_eja_medio_tecnico AS qtd_alunos_ept,
    quantidade_docente_profissional_tecnica AS qtd_docentes_ept
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = @uf
    AND ano = (
      SELECT MAX(ano)
      FROM `basedosdados.br_inep_censo_escolar.escola`
      WHERE sigla_uf = @uf
    )
    AND etapa_ensino_profissional_tecnica = 1
)

SELECT
  ano,
  SUM(qtd_alunos_ept) AS alunos_ept_total,
  SUM(qtd_docentes_ept) AS docentes_ept_total,
  SUM(IF(rede = '2', qtd_alunos_ept, 0)) AS alunos_ept_estadual,
  SUM(IF(rede = '2', qtd_docentes_ept, 0)) AS docentes_ept_estadual,
  ROUND(SUM(qtd_alunos_ept) * 1.0 / NULLIF(SUM(qtd_docentes_ept), 0), 2) AS razao_total_estado,
  ROUND(SUM(IF(rede = '2', qtd_alunos_ept, 0)) * 1.0
        / NULLIF(SUM(IF(rede = '2', qtd_docentes_ept, 0)), 0), 2) AS razao_rede_estadual
FROM escolas_ept
GROUP BY ano
ORDER BY ano;
