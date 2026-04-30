# scintilla-inteligencia

Pipeline ETL que gera **diagnóstico estadual de Educação Profissional e Tecnológica** para 27 unidades federativas. Saída: 30 arquivos JSON (27 UFs + benchmark + metadata + schema) consumidos pela página `/inteligencia` do site `scintilla-site-v2`.

**Status:** scaffold inicial. Aguarda primeiro setup GCP (4 cliques abaixo) antes de produzir dados reais.

## Arquitetura

```
[GitHub Action cron — trimestral]
   ↓
[Python 3.12 + uv]
   ↓
[etl/queries/*.sql contra Base dos Dados (BigQuery free tier)]
[etl/indicators.py — contrato pydantic]
[etl/benchmark.py — top-quartile + média + PNE 2024-2034]
[etl/build.py — orquestrador]
   ↓
[output/diagnostico/<UF>.json × 27 + benchmark.json + metadata.json + schema.json]
   ↓
[cross-repo PR para scintilla-site-v2/public/data/]
```

## First-time setup (Francisco — 4 passos)

Pré-requisitos antes do primeiro refresh real:

### 1. Criar projeto GCP `scintilla-inteligencia`

- Acesse https://console.cloud.google.com/projectcreate
- Nome: `scintilla-inteligencia`
- Billing: vincule cartão (free tier 1TB/mês cobre folga 10×; custo esperado R$ 0)
- Habilite API: `BigQuery API` em "APIs & Services > Library"

### 2. Criar service account + chave JSON

- IAM & Admin > Service Accounts > Create
- Nome: `scintilla-etl`
- Roles: `BigQuery Data Viewer` + `BigQuery Job User`
- Após criar: Keys > Add Key > Create new key > JSON > download
- **Nunca commite o JSON.** Está no .gitignore.

### 3. Adicionar secret no GitHub

- Em https://github.com/franciscomelloc/scintilla-inteligencia/settings/secrets/actions
- New repository secret
- Nome: `GCP_SA_KEY`
- Valor: cole o JSON inteiro (o arquivo do passo 2)

### 4. Criar PAT cross-repo `SITE_REPO_TOKEN`

Necessário para o workflow abrir PR no repo `scintilla-site-v2` automaticamente após cada refresh.

- Em https://github.com/settings/tokens?type=beta
- Generate new token (fine-grained)
- Repository access: `franciscomelloc/scintilla-site-v2`
- Permissions: `Contents: Write` + `Pull requests: Write`
- Copie o token
- No repo `scintilla-inteligencia` > Settings > Secrets, adicione:
  - Nome: `SITE_REPO_TOKEN`
  - Valor: o PAT

### 5. Disparar primeiro refresh

- Após os 4 secrets estarem configurados, vá em Actions > Refresh > Run workflow
- Após ~8 minutos, um PR deve aparecer em `scintilla-site-v2` substituindo os mocks

---

## Desenvolvimento local

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/).

```bash
# instalar deps
uv sync

# colocar credencial GCP
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json

# rodar ETL local
uv run python etl/build.py

# tests
uv run pytest

# lint + types
uv run ruff check .
uv run mypy etl/
```

## Estrutura

```
.fabrica/specs/2026-04-30-diagnostico-estadual-mvp/
  spec.md                  ← especificação versionada
  pne_mapping.md           ← metas PNE 2024-2034 → indicadores
  bd_table_validation.md   ← validação de tabelas BD

etl/
  queries/<codigo>.sql     ← 14 SQLs versionadas, uma por indicador
  reference/
    cnct_curso_eixo.csv    ← mapeamento curso técnico → eixo (CNCT v4)
  schemas/
    uf.schema.json         ← JSON Schema da saída por UF
    benchmark.schema.json
    metadata.schema.json
  indicators.py            ← contrato pydantic + dispatcher por código
  benchmark.py             ← top-quartile + média + PNE
  build.py                 ← orquestrador

output/                    ← gerado, commitado a cada refresh
  diagnostico/<UF>.json × 27
  benchmark.json
  metadata.json
  schema.json (cópia de etl/schemas/uf.schema.json)

tests/
  test_schema.py           ← valida JSON contra JSON Schema
  test_smoke.py            ← cada UF tem 14 indicadores não-null (ou justificados)

.github/workflows/
  refresh.yml              ← cron trimestral + workflow_dispatch
  pr-to-site.yml           ← cross-repo PR após refresh
  ci.yml                   ← lint + tests em PRs
```

## Catálogo de indicadores

14 indicadores em 5 domínios. Spec completa em `.fabrica/specs/2026-04-30-diagnostico-estadual-mvp/spec.md`.

| Domínio | # | Indicadores |
|---|---|---|
| Cobertura | 5 | matrículas/jovem, distribuição dependência, municípios cobertos, eixos, modalidade |
| Qualidade | 3 | rendimento (apr/rep/aban), IDEB EPT, razão aluno/professor |
| Infraestrutura | 1 | conectividade (pirâmide de tiers) |
| Mercado | 3 | saldo CAGED técnicos, prêmio salarial escolaridade, NEET |
| Dinamismo | 2 | crescimento 5y, cursos novos 2y |

## Princípios

- Pipeline determinístico — mesma run, mesmo output
- Schema versionado — frontend depende de contrato estável
- Falha visível — 1 indicador falhando gera `null` + log no PR; não trava run inteira
- Custo zero recorrente — BD free tier 1TB/mês + GH Actions free tier
- Auditável — cada indicador tem fórmula em SQL versionada

## Lead-gen explícito

Dois indicadores expõem **propositalmente** os limites do dado público, com chamada institucional ao consultivo da Scintilla:

- **`qua_taxas_rendimento_ept`** — taxa de conclusão de coorte real exige tracking longitudinal nominativo, indisponível em microdados públicos
- **`mer_premio_salarial_escolaridade`** — prêmio EPT específico exige cruzamento Censo Escolar × RAIS por CPF

Ambos viram conversa comercial direta no frontend `/inteligencia`.
