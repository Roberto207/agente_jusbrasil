# ADR-006: Na dúvida, nunca `real`

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

Os erros não custam igual. Inventada predita como real entra em τ e corta até metade da nota
(`s = macroF1 · (1 − 0,5 · τ)`), além de custar FN de inventada e FP de real. Real com id errado
custa um FP. Real predita como incompleta custa FN de real e FP de incompleta, sem τ. E, fora do
jogo, é o erro que carimba uma alucinação como verificada.

## Decisão

`real` só é emitida quando há coincidência exata de número (ou lei + artigo) **e** resolução
única depois do desempate (ADR-007). Qualquer caminho que termine em dúvida — número lido com
correção de OCR ambígua, mais de um candidato, campos contraditórios — sai como `incompleta` ou
`inventada`, nunca `real`. Semelhança de metadados (tribunal, ano, relator) nunca promove uma
citação a `real` (R14).

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Escolher o candidato mais provável | Troca um FP barato por risco de τ |
| Decidir por limiar de score de similaridade | Não há score calibrado; reabre o caminho da semelhança |

## Consequências

### Positivas
τ tende a zero por construção.

### Negativas
Perde reais legítimas com número muito corrompido pelo OCR.

### Mitigação
O dump de erros separa "real perdida por dúvida" para melhorar a normalização (ADR-003) em vez de
relaxar a regra.
