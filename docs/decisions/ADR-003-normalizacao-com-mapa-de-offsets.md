# ADR-003: Normalização de OCR com mapa de offsets

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

O Nível 2 vale o dobro e traz ruído dentro das citações: `5úmula`, `Fedcral`, `21737l8`,
`170076O`, `1.45g.779`, `RE nº 5. 230.808-DF`, quebras de linha dentro do número, `n°`/`No`,
travessão `–`. Os offsets pontuados são codepoints do texto original (conferido: os 192 trechos
do gabarito batem exatamente com `texto[inicio:fim]`). Normalizar o texto muda posições.

## Decisão

A extração roda sobre uma cópia normalizada e produz, junto, um mapa posição-normalizada →
posição-original. Todo span sai convertido pelo mapa antes de virar JSON. A troca letra→dígito
(`l`→`1`, `O`→`0`, `S`→`5`, `g`→`9`) só acontece **dentro de um token que já parece número**,
nunca no texto inteiro. O texto original nunca é alterado; o `trecho` vem dele.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Padrões tolerantes a ruído direto no texto original | Cada padrão vira uma expressão ilegível e a tolerância fica espalhada |
| Normalizar o texto inteiro sem mapa | Quebra os offsets (viola R2, R38) |
| Troca letra→dígito global | Corrompe palavras ("Súmula", nomes de relator) |

## Consequências

### Positivas
Padrões de extração simples; ruído tratado num único lugar e testável isoladamente.

### Negativas
Um bug no mapa desloca todos os spans do documento.

### Mitigação
Teste que confere `texto_original[inicio:fim]` contra o trecho esperado para os 192 casos.
