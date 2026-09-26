# ADR-008: Confiança pela taxa de acerto do caminho de decisão

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

O campo `confianca` rende até +10% se o Brier for baixo, e nunca pune quem não envia. O núcleo
é determinístico (ADR-001): não há probabilidade saindo de modelo. Mas cada citação termina num
caminho identificável — "número exato, 1 candidato", "número com correção de OCR, 1 candidato",
"sem número", "número ausente", "vários candidatos"...

## Decisão

Cada caminho de decisão tem um nome estável. Uma tabela gerada pela avaliação guarda, por caminho,
a taxa de acerto de classe (e de link, para real) medida no conjunto de controle; a `confianca`
de uma citação é o valor do seu caminho. Caminho com menos de 5 ocorrências usa a taxa média da
sua classe. A tabela é regenerada a cada versão, nunca editada à mão.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Não enviar confiança | Abre mão de até 10% sem risco nenhum de ganho |
| Confiança constante alta | Brier ruim justamente nos casos difíceis |
| Calibração isotônica sobre um score | Não há score contínuo; 192 exemplos são pouco |

## Consequências

### Positivas
Calibração honesta, explicável e barata.

### Negativas
Taxas medidas na amostra podem ser otimistas para o conjunto final.

### Mitigação
Medir no conjunto de controle, não na parte da amostra usada para ajustar regras.

## Revisão de 25/09 — como ficou

A tabela existe (`avaliacao/taxa_acerto.json`), mas hoje **todas as células usam a constante 0,999318**:
o controle tem 301 observações e nenhum erro, então dividir por caminho nunca bate a constante em Brier,
e o `calibrar.py` herda a constante por construção (R26). Simulado com a métrica oficial, constante ×
1,0 dá diferença desprezível (±0,0000004 por erro); o que pesaria seria confiança baixa **nas
citações que erram**, e para isso falta uma base com erros de classificação. A tabela variável está
**pausada** (`specs/confianca_variavel.md`) até o leaderboard público da fase final abrir.
