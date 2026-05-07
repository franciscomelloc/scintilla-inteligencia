-- Indicador: pne_m12c
-- PNE Meta 12.c · % EJA articulada à educação profissional sobre EJA total
--
-- EJA-Médio articulada = matrículas EJA-EM com qualquer componente profissional.
-- Definição via complemento: total − não-profissionalizante. Captura tanto
-- 'eja_medio_tecnico' (curso técnico integrado) quanto 'eja_medio_fic' (FIC
-- integrado) e robusta contra novas categorias futuras do Censo.
--
-- EJA-Fundamental articulada = eja_fundamental_fic (FIC integrado).
-- (EJA-Fundamental não tem 'técnico' por definição; só FIC.)

SELECT
  ano,
  GREATEST(0,
    SUM(COALESCE(quantidade_matricula_eja_medio, 0))
    - SUM(COALESCE(quantidade_matricula_eja_medio_nao_profissionalizante, 0))
  ) AS articulada_em,
  SUM(COALESCE(quantidade_matricula_eja_medio, 0)) AS eja_em_total,
  SUM(COALESCE(quantidade_matricula_eja_fundamental_fic, 0)) AS articulada_ef,
  SUM(COALESCE(quantidade_matricula_eja_fundamental, 0)) AS eja_ef_total
FROM `basedosdados.br_inep_censo_escolar.escola`
WHERE sigla_uf = @uf
  AND ano BETWEEN 2020 AND 2024
GROUP BY ano
ORDER BY ano;
