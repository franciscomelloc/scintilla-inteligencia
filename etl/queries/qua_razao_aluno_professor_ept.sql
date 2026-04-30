-- Indicador: qua_razao_aluno_professor_ept
-- Recortes: total_estado + rede_estadual
-- Polaridade: INVERSA (razão menor é melhor)
--
-- Definição inclusiva: docente conta se atua em ≥1 turma com matrícula EPT no ano.

WITH matriculas_ept AS (
  SELECT
    ano,
    dependencia_administrativa,
    id_turma,
    id_escola,
    COUNT(*) AS qtd_alunos
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')
    AND sigla_uf = '{UF}'
  GROUP BY ano, dependencia_administrativa, id_turma, id_escola
),

docentes_ept AS (
  -- docentes que dão aula em pelo menos uma turma de matrícula EPT
  SELECT DISTINCT
    d.ano,
    d.id_docente,
    m.dependencia_administrativa
  FROM `basedosdados.br_inep_censo_escolar.docente` d
  JOIN matriculas_ept m
    ON d.id_turma = m.id_turma AND d.ano = m.ano
  WHERE d.sigla_uf = '{UF}'
)

SELECT
  m.ano,
  -- total_estado
  SUM(m.qtd_alunos) * 1.0 / COUNT(DISTINCT d.id_docente) AS razao_total_estado,
  -- rede_estadual
  SUM(CASE WHEN m.dependencia_administrativa = 2 THEN m.qtd_alunos ELSE 0 END) * 1.0 /
    NULLIF(COUNT(DISTINCT CASE WHEN d.dependencia_administrativa = 2 THEN d.id_docente END), 0) AS razao_rede_estadual
FROM matriculas_ept m
CROSS JOIN docentes_ept d
WHERE m.ano = d.ano
GROUP BY m.ano
ORDER BY m.ano;
