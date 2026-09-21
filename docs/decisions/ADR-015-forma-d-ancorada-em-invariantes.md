# ADR-015: Forma (d) ancorada em invariantes, não em conjunções

**Status:** Proposto
**Data:** 2026-09-21

## Contexto

Fechadas as causas 2 e 4, o resíduo do recall são 72 citações, todas forma (d) e todas `incompleta` — a
classe de F1 mais baixo (0,83 contra 1,00 e 0,99). O padrão atual transcreve as quatro conjunções da
amostra (`proferido em … pela relatoria de`, `da relatoria de`, `sob relatoria de`, `Rel. Min.`): trocar as
palavras de ligação o cega. O organizador avisa que o conjunto cego traz formas que a amostra não tem.
Não há fonte externa para calibrar — a base oficial é de acórdãos, que citam processos **com** número.

## Decisão

`_compilar_sem_numero` passa a ancorar nos invariantes das 31 citações reais da amostra: gatilho
(substantivo ou classe processual), tribunal do conjunto fechado (opcional quando há classe), ano de
quatro dígitos, marcador de relator e nome. O preenchimento entre âncoras é limitado, a ordem é flexível
e o trecho não pode conter número de processo. **O padrão não pode conter literal de conjunção** —
restrição auditável que o impede de decorar molde. Aceite: a precisão de spans segue 1,0 e a amostra
segue 32/32 na forma (d). O encoder (ADR-011) entra apenas se as âncoras não passarem nesse limiar.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Enumerar mais conjunções | É o defeito atual, em escala maior |
| Encoder direto | Gasta cota de GPU e prazo sem linha de base comparável |
| Congelar só-regras | Deixa a forma (d) sem defesa contra frase nova |

## Consequências

### Positivas
Cobre frase não vista sem treino. O regex vira o componente **preciso** da união do ADR-011, útil tanto
no desfecho só-regras quanto no desfecho com encoder.

### Negativas
Âncoras frouxas podem unir trechos não relacionados. Os moldes de teste são escritos por quem escreve o
padrão — nenhuma medida de forma (d) é validável contra dado externo.

### Mitigação
A proibição de literal de conjunção limita o ajuste ao teste. Precisão e τ medidos em todos os conjuntos,
com reversão imediata se a precisão sair de 1,0.
