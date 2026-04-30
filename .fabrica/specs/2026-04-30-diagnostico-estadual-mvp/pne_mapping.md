# PNE 2024-2034 — Mapeamento de metas → indicadores

**Status:** v1 — pesquisa inicial (texto integral pendente de download)
**Lei:** Lei nº 15.388/2026, sancionada em 14/abr/2026
**Estrutura:** 18 objetivos, 58 metas (vs 20 metas + 56 indicadores do PNE 2014-2024)

## Metas EPT identificadas (4 numéricas)

### M1 — EPT integrada/concomitante: ≥50% do EM até 2036

> "Expansão, até 2036, da oferta de EPT técnica integrada ou concomitante ao ensino médio para pelo menos 50% dos estudantes nessa etapa de ensino."

**Mapeia para:** `cob_distribuicao_modalidade`
**Tipo:** taxa/proporção → disagregação **uniforme** (mesma meta nacional aplicada aos 27 estados)
**Campo no JSON:** `vs_meta_pne_2034.integrada_mais_concomitante`
**Cálculo:** `(matric integrada + matric concomitante) / matric EM total no estado × 100` — comparar contra meta 50%

### M2 — EPT subsequente: expansão de +60%

> "Expansão de 60% das matrículas em cursos subsequentes."

**Mapeia para:** `din_crescimento_matriculas_5y` (componente subsequente) e `cob_matriculas_ept_per_jovem`
**Tipo:** taxa de crescimento → disagregação **uniforme** (cada estado deve crescer 60%)
**Baseline:** matrículas subsequentes no ano-base do PNE (2024 ou 2026 conforme texto integral)

### M3 — Qualificação profissional: 3 mi de matrículas anuais

> "3 milhões de matrículas anuais em cursos de qualificação profissional."

**Mapeia para:** indicador relacionado ao FIC/qualificação — **não está explicitamente nos 14 indicadores atuais** (cobrimos EPT técnica, não FIC). Pendência: avaliar se vale adicionar Indicador 15 `cob_matriculas_fic` ou se mantém o catálogo de 14.
**Tipo:** estoque → disagregação **rateada por pop 15-29**

### M4 — Conectividade: 50% das escolas públicas em 2 anos / 100% em 10 anos

> "50% das escolas públicas terão internet de alta velocidade com wi-fi em dois anos, alcançando 100% em dez anos."

**Mapeia para:** `inf_conectividade_ept` — tier mais alto da pirâmide
**Tipo:** taxa → disagregação **uniforme**
**Trajetória:**
- Meta intermediária 2028: 50% das escolas com banda larga + uso pelo aluno
- Meta final 2036: 100%
**Campo no JSON:** `vs_meta_pne_2028` e `vs_meta_pne_2036` (duas dimensões temporais possíveis para conectividade)

## Indicadores nossos × metas PNE

| Código | Meta PNE | `meta_pne_aplicavel` | Disagregação |
|---|---|---|---|
| `cob_matriculas_ept_per_jovem` | M2 (parcial) | true | uniforme/rateada |
| `cob_distribuicao_dependencia` | — | false | — |
| `cob_municipios_com_ept` | — | false | — |
| `cob_eixos_cobertos` | — | false | — |
| `cob_distribuicao_modalidade` | **M1** | true | uniforme |
| `qua_taxas_rendimento_ept` | — | false (até confirmação no texto integral) | — |
| `qua_ideb_escolas_ept` | — | false | — |
| `qua_razao_aluno_professor_ept` | — | false | — |
| `inf_conectividade_ept` | **M4** | true | uniforme |
| `mer_saldo_caged_tecnicos` | — | false | — |
| `mer_premio_salarial_escolaridade` | — | false | — |
| `mer_neet_rate` | — | **pendente** (PNE pode ter meta de NEET ou escolaridade jovens) | — |
| `din_crescimento_matriculas_5y` | **M2** | true | uniforme |
| `din_cursos_novos_ept` | — | false | — |

**Resumo:** 3 indicadores com meta PNE confirmada (M1, M2, M4), 1 pendente (NEET), 10 sem meta numérica direta.

## Pendências

1. **Texto integral da Lei 15.388/2026** — baixar PDF oficial e mapear as 58 metas inteiras pra eventualmente adicionar metas que não saíram nas notícias.
2. **Meta de NEET / escolaridade jovens 18-29** — o PNE 2014 tinha (Meta 8); validar se PNE 2024 mantém com valor numérico.
3. **Meta 3 (FIC)** — decidir se adicionamos Indicador 15 `cob_matriculas_fic` ao catálogo ou se mantém em 14.
4. **Baseline e horizonte** — o texto integral confirmará valores baseline (ano de referência) e horizontes intermediários.

## Fontes

- [Governo sanciona PNE 2024-2034 — INEP](https://www.gov.br/inep/pt-br/centrais-de-conteudo/noticias/institucional/governo-do-brasil-sanciona-novo-plano-nacional-da-educacao)
- [Governo sanciona PNE — MEC](https://www.gov.br/mec/pt-br/assuntos/noticias/2026/abril/governo-do-brasil-sanciona-novo-plano-nacional-da-educacao)
- [PNE 2024-2034 — MEC oficial](https://www.gov.br/mec/pt-br/pne/pne-2024-2034)
- [Comissão Especial PL 2.614/2024 — Câmara](https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-temporarias/especiais/57a-legislatura/comissao-especial-sobre-o-plano-nacional-de-educacao-decenio-2024-2034-pl-2614-24/)
- [Apresentação EPT no PNE — Diogo Jamra](https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-temporarias/especiais/57a-legislatura/comissao-especial-sobre-o-plano-nacional-de-educacao-decenio-2024-2034-pl-2614-24/apresentacoes-em-eventos/DIOGOJAMRAFundaoIta.pdf)
