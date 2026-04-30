-- Indicador: cob_matriculas_ept_per_jovem
-- Recortes: total_estado + rede_estadual
-- Pendência: validar nomes de coluna após primeira execução com GCP_SA_KEY
--
-- Lógica:
--   numerador = matrículas EPT (integrada + concomitante + subsequente) no UF, ano
--   denominador = pop 15-29 do UF, ano (PNAD)
--   resultado = (numerador / denominador) * 1000

WITH matriculas_ept AS (
  SELECT
    sigla_uf,
    ano,
    dependencia_administrativa,
    COUNT(*) AS qtd_matriculas
  FROM `basedosdados.br_inep_censo_escolar.matricula`
  WHERE ano BETWEEN 2020 AND 2024
    AND tipo_oferta IN ('integrada', 'concomitante', 'subsequente')  -- validar nomes pós-GCP
    AND sigla_uf = '{UF}'
  GROUP BY sigla_uf, ano, dependencia_administrativa
),

pop_jovem AS (
  SELECT
    sigla_uf,
    ano,
    SUM(peso) AS pop_15_29
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE ano BETWEEN 2020 AND 2024
    AND idade BETWEEN 15 AND 29
    AND sigla_uf = '{UF}'
  GROUP BY sigla_uf, ano
)

SELECT
  m.sigla_uf,
  m.ano,
  -- total_estado: agrega todas dependências
  SUM(m.qtd_matriculas) * 1000.0 / p.pop_15_29 AS valor_total_estado,
  -- rede_estadual: dependencia=2
  SUM(CASE WHEN m.dependencia_administrativa = 2 THEN m.qtd_matriculas ELSE 0 END) * 1000.0 / p.pop_15_29 AS valor_rede_estadual
FROM matriculas_ept m
JOIN pop_jovem p USING (sigla_uf, ano)
GROUP BY m.sigla_uf, m.ano, p.pop_15_29
ORDER BY m.ano;
