# Princípios da Fábrica — scintilla-inteligencia

Versão local dos princípios da fábrica Scintilla aplicados ao repo de inteligência.

## Princípios

1. **Pipeline determinístico.** Mesma execução em ambiente limpo produz output idêntico.
2. **Schema versionado.** O frontend depende do contrato JSON estável. Mudanças quebram a UX.
3. **Falha visível.** Se 1 indicador falha, gera `null` + caveat explicativo. Não trava o pipeline.
4. **Custo zero recorrente.** BD/BigQuery free tier (1TB/mês) + GH Actions free tier.
5. **Auditável.** Cada indicador tem fórmula em SQL versionada e fonte rastreável.
6. **Lead-gen estruturalmente embutido.** Onde dado público termina, oferta consultiva começa — explicitamente nos caveats.

## Fluxo de trabalho

- 1 indicador = 1 SQL + 1 entrada em `INDICATOR_CATALOG` + 1 conjunto de tests
- Mudanças estruturais (novo indicador, novo recorte) exigem atualização da spec primeiro
- Spec viva em `.fabrica/specs/2026-04-30-diagnostico-estadual-mvp/`

## Não fazer

- Não tentar tracking longitudinal individual (id_aluno re-hash anual nos microdados públicos)
- Não inferir formação EPT específica em RAIS (não distinguido publicamente)
- Não baixar microdados brutos — agregar por UF em CTE primeiro (BigQuery rate-limit)
- Não commitar credenciais GCP nem dados nominativos

## Dependências obrigatórias do humano

Setup inicial requer 4 cliques de Francisco (ver README.md):
1. Projeto GCP + billing
2. Service account JSON → secret `GCP_SA_KEY`
3. PAT cross-repo → secret `SITE_REPO_TOKEN`
4. Disparar primeiro `workflow_dispatch`
