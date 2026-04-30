-- Indicador: qua_taxas_rendimento_ept
-- Recortes: total_estado + rede_estadual
-- 3 sub-valores: aprovação, reprovação, abandono — taxas anuais do EM
--
-- Métrica: média ponderada (peso = quantidade_matricula_medio_tecnico) das taxas EM
-- nas escolas que ofertam EPT. Caveat: taxas oficiais INEP no EM agregam regular + tec
-- na mesma escola — taxa EPT-específica exige cruzamento Censo×egressos por aluno (lead-gen).

WITH escolas_ept AS (
  SELECT
    e.ano,
    e.id_escola,
    e.rede,
    COALESCE(e.quantidade_matricula_medio_tecnico, 0)
      + COALESCE(e.quantidade_matricula_eja_medio_tecnico, 0) AS qtd_ept
  FROM `basedosdados.br_inep_censo_escolar.escola` e
  WHERE e.ano BETWEEN 2020 AND 2024
    AND e.sigla_uf = '{UF}'
    AND (COALESCE(e.quantidade_matricula_medio_tecnico, 0)
         + COALESCE(e.quantidade_matricula_eja_medio_tecnico, 0)) > 0
),

ind AS (
  SELECT
    ano,
    id_escola,
    taxa_aprovacao_em,
    taxa_reprovacao_em,
    taxa_abandono_em
  FROM `basedosdados.br_inep_indicadores_educacionais.escola`
  WHERE ano BETWEEN 2020 AND 2024
)

SELECT
  e.ano,
  ROUND(SUM(i.taxa_aprovacao_em * e.qtd_ept) / NULLIF(SUM(IF(i.taxa_aprovacao_em IS NOT NULL, e.qtd_ept, 0)), 0), 2) AS aprovacao_total,
  ROUND(SUM(i.taxa_reprovacao_em * e.qtd_ept) / NULLIF(SUM(IF(i.taxa_reprovacao_em IS NOT NULL, e.qtd_ept, 0)), 0), 2) AS reprovacao_total,
  ROUND(SUM(i.taxa_abandono_em * e.qtd_ept) / NULLIF(SUM(IF(i.taxa_abandono_em IS NOT NULL, e.qtd_ept, 0)), 0), 2) AS abandono_total,
  ROUND(SUM(IF(e.rede = 'estadual', i.taxa_aprovacao_em * e.qtd_ept, 0)) /
        NULLIF(SUM(IF(e.rede = 'estadual' AND i.taxa_aprovacao_em IS NOT NULL, e.qtd_ept, 0)), 0), 2) AS aprovacao_estadual,
  ROUND(SUM(IF(e.rede = 'estadual', i.taxa_reprovacao_em * e.qtd_ept, 0)) /
        NULLIF(SUM(IF(e.rede = 'estadual' AND i.taxa_reprovacao_em IS NOT NULL, e.qtd_ept, 0)), 0), 2) AS reprovacao_estadual,
  ROUND(SUM(IF(e.rede = 'estadual', i.taxa_abandono_em * e.qtd_ept, 0)) /
        NULLIF(SUM(IF(e.rede = 'estadual' AND i.taxa_abandono_em IS NOT NULL, e.qtd_ept, 0)), 0), 2) AS abandono_estadual
FROM escolas_ept e
LEFT JOIN ind i USING (ano, id_escola)
GROUP BY e.ano
ORDER BY e.ano;
