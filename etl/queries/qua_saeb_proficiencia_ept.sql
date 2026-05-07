-- Indicador: qua_saeb_proficiencia_ept
-- Comparação SAEB Mat/Port em municípios COM EPT vs SEM EPT
-- Usa basedosdados.br_inep_saeb.municipio que vem por município IBGE
-- Cruzamento por id_municipio com Censo Escolar

WITH munis_com_ept AS (
  SELECT DISTINCT id_municipio
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = @uf
    AND COALESCE(quantidade_matricula_profissional_tecnica, 0)
        + COALESCE(quantidade_matricula_medio_tecnico, 0) > 0
),

saeb_uf AS (
  SELECT MAX(ano) AS ano_recente
  FROM `basedosdados.br_inep_saeb.municipio`
  WHERE sigla_uf = @uf
)

SELECT
  s.ano,
  s.disciplina,
  s.serie,
  CASE WHEN m.id_municipio IS NOT NULL THEN 1 ELSE 0 END AS muni_com_ept,
  AVG(s.media) AS proficiencia_media,
  COUNT(*) AS n_municipios
FROM `basedosdados.br_inep_saeb.municipio` s
LEFT JOIN munis_com_ept m ON m.id_municipio = s.id_municipio
WHERE s.sigla_uf = @uf
  AND s.ano = (SELECT ano_recente FROM saeb_uf)
  AND s.media IS NOT NULL
  AND s.serie = 12  -- EM 3º ano
  AND s.rede = 'estadual'
GROUP BY s.ano, s.disciplina, s.serie, muni_com_ept
ORDER BY s.disciplina, muni_com_ept DESC;
