-- Indicador: qua_aderencia_docente_ept
-- Aderência da formação dos docentes que ensinam disciplina profissionalizante.
--
-- Universo: docentes com disciplina_profissionalizante='1' E vinculados a turma
-- com id_curso_educ_profissional definido (curso EPT real). Distinct por id_docente
-- — docente em múltiplas turmas conta 1 vez.
--
-- Métricas calculadas em 2 recortes (total_estado + rede_estadual):
--   pct_superior      % com ao menos 1 curso superior cadastrado (id_curso_1 NOT NULL)
--   pct_pos_lato      % com especialização (especializacao='1')
--   pct_pos_stricto   % com mestrado OU doutorado
--
-- Limitação: aderência por área (curso superior compatível com o eixo CNCT do
-- curso técnico ensinado) exige mapping CINE-Brasil/OCDE → eixo CNCT, ainda
-- não construído. Esse card mede FORMAÇÃO BRUTA (tem superior? tem pós?), não
-- compatibilidade de área. Documentado no caveat.

WITH ano_max AS (
  SELECT MAX(ano) AS ano_ref
  FROM `basedosdados.br_inep_censo_escolar.docente`
  WHERE sigla_uf = '{UF}'
    AND disciplina_profissionalizante = '1'
    AND id_curso_educ_profissional IS NOT NULL
),

base AS (
  SELECT
    d.id_docente,
    d.rede,
    d.id_curso_1,
    d.especializacao,
    d.mestrado,
    d.doutorado
  FROM `basedosdados.br_inep_censo_escolar.docente` d
  CROSS JOIN ano_max a
  WHERE d.sigla_uf = '{UF}'
    AND d.ano = a.ano_ref
    AND d.disciplina_profissionalizante = '1'
    AND d.id_curso_educ_profissional IS NOT NULL
),

-- Colapsa por id_docente: 1 linha por docente. Formação não muda entre turmas no
-- mesmo ano, então MAX captura presença da credencial.
distintos AS (
  SELECT
    id_docente,
    MAX(IF(rede = '2', 1, 0)) AS in_estadual,
    MAX(IF(id_curso_1 IS NOT NULL, 1, 0)) AS tem_superior,
    MAX(IF(especializacao = '1', 1, 0)) AS tem_lato,
    MAX(IF(mestrado = '1' OR doutorado = '1', 1, 0)) AS tem_stricto
  FROM base
  GROUP BY id_docente
)

SELECT
  (SELECT ano_ref FROM ano_max) AS ano,

  -- Total estado
  COUNT(*) AS docentes_total,
  ROUND(100.0 * SUM(tem_superior) / NULLIF(COUNT(*), 0), 2) AS pct_superior_total,
  ROUND(100.0 * SUM(tem_lato) / NULLIF(COUNT(*), 0), 2) AS pct_pos_lato_total,
  ROUND(100.0 * SUM(tem_stricto) / NULLIF(COUNT(*), 0), 2) AS pct_pos_stricto_total,

  -- Rede estadual
  SUM(in_estadual) AS docentes_estadual,
  ROUND(100.0 * SUM(IF(in_estadual = 1, tem_superior, 0)) / NULLIF(SUM(in_estadual), 0), 2) AS pct_superior_estadual,
  ROUND(100.0 * SUM(IF(in_estadual = 1, tem_lato, 0)) / NULLIF(SUM(in_estadual), 0), 2) AS pct_pos_lato_estadual,
  ROUND(100.0 * SUM(IF(in_estadual = 1, tem_stricto, 0)) / NULLIF(SUM(in_estadual), 0), 2) AS pct_pos_stricto_estadual

FROM distintos;
