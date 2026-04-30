# Validação de tabelas Base dos Dados

**Status:** v1 — datasets confirmados; colunas exatas pendentes de validação na primeira execução com GCP credentials
**Data:** 2026-04-30

## Datasets confirmados como existentes em BD

Todos os datasets abaixo foram localizados via search/index do basedosdados.org. Tabelas internas e nomes exatos de colunas serão validados na primeira execução do ETL após GCP_SA_KEY estar disponível.

### `basedosdados.br_inep_censo_escolar`
- Cobertura temporal: 1995-2024 (microdados anuais)
- Tabelas esperadas:
  - `matricula` — uma linha por matrícula com flags de modalidade
  - `escola` — uma linha por escola com campos de infraestrutura
  - `docente` ou `docente_basica` — vínculos docentes
  - `turma` — turmas com tipo_oferta/etapa_ensino

### `basedosdados.br_inep_ideb`
- IDEB bianual (anos pares)
- Tabelas esperadas:
  - `escola` — IDEB por escola/ano/etapa

### `basedosdados.br_me_rais`
- RAIS anual (cobertura desde 1985+)
- Tabelas esperadas:
  - `microdados_vinculos` — vínculos formais ativos em 31/dez

### `basedosdados.br_me_caged` (ou `br_mte_caged` em refactors)
- CAGED mensal — Novo CAGED via eSocial (2020+)
- Tabelas esperadas:
  - `microdados_movimentacao` — admissões+desligamentos por mês

### `basedosdados.br_ibge_pnadc`
- PNAD Contínua trimestral
- Tabelas esperadas:
  - `microdados` — pessoas/domicílios da amostra

### `basedosdados.br_inep_indicadores_educacionais`
- Indicadores pré-calculados pelo INEP
- Tabelas esperadas:
  - `escola` — taxas de aprovação/reprovação/abandono por escola/ano/etapa
  - Possivelmente cortes por modalidade EPT (validar)

## Pendências de validação na implementação

Antes de cravar SQLs definitivos, primeiro acesso com GCP credentials precisa:

1. `INFORMATION_SCHEMA.TABLES` em cada dataset — confirmar nomes exatos
2. `INFORMATION_SCHEMA.COLUMNS` em cada tabela relevante — listar todas as colunas
3. Validar nomes específicos:
   - `tipo_oferta` ou `tipo_oferta_basica` ou `modalidade`
   - `etapa_ensino` codes — quais identificam EPT integrada (códigos 25-30 historicamente)
   - `dependencia_administrativa` valores: 1=federal, 2=estadual, 3=municipal, 4=privada
   - `situacao_aluno` valores que identificam concluinte
   - `in_internet_alunos` ou `in_internet_aprendizagem` — qual existe pós-2022
   - Persistência ou não de `id_aluno` cross-year (já assumido como NÃO publicamente)
   - Codificação de `grau_instrucao` em RAIS — confirmar 11 níveis
   - CBO 2002 codes — família 3xxxx para técnicos de nível médio

## Estratégia de validação durante execução

1. Antes de rodar queries de produção, executar smoke check:
   ```sql
   SELECT column_name, data_type
   FROM `basedosdados.br_inep_censo_escolar.INFORMATION_SCHEMA.COLUMNS`
   WHERE table_name = 'matricula'
   ORDER BY ordinal_position;
   ```
2. Comparar contra esperado; se há divergência, atualizar `etl/queries/<codigo>.sql`
3. Ajustes ficam versionados no git (auditável)

## Plano de ação

- [ ] Implementação inicial usa **placeholders esperados** baseados em documentação pública e versões anteriores conhecidas
- [ ] Primeira execução com GCP rodada manual — script `etl/validate.py` faz introspecção e reporta divergências
- [ ] Ajustes nas queries entram como primeiro PR após validação
- [ ] CI passa a validar schemas a cada refresh

## Riscos identificados

- **R1: Refactors recentes em BD podem ter renomeado tabelas.** Mitigação: introspection script.
- **R2: Algumas colunas podem ter sido removidas/renomeadas em onda específica.** Mitigação: backfill começa em 2020; queries com COALESCE quando aplicável.
- **R3: Cobertura temporal pode estar fragmentada.** Mitigação: validar `MIN/MAX(ano)` por dataset antes do backfill 5 anos.
