# ADR-005: O escopo de extração segue o gabarito, não o exemplo do regulamento

**Status:** Aceito — **mantido em 2026-09-21** depois de conferir a página Data do desafio; o risco
para o conjunto cego está registrado abaixo e é a pergunta prioritária à organização
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


---

## Revisão de 2026-09-21 — a página Data contradiz o gabarito distribuído

A página **Data** do desafio afirma que referência vaga **é** `incompleta`:

> Uma citação sem identificadores suficientes para sequer formular a consulta — "jurisprudência
> pacífica desta Corte", "o dispositivo legal de regência" — é incompleta sem passar pelo banco.

E descreve um gabarito com **225 citações** (`incompleta` 65) e uma base de **1.016 registros**.

O que está distribuído é outra coisa: `goldenset_offsets.csv` com **192 citações** (`incompleta` 32)
e base de **1.014**. `real` (96) e `inventada` (64) batem exatamente — **a diferença de 33 é toda de `incompleta`**.
A contagem das referências vagas nos 26 documentos dá **11**, não 33: a origem da diferença
continua sem explicação.

Um novo download do Kaggle em 21/09 veio **byte a byte idêntico** ao de 15/09: o dataset não mudou.
E a submissão de 21/09 marcou **1,08604** no leaderboard, igual ao cálculo local sobre as 192 —
logo o leaderboard usa o gabarito distribuído, não o descrito na página.

**Decisão mantida**, porque o gabarito distribuído é o que pontua hoje e extrair referência vaga
contra ele seria falso positivo certo.

**Risco registrado:** se o conjunto final anotar as 11 referências vagas e nós não as extrairmos,
o F1 de `incompleta` cai para ~0,85 e o score para ~1,046 — perda de ~0,046. Vale o inverso com a
mesma ordem de grandeza: extraí-las contra um gabarito que não as anota custa o mesmo em precisão.
Sem informação, ligar ou desligar tem valor esperado equivalente; o que tem valor é **poder
escolher**, o que hoje não é possível porque o detector não existe (a flag é ignorada em
`extracao/__init__.py`).
