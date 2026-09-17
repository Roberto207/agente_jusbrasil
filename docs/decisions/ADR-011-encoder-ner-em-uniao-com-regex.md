# ADR-011: Encoder NER em união com o regex na extração

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

Regex cobre os moldes da amostra, mas o Nível 2 (peso 2×) e o conjunto final trazem variação de
superfície imprevisível. Em NER português, LLMs locais zero-shot ficaram em F1 ~0,55 no LeNER-Br,
contra 0,87–0,92 de modelos supervisionados. Encoders dão posições exatas e são determinísticos.

## Decisão

Um encoder português (candidatos: RoBERTaLexPT, BERTimbau, Legal-BERTimbau — escolha por medição
e por licença compatível com a regra OSI) é treinado como NER (marcação BIO) nos dados sintéticos
(ADR-012), na parte de ajuste da amostra e no LeNER-Br. Na execução, as candidatas do encoder se
**somam** às do regex e passam pelo mesmo filtro das quatro formas de citação e pela resolução de
sobreposição. Pesos publicados no Hugging Face com revisão fixa, dentro do prazo.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Encoder substitui o regex | Regex é preciso nos moldes conhecidos; perderia precisão |
| LLM como extrator | F1 menor, posições por texto gerado, mais GPU |
| GLiNER sem treino | Sem evidência em texto jurídico brasileiro; fica como reserva |

## Consequências

### Positivas
Recall em frases novas; posições nativas; roda em GPU ou CPU.

### Negativas
Convenção de anotação do LeNER-Br difere do gabarito; pode trazer falso positivo.

### Mitigação
Filtro das quatro formas; relatório separa candidatas por origem (regex, encoder, ambos).
