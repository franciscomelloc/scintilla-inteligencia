-- Indicador: mer_neet_rate
-- Recortes: apenas total_estado
-- Polaridade: INVERSA (NEET menor é melhor)
-- Janela: média móvel anual (4 trimestres PNAD) reduz ruído amostral

WITH pnad AS (
  SELECT
    ano,
    trimestre,
    sigla_uf,
    idade,
    sexo,
    -- definição NEET: não estuda E não trabalha na semana de referência
    CASE WHEN frequencia_escola = 'nao' AND condicao_ocupacao = 'desocupado' THEN 1 ELSE 0 END AS neet,
    -- componente: distinguir desempregado buscando vs inativo
    CASE WHEN frequencia_escola = 'nao' AND condicao_ocupacao = 'desocupado' AND procurou_trabalho = 'sim' THEN 1 ELSE 0 END AS neet_buscando,
    peso
  FROM `basedosdados.br_ibge_pnadc.microdados`
  WHERE ano BETWEEN 2020 AND 2025
    AND idade BETWEEN 15 AND 29
    AND sigla_uf = '{UF}'
)

SELECT
  ano,
  trimestre,
  -- agregado
  100.0 * SUM(neet * peso) / SUM(peso) AS neet_rate_total,
  -- por faixa etária
  100.0 * SUM(CASE WHEN idade BETWEEN 15 AND 17 THEN neet * peso ELSE 0 END) /
    NULLIF(SUM(CASE WHEN idade BETWEEN 15 AND 17 THEN peso ELSE 0 END), 0) AS neet_15_17,
  100.0 * SUM(CASE WHEN idade BETWEEN 18 AND 24 THEN neet * peso ELSE 0 END) /
    NULLIF(SUM(CASE WHEN idade BETWEEN 18 AND 24 THEN peso ELSE 0 END), 0) AS neet_18_24,
  100.0 * SUM(CASE WHEN idade BETWEEN 25 AND 29 THEN neet * peso ELSE 0 END) /
    NULLIF(SUM(CASE WHEN idade BETWEEN 25 AND 29 THEN peso ELSE 0 END), 0) AS neet_25_29,
  -- por sexo
  100.0 * SUM(CASE WHEN sexo = 'masculino' THEN neet * peso ELSE 0 END) /
    NULLIF(SUM(CASE WHEN sexo = 'masculino' THEN peso ELSE 0 END), 0) AS neet_homens,
  100.0 * SUM(CASE WHEN sexo = 'feminino' THEN neet * peso ELSE 0 END) /
    NULLIF(SUM(CASE WHEN sexo = 'feminino' THEN peso ELSE 0 END), 0) AS neet_mulheres,
  -- composição
  100.0 * SUM(neet_buscando * peso) / NULLIF(SUM(neet * peso), 0) AS pct_buscando,
  100.0 * SUM((neet - neet_buscando) * peso) / NULLIF(SUM(neet * peso), 0) AS pct_inativos
FROM pnad
GROUP BY ano, trimestre
ORDER BY ano, trimestre;
