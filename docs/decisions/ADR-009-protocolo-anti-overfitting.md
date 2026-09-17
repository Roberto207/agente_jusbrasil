# ADR-009: Protocolo contra decorar a amostra

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

A amostra tem 26 documentos gerados por poucos moldes de frase ("julgado do X proferido em
AAAA pela relatoria de Y", "precedente do X de AAAA, da relatoria de Y"). O leaderboard da fase de
treino usa essa mesma amostra, com gabarito aberto: é possível chegar perto de 1,1 decorando. O
ranking final vem de 60% de um conjunto cego que pode ter moldes, leis e formas de alucinação que
não aparecem aqui (lei incompleta, número emprestado).

## Decisão

Três regras. (1) Os documentos da amostra são divididos em duas partes fixas, estratificadas por
nível: uma para ajustar regras, outra só para medir. (2) Um gerador sintético produz documentos
com citações da base, números perturbados, ruído de OCR e moldes de frase variados; ele é o
conjunto de controle principal. (3) Nenhuma regra, id, trecho ou offset específico de documento
entra no código (R43), a saída não depende do nome dos documentos (R41), e o leaderboard
da fase de treino não é usado como sinal de qualidade. Quando o conjunto final chegar, seus
documentos só são processados — nunca lidos para ajustar regras (Foundational 4b; tentar inferir o
teste privado desclassifica).

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Usar toda a amostra para ajustar e confiar no leaderboard | É o mesmo dado dos dois lados |
| Validação cruzada sobre 26 documentos | Os moldes se repetem entre documentos; não mede generalização |

## Consequências

### Positivas
Número honesto sobre o que acontece fora da amostra.

### Negativas
O gerador é trabalho extra e pode reproduzir os vieses de quem o escreveu.

### Mitigação
Moldes do gerador escritos por quem não escreveu os padrões de extração.
