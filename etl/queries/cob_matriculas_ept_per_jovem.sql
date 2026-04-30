-- Indicador: cob_matriculas_ept_per_jovem
-- Recortes: total_estado + rede_estadual
-- Métrica: matrículas EPT × 1000 / pop 15-29 do estado
--
-- Numerador: SUM(quantidade_matricula_medio_tecnico + quantidade_matricula_eja_medio_tecnico) por escola
-- Denominador: pop 15-29 ponderada por V1028 (PNAD Contínua), média anual de trimestres
-- Caveat: escolas com EPT subsequente isolada não aparecem nos campos agregados de EM —
-- subseq. típico do IF/ETEC tem matricula registrada via matricula.id_curso_educ_profissional NOT NULL
-- mas sem etapa de EM, então fica fora deste somatório. Tratado num indicador separado de subsequente.

WITH matriculas_ept_escola AS (
  SELECT
    sigla_uf,
    ano,
    rede,
    SUM(COALESCE(quantidade_matricula_medio_tecnico, 0)
        + COALESCE(quantidade_matricula_eja_medio_tecnico, 0)) AS qtd_ept
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE ano BETWEEN 2020 AND 2024
    AND sigla_uf = '{UF}'
  GROUP BY sigla_uf, ano, rede
),

ept_total AS (
  SELECT sigla_uf, ano, SUM(qtd_ept) AS total_estado
  FROM matriculas_ept_escola
  GROUP BY sigla_uf, ano
),

ept_estadual AS (
  SELECT sigla_uf, ano, SUM(qtd_ept) AS rede_estadual
  FROM matriculas_ept_escola
  WHERE rede = '2'
  GROUP BY sigla_uf, ano
),

pop_jovem AS (
  SELECT
    sigla_uf,
    ano,
    SUM(V1028) / 4.0 AS pop_15_29  -- média de 4 trimestres
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE ano BETWEEN 2020 AND 2024
    AND V2009 BETWEEN 15 AND 29
    AND sigla_uf = '{UF}'
  GROUP BY sigla_uf, ano
)

SELECT
  COALESCE(t.ano, e.ano) AS ano,
  ROUND(t.total_estado * 1000.0 / NULLIF(p.pop_15_29, 0), 2) AS valor_total_estado,
  ROUND(e.rede_estadual * 1000.0 / NULLIF(p.pop_15_29, 0), 2) AS valor_rede_estadual
FROM ept_total t
LEFT JOIN ept_estadual e USING (sigla_uf, ano)
LEFT JOIN pop_jovem p USING (sigla_uf, ano)
ORDER BY ano;
