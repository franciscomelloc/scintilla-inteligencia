# Scintilla Inteligência — Diagnóstico Estadual (MVP backend)

**Status:** v2 — catálogo de 14 indicadores aprovado pelo Francisco
**Data:** 2026-04-30
**Autor:** Francisco + Claude (factory)
**Escopo:** apenas backend (pipeline ETL → JSON). Frontend (`/inteligencia`) é fase posterior.

---

## 1. Objetivo

Pipeline ETL determinístico, refresh trimestral, que gera diagnóstico de Educação Profissional e Tecnológica para 27 unidades federativas (26 estados + DF), com **14 indicadores** comparados a benchmarks (top-quartile, média nacional, e meta PNE 2024-2034 quando aplicável), com **5 anos de histórico** para sparklines/tendências.

Saída: 30 arquivos JSON estáticos (27 estados + benchmark + metadata + schema), prontos para consumo pelo frontend institucional em `/inteligencia`.

## 2. Por que fazer

**Lead-gen qualificado.** Gestor de SEE entra em `/inteligencia`, escolhe seu estado, vê 14 indicadores comparados a benchmark + perguntas que esses dados levantam mas não respondem. Pavimenta a conversa de consultoria.

**Lead-gen estruturalmente forte:** dois indicadores expõem **explicitamente** os limites do dado público (conclusão de coorte e prêmio salarial específico EPT) com chamada institucional pra cruzamento nominativo via projeto consultivo Scintilla. Onde o dado público termina, a oferta paga começa.

**Demonstração de capacidade.** Cruzamento Censo Escolar + RAIS + PNAD + IDEB + CAGED + CNCT + PNE numa leitura coerente por estado. Insumo para pitch comercial sem custo marginal por estado.

## 3. Arquitetura

```
[GitHub Action cron — trimestral + on-demand]
   ↓
[Python ETL]
   ↓ usa basedosdados-python client + BigQuery (free tier 1TB/mês)
[queries SQL versionadas em etl/queries/<indicador>.sql]
   ↓
[indicators.py — contrato pydantic: codigo, valor, vintage, fonte, caveat]
[benchmark.py — calcula top-quartile (P75) + média nacional + meta PNE]
   ↓
[output/diagnostico/<UF>.json × 27 + benchmark.json + metadata.json + schema.json]
   ↓
[cross-repo PR para scintilla-site-v2/public/data/]
```

**Princípios:**
- Pipeline determinístico — mesma run, mesmo output
- Schema versionado — frontend depende de contrato estável
- Falha visível — se 1 indicador falha, gera JSON com `null` + erro logado, não trava run inteira
- Custo zero recorrente — BD/BigQuery free tier cobre folga; GH Actions free tier cobre cron
- Auditável — cada indicador tem fórmula em SQL versionada, fonte rastreável

## 4. Decisão estrutural — Recortes C+D

Cada indicador (quando aplicável) traz **2 recortes simultâneos** no JSON:
- `total_estado` — todas as dependências (federal + estadual + municipal + privada + Sistema S)
- `rede_estadual` — apenas `dependencia_administrativa = 2`

Frontend posterior implementa toggle "Sistema todo / Rede estadual" pra leitura escolhida.

**Indicadores SEM recorte por rede** (mercado de trabalho não tem rede):
- 10 (saldo CAGED), 11 (prêmio salarial), 12 (NEET) — apenas `total_estado`

**Sistema S no MVP:** agregado em "privada" por limitação de classificação no Censo Escolar. Separação Sistema S exige lookup contra lista canônica não disponível em BD nativamente — pendência v2.

## 5. Catálogo de indicadores (v2, 14 indicadores)

### Domínio Cobertura (5)

#### 1. `cob_matriculas_ept_per_jovem`
Matrículas EPT por 1.000 jovens 15-29 anos. Mede capilaridade por aluno.
- **Recortes:** total + estadual
- **Fórmula:** (matrículas EPT / pop 15-29 PNAD) × 1000
- **Fonte:** Censo Escolar `matricula` + PNAD `microdados`
- **Lag:** 12m
- **Caveat:** Inclui integrada+concomitante+subsequente. Denominador PNAD do mesmo ano.

#### 2. `cob_distribuicao_dependencia`
Distribuição percentual entre 4 dependências (federal/estadual/municipal/privada+SistemaS). Mede anatomia institucional do sistema.
- **Recortes:** apenas total (é o próprio recorte sendo decomposto)
- **Output:** 4 valores que somam 100% + valor_5y por dependência + delta vs média nacional
- **Caveat:** Sistema S agregado em privada no MVP; v2 separa via lookup canônico.

#### 3. `cob_municipios_com_ept`
% municípios com ≥1 escola técnica. Capilaridade geográfica (versão simples, não ponderada por população).
- **Recortes:** total + estadual
- **Fórmula:** count(distinct mun com ≥1 escola EPT) / total mun do estado × 100
- **Caveat:** Município conta igual independente do tamanho. Para leitura de cobertura populacional, ver Indicador 1.

#### 4. `cob_eixos_cobertos`
Eixos tecnológicos cobertos (de 13 do CNCT v4). Amplitude da oferta.
- **Recortes:** total + estadual
- **Output:** count + lista nominal cobertos/ausentes + top-3 eixos por matrícula
- **Pendência implementação:** construir CSV `etl/reference/cnct_curso_eixo.csv` parsando o Catálogo Nacional de Cursos Técnicos v4 do MEC.
- **Caveat:** Eixo Militar tem oferta restrita; raramente aparece em rede estadual.

#### 5. `cob_distribuicao_modalidade`
Distribuição percentual entre integrada / concomitante / subsequente. Perfil de público.
- **Recortes:** total + estadual
- **Output:** 3 valores que somam 100% + valor_5y por modalidade + delta vs média nacional
- **Benchmark:** apenas média nacional (não top-quartile — distribuição multi-categórica)
- **Caveat:** Concomitante tem volume estruturalmente baixo (<10% nacional). Integrada cresceu pós-Lei 13.415/2017.

### Domínio Qualidade & Resultado (3)

#### 6. `qua_taxas_rendimento_ept`
Taxas anuais de aprovação/reprovação/abandono na última série de cada modalidade EPT. Substituiu indicador anterior de conclusão de coorte (não viável com dados públicos).
- **Recortes:** total + estadual
- **Output:** 3 sub-valores agregados + breakdown por modalidade (3×3) + valor_5y
- **Lag:** 12m
- **Caveat institucional (lead-gen explícito):** _"Taxas de Rendimento são anuais e medem desfecho na última série. Não constitui taxa de conclusão de coorte — esse indicador não é publicado pelo INEP para educação básica e exige tracking longitudinal nominativo, indisponível em microdados públicos. Para análise de conclusão de coorte real no estado, fale com a Scintilla."_
- **Pendência implementação:** validar se INEP publica Taxas de Rendimento com corte modal EPT em `br_inep_indicadores_educacionais` ou se precisamos calcular via Censo Escolar bruto agregado por `situacao_aluno` na última série.

#### 7. `qua_ideb_escolas_ept`
IDEB-EM médio das escolas com oferta EPT (integrada/concomitante). Qualidade pedagógica do ambiente.
- **Recortes:** total + estadual
- **Output:** valor + valor_5y bianual com gaps + delta vs escolas sem EPT
- **Lag:** 2-3 anos (IDEB bianual, anos pares)
- **Caveat:** IDEB é índice de qualidade do EM, não da EPT em si. Mede ambiente pedagógico, não componente técnico.

#### 8. `qua_razao_aluno_professor_ept`
Razão alunos/docente em EPT. Densidade pedagógica.
- **Recortes:** total + estadual
- **Output:** valor + breakdown por modalidade + valor_5y + `polaridade_inversa: true`
- **Definição inclusiva:** docente conta se atua em ≥1 turma com matrícula EPT.
- **Caveat:** Polaridade inversa (razão menor é melhor). Numerador é matrícula (não aluno único).

### Domínio Infraestrutura (1)

#### 9. `inf_conectividade_ept`
Conectividade nas escolas com EPT. Pirâmide de 4 tiers + componentes.
- **Recortes:** total + estadual
- **Output:** valor (% no tier mais alto) + tier_distribuicao (4 níveis) + componentes (3) + valor_5y
- **Tiers:** sem_internet → internet_basica_sem_banda_larga → banda_larga_sem_uso_aluno → banda_larga_com_uso_aluno
- **Caveat:** Auto-declaratório. Velocidade real (Mbps) não coletada pelo Censo. Substitui versão anterior de "lab/oficina" (campo inexistente no Censo).
- **Forte candidato a meta PNE** (Lei 14.172/2021, programa Educação Conectada).

### Domínio Mercado de Trabalho (3) — sem recorte por rede

#### 10. `mer_saldo_caged_tecnicos`
Saldo CAGED (admissões − desligamentos) em CBO 3xxxx (Técnicos de Nível Médio), 12 meses rolantes.
- **Recortes:** apenas total
- **Output:** saldo absoluto + saldo per 1.000 jovens 15-29 + crescimento yoy + top-3 subfamílias CBO + valor_5y
- **Lag:** 2-3 meses (mais fresco)
- **Backfill:** começa em 2020 (Novo CAGED, eSocial)
- **Caveat:** Apenas vínculos formais; informalidade não capturada. CBO 3xxxx exclui ocupações afins em famílias 5xxxx/7xxxx — crosswalk eixo→CBO fica pra v2.

#### 11. `mer_premio_salarial_escolaridade`
Mediana salarial em vínculos formais por nível de escolaridade do trabalhador. Gradiente educacional do mercado.
- **Recortes:** apenas total
- **Output:** medianas BRL real (sem-EM, EM completo, Superior completo) + prêmios % (EM vs sem-EM, Sup vs EM, Sup vs sem-EM) + valor_5y do prêmio EM + crescimento real
- **Correção monetária:** IPCA pra ano-base = ano mais recente do RAIS
- **Lead-gen explícito:** campo `premio_ept_especifico_publicamente_mensuravel: false`
- **Caveat institucional:** _"RAIS não distingue publicamente Ensino Médio regular de Ensino Médio Técnico — o prêmio específico da formação EPT não é mensurável via dados abertos. Para análise nominativa do prêmio EPT no seu estado (cruzamento Censo Escolar × RAIS por CPF), fale com a Scintilla."_

#### 12. `mer_neet_rate`
% jovens 15-29 que não estudam nem trabalham. Vácuo institucional.
- **Recortes:** apenas total
- **Output:** valor + breakdown por faixa etária (15-17, 18-24, 25-29) + breakdown por sexo + composição interna (desempregados buscando vs inativos não-procurando) + IC95 + valor_5y + `polaridade_inversa: true`
- **Janela:** média móvel anual (4 trimestres PNAD) — reduz ruído amostral
- **Lag:** 3-6 meses
- **Sem recorte por raça no MVP** (pendência v2 com decisão consciente)
- **Forte candidato a meta PNE** (Meta 8 anterior elevava escolaridade jovens 18-29).

### Domínio Dinamismo (2)

#### 13. `din_crescimento_matriculas_5y`
Crescimento de matrículas EPT em janela 5 anos.
- **Recortes:** total + estadual
- **Output:** crescimento cumulativo % + CAGR % + matric_t0 + matric_t5 + decomposição por modalidade + decomposição por dependência (no recorte total)
- **Janela fixa:** Censo mais recente vs 5 anos anteriores (não móvel)
- **Benchmark principal:** CAGR (top-quartile + posição calculados sobre CAGR)
- **Forte candidato a meta PNE** (Meta 11 anterior triplicava matrículas EPT; PNE 2024-2034 mantém expansão).

#### 14. `din_cursos_novos_ept`
Cursos novos abertos nos últimos 2 anos. Renovação do portfólio.
- **Recortes:** total + estadual
- **Output:** cursos_novos_2y + cursos_descontinuados_2y + saldo_liquido + taxa_renovacao % + eixos dos novos + valor_5y da taxa
- **Definição "curso novo":** par escola+curso que aparece pela primeira vez na janela observada (exclui reaberturas).
- **Caveat:** Não distingue curso conceitualmente novo de mesmo curso reiniciado em escola diferente.

## 6. Benchmark methodology

Para cada indicador, três dimensões de comparação no JSON:

**Top-quartile (P75)** — percentil 75 da distribuição entre os 27 estados. Define ambição realista.

**Média nacional** — ponderada por população 15-29 (PNAD) quando o indicador é taxa/proporção; soma quando é estoque.

**Meta PNE 2024-2034** — campo opcional (`vs_meta_pne_2034`). Aplicado apenas a indicadores tocados pelo PNE. Disagregação:
- **Indicadores em taxa/proporção:** meta nacional aplicada uniformemente aos 27 estados
- **Indicadores em estoque (matrículas, saldo):** meta nacional rateada por participação da pop 15-29 do estado

Estrutura `benchmark.json`:
```json
{
  "vintage": "2024",
  "top_quartile": {
    "<codigo_indicador>": {
      "total_estado": <P75>,
      "rede_estadual": <P75>
    }
  },
  "media_nacional": {
    "<codigo_indicador>": {
      "total_estado": <media>,
      "rede_estadual": <media>
    }
  },
  "pne_2024_2034": {
    "versao_referencia": "Lei XX.XXX/2025 (PL 2.614/2024 aprovado)",
    "data_atualizacao": "2026-04-30",
    "horizonte_alvo": 2034,
    "metas": {
      "<codigo_indicador>": {
        "meta_2034": <valor>,
        "baseline": <valor>,
        "fonte_texto": "Meta X.Y — ...",
        "metodologia_disagregacao": "uniforme | rateada_pop"
      }
    }
  }
}
```

## 7. Schema JSON output (exemplo MG)

```json
{
  "uf": "MG",
  "uf_nome": "Minas Gerais",
  "vintage": {
    "censo_escolar": "2024",
    "rais": "2023",
    "caged": "2026-Q1",
    "pnad": "2025-T4_a_2026-T3_media_movel",
    "ideb": "2023"
  },
  "last_built": "2026-04-30T03:00:00Z",
  "indicators": {
    "cob_matriculas_ept_per_jovem": {
      "total_estado": {
        "valor": 9.4,
        "valor_5y": [7.1, 7.6, 8.0, 8.8, 9.4],
        "anos_5y": [2020, 2021, 2022, 2023, 2024],
        "vs_top_quartile": -3.0,
        "vs_media_nacional": +0.7,
        "vs_meta_pne_2034": -8.6,
        "meta_pne_aplicavel": true,
        "posicao": 12
      },
      "rede_estadual": {
        "valor": 4.2,
        "valor_5y": [3.0, 3.2, 3.6, 3.9, 4.2],
        "vs_top_quartile": -1.1,
        "vs_media_nacional": +0.3,
        "vs_meta_pne_2034": null,
        "meta_pne_aplicavel": false,
        "posicao": 14
      },
      "vintage": "2024",
      "caveat": "..."
    }
  },
  "perguntas_que_levantam": [
    "...geração híbrida (regra automática + curadoria Francisco antes de publicar)..."
  ]
}
```

`schema.json` é JSON Schema (draft 2020-12) que valida `<UF>.json` e `benchmark.json`.

## 8. Pipeline de refresh

**Cron**: `0 6 1 1,4,7,10 *` (1º dia jan/abr/jul/out, 06:00 UTC = 03:00 BRT)
**On-demand**: workflow_dispatch com input `force_full_rebuild`
**Budget**: 8 minutos total no GitHub Actions ubuntu-latest
**Falha-tolerante**: cada indicador roda isolado; falha gera `null` + log no PR description

**Output**: commita em `output/` no repo na branch `data-YYYY-Q*`. Em seguida, `pr-to-site.yml` abre cross-repo PR para `scintilla-site-v2` copiando `output/` para `public/data/`.

## 9. Repo + integração

```
scintilla-inteligencia/
├─ .fabrica/
│  ├─ specs/2026-04-30-diagnostico-estadual-mvp/spec.md  ← este arquivo
│  └─ principles.md (link para fábrica)
├─ etl/
│  ├─ queries/<codigo>.sql   ← 14 SQLs versionadas
│  ├─ reference/
│  │  └─ cnct_curso_eixo.csv  ← mapeamento curso técnico → eixo (parsing do CNCT v4)
│  ├─ indicators.py           ← contrato pydantic + execução
│  ├─ benchmark.py            ← top-quartile + média + PNE
│  ├─ build.py                ← orquestrador
│  └─ schemas/
│     ├─ uf.schema.json
│     ├─ benchmark.schema.json
│     └─ metadata.schema.json
├─ output/
│  ├─ diagnostico/<UF>.json   ← 27 arquivos
│  ├─ benchmark.json
│  ├─ metadata.json
│  └─ schema.json
├─ tests/
│  ├─ test_schema.py
│  ├─ test_smoke.py
│  └─ test_benchmark.py
├─ .github/workflows/
│  ├─ refresh.yml
│  ├─ pr-to-site.yml
│  └─ ci.yml
├─ pyproject.toml             ← uv lockfile
├─ README.md
└─ .gitignore
```

## 10. Tech stack

- Python 3.12 + `uv` (build + lockfile)
- `basedosdados` (PyPI) — wrapper BigQuery
- `pydantic` v2 — contrato Python
- JSON Schema 2020-12 — validação cross-language
- `pytest` — tests
- `ruff` + `mypy --strict` — lint
- BigQuery via GCP service account (free tier 1TB/mês)
- GitHub Actions cron + workflow_dispatch

## 11. Acceptance criteria (objetivos, testáveis)

1. ✅ `python etl/build.py` em ambiente limpo gera 30 arquivos: 27 `diagnostico/<UF>.json` + `benchmark.json` + `metadata.json` + `schema.json`
2. ✅ Cada `<UF>.json` valida contra `schema.json` (JSON Schema 2020-12)
3. ✅ Cada `<UF>.json` contém os 14 indicadores; valor `null` apenas com `caveat` explicando ausência
4. ✅ Cada indicador (quando aplicável) tem 2 recortes — `total_estado` e `rede_estadual` — exceto Mercado (10, 11, 12) que tem só `total_estado`
5. ✅ `benchmark.json` contém top-quartile + média nacional + bloco PNE para os 14 indicadores
6. ✅ Cada indicador tem campo `vintage` e `valor_5y` (array com 5 anos ou `null` quando série não existe)
7. ✅ Build total roda em ≤ 8 minutos no GitHub Actions ubuntu-latest
8. ✅ Workflow `refresh.yml` dispara em cron trimestral E `workflow_dispatch`
9. ✅ Após refresh, `pr-to-site.yml` abre PR em `scintilla-site-v2` com diff em `public/data/`
10. ✅ Custo BigQuery por refresh ≤ 100GB processados (folga 10× sobre free tier)
11. ✅ Documentação: `README.md` cobre setup local, contribuição, rotação de credencial GCP

## 12. Pendências e riscos

### Bloqueantes para começar implementação

- [ ] Francisco abre projeto GCP `scintilla-inteligencia` + service account + cartão (free tier 1TB/mês cobre, mas billing precisa estar habilitado)
- [ ] Service account JSON em GitHub secret `GCP_SA_KEY`
- [ ] PAT cross-repo `SITE_REPO_TOKEN` com `contents:write,pull_requests:write` no `scintilla-site-v2`
- [ ] Eu valido nomes exatos de tabelas BD (~30-60 min antes de codar)

### Pendências de pesquisa paralela

**Metas numéricas PNE 2024-2034** — texto da lei aprovada precisa ser baixado pra mapear cada meta a um indicador nosso e extrair valor numérico alvo + baseline. Candidatos prioritários (5 indicadores):
- Indicador 1 (matrículas EPT por 1.000 jovens) — Meta de expansão EPT
- Indicador 9 (conectividade) — Lei 14.172/2021, programa Educação Conectada
- Indicador 12 (NEET) — Meta 8 anterior elevava escolaridade jovens 18-29
- Indicador 13 (crescimento matrículas) — Meta 11 anterior triplicava EPT
- Indicador 5 (distribuição modalidade) ou 6 (rendimento) — Meta de qualidade EPT

Fontes para mapeamento:
- [Câmara — Infográfico PNE 2024-2034](https://infograficos.camara.leg.br/pne-2024-2034/)
- [MEC — Página oficial PNE 2024-2034](https://www.gov.br/mec/pt-br/pne/pne-2024-2034)
- [Câmara — Comissão Especial PNE PL 2614-24](https://www2.camara.leg.br/atividade-legislativa/comissoes/comissoes-temporarias/especiais/57a-legislatura/comissao-especial-sobre-o-plano-nacional-de-educacao-decenio-2024-2034-pl-2614-24/)

### Riscos identificados

- **R1: Nome de tabelas BD pode ter mudado.** Mitigação: validação técnica antes de codar.
- **R2: BD pode ter rate-limit em queries grandes.** Mitigação: agregar por UF em CTEs antes de baixar; nunca microdado bruto.
- **R3: Filtro "EPT" no Censo Escolar mudou pré/pós-2017 (BNCC).** Mitigação: backfill começa em 2020.
- **R4: Novo CAGED (2020+) tem metodologia diferente do CAGED Antigo.** Mitigação: começar série em 2020.
- **R5: PNAD reagrupada em 2024.** Mitigação: validar continuidade da série antes do backfill.
- **R6: Geração automática de "perguntas que levantam" pode soar artificial.** Mitigação: híbrido com curadoria Francisco antes de publicar trimestralmente.
- **R7: RAIS não distingue EM regular de EM técnico publicamente.** Mitigação: já assumido — vira lead-gen explícito no Indicador 11.
- **R8: INEP não publica conclusão de coorte para educação básica.** Mitigação: já assumido — vira lead-gen explícito no Indicador 6.
- **R9: id_aluno do Censo Escolar é re-hash anual.** Mitigação: já assumido — não tentamos tracking longitudinal individual.
- **R10: PNE 2024-2034 metas numéricas ainda não extraídas.** Mitigação: pendência de pesquisa paralela com fontes mapeadas.

### Não bloqueantes (frontend phase)

- Visual / design system (aguarda redesign do site institucional pelo Francisco)
- Email-gate / lead capture (decisão de produto na fase frontend)
- PDF download vs HTML interativo
- Mapa oferta-demanda (EPT × mercado) — segundo produto, fase posterior

## 13. Próximos passos após aprovação da spec v2

1. Pesquisa paralela PNE 2024-2034 → mapeamento meta → indicador (5-7 indicadores tocados)
2. Validação técnica de tabelas BD (~30-60 min)
3. Francisco abre projeto GCP + secrets
4. Scaffold do repo `scintilla-inteligencia` seguindo princípios da fábrica
5. Implementação por indicador (TDD: 1 indicador por PR, com fixture + smoke test)
6. CI verde → cron habilitado → primeiro refresh
7. Cross-repo PR para `scintilla-site-v2` (apenas dados, sem frontend ainda)

---

**Sources consultadas para v2:**
- [Indicadores Educacionais — INEP](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais)
- [INEP publica taxas de rendimento escolar 2024](https://www.gov.br/inep/pt-br/centrais-de-conteudo/noticias/censo-escolar/inep-publica-taxas-de-rendimento-escolar-do-censo-escolar-2024)
- [Indicadores Educacionais da Educação Básica — dados.gov.br](https://dados.gov.br/dados/conjuntos-dados/indicadores-educacionais-da-educao-bsica)
- [Dicionário de Indicadores Educacionais — INEP (PDF)](https://download.inep.gov.br/publicacoes/institucionais/estatisticas_e_indicadores/dicionario_de_indicadores_educacionais_formulas_de_calculo.pdf)
- [Base dos Dados — Indicadores Educacionais INEP](https://basedosdados.org/dataset/br-inep-indicadores-educacionais)
- [Câmara — Infográfico PNE 2024-2034](https://infograficos.camara.leg.br/pne-2024-2034/)
- [MEC — Página oficial PNE 2024-2034](https://www.gov.br/mec/pt-br/pne/pne-2024-2034)
- [MEC discute EPT no novo PNE](https://www.gov.br/mec/pt-br/assuntos/noticias/2025/julho/mec-discute-ept-no-novo-plano-nacional-de-educacao)
