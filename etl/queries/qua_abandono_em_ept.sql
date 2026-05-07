-- Indicador: qua_abandono_em_ept
-- Taxa de abandono EM em escolas COM EPT vs SEM EPT, rede estadual
-- Atenção: indicadores_educacionais.rede vem como STRING ("estadual"), não código '2' como em escola.
-- Ponderação por matrículas EM da escola (peso = quantidade_matricula_medio do censo escolar).

WITH escola_em AS (
  SELECT
    id_escola,
    ano,
    COALESCE(quantidade_matricula_medio, 0) AS qtd_em,
    CASE WHEN COALESCE(quantidade_matricula_profissional_tecnica, 0)
            + COALESCE(quantidade_matricula_medio_tecnico, 0) > 0 THEN 1 ELSE 0 END AS tem_ept
  FROM `basedosdados.br_inep_censo_escolar.escola`
  WHERE sigla_uf = @uf
    AND ano BETWEEN 2020 AND 2024
    AND rede = '2'  -- censo escolar usa código numérico
)

SELECT
  i.ano,
  e.tem_ept,
  SUM(i.taxa_abandono_em * e.qtd_em) / NULLIF(SUM(e.qtd_em), 0) AS taxa_abandono_em_ponderada,
  SUM(e.qtd_em) AS matriculas_em_total,
  COUNT(DISTINCT i.id_escola) AS n_escolas
FROM `basedosdados.br_inep_indicadores_educacionais.escola` i
JOIN escola_em e ON e.id_escola = i.id_escola AND e.ano = i.ano
WHERE i.rede = 'estadual'  -- aqui sim, vem como nome
  AND e.qtd_em > 0
  AND i.taxa_abandono_em IS NOT NULL
GROUP BY i.ano, e.tem_ept
ORDER BY i.ano DESC, e.tem_ept DESC;
