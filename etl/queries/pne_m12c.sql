-- Indicador: pne_m12c
-- PNE Meta 12.c · % EJA articulada à educação profissional sobre EJA total
-- EJA-Médio articulada: quantidade_matricula_eja_medio_tecnico
-- EJA-Médio total: quantidade_matricula_eja_medio
-- EJA-Fundamental articulada: quantidade_matricula_eja_fundamental_fic
-- EJA-Fundamental total: quantidade_matricula_eja_fundamental

SELECT
  ano,
  SUM(COALESCE(quantidade_matricula_eja_medio_tecnico, 0)) AS articulada_em,
  SUM(COALESCE(quantidade_matricula_eja_medio, 0)) AS eja_em_total,
  SUM(COALESCE(quantidade_matricula_eja_fundamental_fic, 0)) AS articulada_ef,
  SUM(COALESCE(quantidade_matricula_eja_fundamental, 0)) AS eja_ef_total
FROM `basedosdados.br_inep_censo_escolar.escola`
WHERE sigla_uf = '{UF}'
  AND ano BETWEEN 2020 AND 2024
GROUP BY ano
ORDER BY ano;
