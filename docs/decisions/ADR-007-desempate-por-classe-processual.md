# ADR-007: Desempate por classe processual e conflito de campos

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

O mesmo número de processo aparece em vários registros da base: recursos internos do mesmo
processo (`REsp 1.640.323` e `AgInt no AgInt no REsp 1.640.323`), e dezenas de números CNJ
repetidos no STM e no TSE. Na amostra, uma real tinha dois candidatos. Nenhuma inventada
reaproveita número existente, mas é a alucinação mais plausível do conjunto final.

## Decisão

Com mais de um candidato, filtrar em ordem: tribunal, UF, classe processual principal (`REsp`,
`HC`, `Rcl`...) e cadeia de recursos internos (`AgInt no`, `EDcl no`). Cadeia ausente na citação
é compatível com qualquer cadeia; cadeia presente precisa bater. Se sobrar um: `real`. Se sobrarem
vários: `incompleta` (R7). Se o número existe mas tribunal, UF ou classe principal **explícitos**
contradizem todos os candidatos: `inventada` (R40). Siglas e nomes por extenso de classe
processual vêm de uma tabela versionada.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Mais de um candidato → sempre incompleta | Perde reais que a cadeia de recursos resolve |
| Número existente → sempre real | Deixa passar alucinação com número emprestado (τ) |

## Consequências

### Positivas
Usa toda a informação da citação antes de desistir.

### Negativas
Regra de contradição sem exemplo na amostra; UF lida com OCR pode contradizer por engano.

### Mitigação
Casos de contradição entram no conjunto de controle sintético (ADR-009); UF só contradiz se lida
sem correção de OCR.
