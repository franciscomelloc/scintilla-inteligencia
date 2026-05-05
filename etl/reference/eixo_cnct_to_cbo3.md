# Mapping: Eixo Tecnológico CNCT → Famílias CBO 2002 (subgrupo 3xxxx)

Catálogo Nacional de Cursos Técnicos (MEC, v4 vigente) define 13 eixos
tecnológicos. Cada eixo agrupa cursos técnicos com afinidade
ocupacional. Pra calcular **aderência oferta EPT × demanda mercado**,
mapeamos cada eixo a um conjunto de famílias CBO 3xxxx ("Técnicos de
Nível Médio") onde os egressos do eixo são contratados.

## Regras de mapping

1. **Granularidade**: subgrupo CBO de 3 dígitos (ex: `317` = TI) ou
   código completo de 6 dígitos quando necessário. Cada CBO é atribuída
   a **exatamente 1 eixo** — sem dupla contagem.
2. **Escopo CBO**: apenas grande grupo 3 (Técnicos Nível Médio).
   Excluído subgrupo 33xxxx (Técnicos da educação) por já estar
   filtrado nos cards `mer_demanda_cbo_top` e `mer_demanda_mesorregiao`
   — manter consistência.
3. **Eixos sem demanda CBO 3xxxx mensurável** ficam excluídos da
   matriz de aderência (e.g. Militar = CBO 02, não 3). Documentado.
4. **Casos ambíguos** (CBO compatível com 2+ eixos): atribuir ao eixo
   onde a maior parte da formação técnica brasileira ocorre, com base
   no Catálogo MEC.

## Mapping proposto (revisar antes de hardcodar)

| # | Eixo CNCT | CBO 3xxxx atribuídas | Justificativa principal |
|---|---|---|---|
| 1 | **Ambiente e Saúde** | `321`, `322`, `323`, `324`, `325`, `326` | Saúde é toda 32x (enfermagem, farmácia, patologia, saúde bucal). Inclui Téc Meio Ambiente em 321 (biotécnicos) |
| 2 | **Controle e Processos Industriais** | `311`, `313` | 311 = polivalentes/química/petroquímica; 313 = eletricidade/eletrônica industrial |
| 3 | **Desenvolvimento Educacional e Social** | — (excluído) | Cursos do eixo (Cuidador Idoso, Multimeios, Libras) caem em CBO 33xxxx ou 5xxxx — fora do escopo CBO 3 com 33 já excluído |
| 4 | **Gestão e Negócios** | `351`, `354`, `391` (parcial) | 351 = Téc Adm/Contab/RH/Seg Trabalho; 354 = vendas/eventos/comércio. 391 = controle de produção/qualidade (gerencial) |
| 5 | **Informação e Comunicação** | `317` | Téc TI completo (suporte, redes, dev, banco de dados) |
| 6 | **Infraestrutura** | `312`, `318` | 312 = obras civis, agrimensura, geomática; 318 = transportes/logística operacional |
| 7 | **Militar** | — (excluído) | Forças armadas usam CBO 0xxxx, não 3 |
| 8 | **Produção Alimentícia** | — (excluído) | Téc Alimentos/Panificação majoritariamente em CBO 7xxxx-8xxxx (operacionais), não 3 — diluiria a análise |
| 9 | **Produção Cultural e Design** | `374`, `376` | 374 = audiovisual, mídia; 376 = artes plásticas, design, cenografia |
| 10 | **Produção Industrial** | `314`, `300` | 314 = manutenção mecânica, mecânica industrial; 300 = polivalentes (eletromecânica) |
| 11 | **Recursos Naturais** | `301` | Téc agropecuária polivalente. 32x agropecuária está mais em saúde — gray area; alternativa: deixar em Saúde por consistência |
| 12 | **Segurança** | `351605` (single CBO) | Conflito com Eixo 4 (Gestão usa todo 351). Decisão: 351605 vai pra **Segurança** explicitamente, restante de 351 fica em Gestão |
| 13 | **Turismo, Hospitalidade e Lazer** | `371`, `354820` (single CBO) | 371 = lazer/recreação/desportivo; 354820 (Organizador Evento) sai de Gestão pra cá |

## Casos ambíguos resolvidos

| CBO | Decisão | Razão |
|---|---|---|
| `351605` (Téc Seg Trabalho) | → **Segurança** (não Gestão) | Eixo CNCT específico tem o curso |
| `354820` (Organizador Evento) | → **Turismo/Hospit.** (não Gestão) | Eixo CNCT específico tem o curso |
| `391xxx` (Controle Produção/Qualidade) | → **Gestão** (não Indústria) | Função gerencial, não operacional |
| `300305` (Téc Eletromecânica) | → **Produção Industrial** | Curso explícito do eixo |
| `321` (Téc Agropecuária) | → **Ambiente e Saúde** | BD agrupa em 32x; manter |

## CBOs cobertos vs descartados

Após este mapping, do top 30 CBO 3xxxx do Brasil (excluindo 33xxxx
já filtrado):

- Cobertos pelo mapping: ~85% do saldo CAGED 12m
- Descartados (CBO sem eixo CNCT correspondente): ~15%
  - Maioria são CBOs gerais que não têm curso CNCT específico
  - Documentar como caveat na visualização

## Pendências para validação humana

1. Confirmar atribuição de **`391xxx` (controladores qualidade/produção)** — pode ser argumentado como Eixo 10 (Produção Industrial) em vez de Eixo 4 (Gestão)
2. Confirmar **`321` agropecuária** em Saúde vs Recursos Naturais
3. Confirmar exclusão dos eixos Militar, Educação Social, Produção Alimentícia (sem demanda mensurável em CBO 3xxxx)
4. Validar contra o **Catálogo CNCT v4 MEC** (PDF oficial) — link: catalogonacionaldecursostecnicos.mec.gov.br

## Próximo passo

Após aprovação humana deste mapping:
1. Hardcode no SQL `mer_aderencia_eixo_cbo.sql` via CASE WHEN sobre `cbo_2002`
2. Espelhar no Python (`etl/processors.py`) caso o agg precisa
3. Popular `etl/reference/cnct_curso_eixo.csv` com mapping curso INEP → eixo

## Resolução (descoberta 2026-05-05)

**Não precisamos popular CSV manual.** Confirmado via parsing direto do
Caderno de Conceitos e Orientações INEP 2022 (páginas 93-99): o código
`id_curso_educ_profissional` **codifica o eixo no próprio número** —
`eixo_id = id_curso // 1000`.

Estrutura dos códigos INEP (validada com 196 cursos do Censo 2020):

| eixo_id | Eixo Tecnológico (INEP) | Range de código |
|---|---|---|
| 1 | Ambiente e Saúde | 1001-1033, 1999 |
| 2 | Desenvolvimento Educacional e Social | 2029-2040, 2999 |
| 3 | Controle e Processos Industriais | 3036-3064, 3999 |
| 4 | Gestão e Negócios | 4050-4066, 4999 |
| 5 | Turismo, Hospitalidade e Lazer | 5066-5072, 5999 |
| 6 | Informação e Comunicação | 6073-6082, 6999 |
| 7 | Infraestrutura | 7081-7098, 7999 |
| 8 | Militar | 8099-8133, 8999 |
| 9 | Produção Alimentícia | 9120-9127, 9999 |
| 10 | Produção Cultural e Design | 10144-10160, 10999 |
| 11 | Produção Industrial | 11154-11178, 11999 |
| 12 | Recursos Naturais | 12171-12188, 12999 |
| 13 | Segurança | 13181-13183, 13999 |

**Implementação SQL:**
```sql
DIV(id_curso_educ_profissional, 1000) AS eixo_id
```

ATENÇÃO: o eixo `2 = Desenvolvimento Educacional e Social` na numeração
INEP corresponde ao eixo `3 = Desenvolvimento Educacional e Social` no
Catálogo Nacional MEC (ordem alfabética). Estamos usando a numeração
INEP no banco. O mapping eixo→CBO acima foi atualizado pra refletir.

## Mapping eixo INEP → CBO 3xxxx (atualizado)

| INEP eixo_id | Eixo | CBO 3xxxx atribuídas | Status |
|---|---|---|---|
| 1 | Ambiente e Saúde | `321-326` | ✓ inclui |
| 2 | Desenvolvimento Educ. e Social | — | excluído (CBO 33 já filtrado) |
| 3 | Controle e Processos Industriais | `311, 313` | ✓ inclui |
| 4 | Gestão e Negócios | `351, 354, 391` (excl. 351605, 354820) | ✓ inclui |
| 5 | Turismo, Hospit. e Lazer | `371, 354820` | ✓ inclui |
| 6 | Informação e Comunicação | `317` | ✓ inclui |
| 7 | Infraestrutura | `312, 318` | ✓ inclui |
| 8 | Militar | — | excluído (CBO 0xxx) |
| 9 | Produção Alimentícia | — | excluído (CBO 7-8) |
| 10 | Produção Cultural e Design | `374, 376` | ✓ inclui |
| 11 | Produção Industrial | `314, 300` | ✓ inclui |
| 12 | Recursos Naturais | `301` | ✓ inclui |
| 13 | Segurança | `351605` | ✓ inclui |

## Gargalo confirmado (diagnose 2026-05-05)

**BD não tem mapping curso INEP → eixo.** Diagnose confirmou:

```
basedosdados.br_inep_censo_escolar:
  matricula.id_curso_educ_profissional       (código INEP, sem nome)
  docente.id_curso_educ_profissional         (código INEP, sem nome)
  turma.id_curso_educacao_profissional       (código INEP, sem nome)

basedosdados.br_bd_diretorios_brasil:
  Nenhuma tabela cnct/curso_tecnico/eixo
```

**Fonte oficial do mapping**: dicionário INEP do Censo Escolar (publicado
junto com microdados anuais como `TABELAS_INTRODUTORIAS.xlsx`). A
planilha contém aba "TABELA - CURSOS DA EDUCAÇÃO PROFISSIONAL" com:
- `ID_CURSO_EDUC_PROFISSIONAL` (código INEP)
- `NO_CURSO_EDUC_PROFISSIONAL` (nome do curso)
- `ID_EIXO_TECNOLOGICO` + `NO_EIXO_TECNOLOGICO` (eixo)

**Implementação proposta** (ciclo separado):
1. Script `etl/scripts/parse_inep_cursos_eixos.py`:
   - Baixa XLSX do dicionário INEP (URL precisa ser determinada — INEP
     muda a cada ano de microdado publicado)
   - Parser da aba "TABELA - CURSOS DA EDUCAÇÃO PROFISSIONAL"
   - Output: `etl/reference/inep_id_curso_to_eixo.csv` com colunas
     `id_curso, nome_curso, eixo_tecnologico`
2. Aderência só passa a calcular após o CSV estar populado.
3. Cycle: validar com 1 UF antes de propagar.
