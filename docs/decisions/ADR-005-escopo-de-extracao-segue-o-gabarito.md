# ADR-005: O escopo de extração segue o gabarito, não o exemplo do regulamento

**Status:** Aceito — provisório; o tratamento de referências vagas está em análise pela equipe
**Data:** 2026-09-17

## Contexto

O regulamento dá "conforme jurisprudência pacífica do tribunal" como exemplo de `incompleta`.
Na amostra, frases assim aparecem nos textos ("a jurisprudência pacífica desta Corte", "o
entendimento sumulado sobre a matéria", "o artigo correspondente do Código de Processo Civil") e
**não são anotadas**. Toda incompleta anotada traz tribunal ou classe, ano e relator. Também não
são anotados: número dos autos do próprio parecer, protocolo, OAB, folhas e valores (43 números
fora do gabarito, todos desses tipos). Cada extração não anotada é falso positivo.

## Decisão

Extrair só três formas: (1) jurisprudência com número de processo ou de súmula; (2) lei com
artigo; (3) jurisprudência sem número com (tribunal ou classe) + ano + relator. O cabeçalho do
documento é ignorado. Referência genérica não é extraída (R33, R34). A divergência com o
regulamento fica em análise pela equipe.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Seguir o exemplo do regulamento e extrair referências vagas | Falso positivo certo na amostra, que é o único sinal que existe |
| Extrair tudo e deixar a métrica decidir | Falso positivo derruba a precisão das três classes |

## Consequências

### Positivas
Alinhado ao único gabarito disponível.

### Negativas
Se o conjunto final anotar referências vagas, perde recall de `incompleta`.

### Mitigação
Detector de referência vaga implementado atrás de uma chave, desligado; religar é uma linha de
configuração se a análise da equipe concluir que o conjunto final anota essas referências.
