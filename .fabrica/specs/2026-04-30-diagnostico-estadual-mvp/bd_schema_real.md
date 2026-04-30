# Schema BD real — colunas confirmadas via INFORMATION_SCHEMA

Pesquisa feita em 2026-04-30 via `etl/introspect.py` + workflow `introspect-bd.yml`. Output completo em workflow artifact `bd-schema-report` (run #25171983981).

## Tabelas confirmadas

| Dataset | Tabela | Cols | Notas |
|---|---|---|---|
| `br_inep_censo_escolar` | `matricula` | 96 | EPT filter: `id_curso_educ_profissional IS NOT NULL` |
| `br_inep_censo_escolar` | `escola` | 455 | Tem `quantidade_matricula_medio_tecnico` agregada |
| `br_inep_censo_escolar` | `docente` | 126 | Tem `id_turma`, `disciplina_profissionalizante` |
| `br_inep_indicadores_educacionais` | `escola` | 208 | `taxa_aprovacao_em` agregada (não EPT-specific) |
| `br_inep_ideb` | `escola` | 14 | `ensino` STRING (`'medio'`), `ideb` FLOAT64 |
| `br_me_caged` | `microdados_movimentacao` | 25 | `saldo_movimentacao` já assinado, `cbo_2002` STRING |
| `br_me_rais` | `microdados_vinculos` | 66 | `vinculo_ativo_3112` STRING ('1'), `grau_instrucao_apos_2005` STRING |
| `br_ibge_pnadc` | `microdados` | 424 | Códigos IBGE: V2009 (idade), V1028 (peso), VD4002 (ocupação), V3002 (frequência escola) |
| `br_bd_diretorios_brasil` | `municipio` | 27 | Universo de municípios para denominador |

## Colunas-chave por indicador

Detalhamento aplicado no `etl/queries/*.sql` calibrado em 2026-04-30. Cada SQL agora referencia colunas reais.

## Pendências de v2 (real ETL execution)

A calibração das SQLs está completa; falta a camada Python que:

1. Conecta `google-cloud-bigquery` em `etl/build.py::run_indicator()`
2. Para cada indicador, transforma o DataFrame retornado na estrutura aninhada esperada pelos renderers do frontend (`total_estado`, `rede_estadual`, com sub-campos específicos por indicador)
3. Calcula benchmark cruzando os 27 estados (top-quartile, média ponderada por pop 15-29, posição 1-27)
4. Aplica caveats automáticos (ano vintage, quando dado é parcial)

Estimativa: ~1 dia de eng. com testes. Cada indicador exige um processador custom porque a forma do JSON varia (sparkline vs distribuição vs single value vs ranking).

## Como retomar

```bash
gh workflow run introspect-bd.yml --repo franciscomelloc/scintilla-inteligencia
gh run download <id> --name bd-schema-report
# Edita etl/build.py para substituir placeholder
# Roda local: GCP_BILLING_PROJECT=scintilla-ia uv run python etl/build.py --uf MG
# Itera por indicador
```

## Lookups que precisam ser preparados antes

- `etl/reference/cnct_curso_eixo.csv` — parsing do Catálogo Nacional de Cursos Técnicos v4 (PDF MEC) → CSV `id_curso,eixo`. Necessário para `cob_eixos_cobertos` e `cob_distribuicao_modalidade`.
- `etl/reference/etapa_ensino_modalidade.csv` — mapping `etapa_ensino_codigo,modalidade` (integrada/concomitante/subsequente/EJA/FIC). Necessário para `cob_distribuicao_modalidade` e `din_crescimento_matriculas_5y`.
