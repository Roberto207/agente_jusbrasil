# ADR-011: Encoder NER em união com o regex na extração

**Status:** Aceito e **implementado** — encoder ligado na submissão desde a `sub-006` (25/09)
**Data:** 2026-09-17 · **Revisão:** 2026-09-25

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

## Revisão de 25/09 — como ficou

- **Modelo:** BERTimbau-base (MIT) ajustado (`enc-001`), publicado em
  `Roberto2799/jusbrasil-encoder-citacoes` @ `d91d0914…`. RoBERTaLexPT saiu pela licença (CC BY 4.0 não é
  OSI); Legal-BERTimbau perdeu a comparação (é jurídico de Portugal). Detalhes em `tarefas_equipe.md`, Fase 4.
- **Dados de treino:** sintético (camadas 1 e 2), 14 documentos de ajuste da amostra e LeNER-Br `train`
  convertido para a convenção do desafio (sem o número do próprio processo).
- **União, não troca:** o encoder só acrescenta onde o regex não achou nada, com portas (fora do
  cabeçalho; dígito + âncora, artigo só com a lei nomeada; `ler_campos` lê). Inferência em CPU.
- **Go/no-go formal (LeNER-Br `test`, regras congeladas):** jurisprudência 58 → 64/74 (ganho frágil: 5 de
  6 são a mesma OJ num documento); **lei 115 → 173/202** (11 artigos exatos do acervo, com `caput`,
  `parágrafo único`, alíneas). Amostra 192/192, zero espúrios, τ = 0, R49 ok. Decisão da equipe: **GO**.
- **Determinismo entre máquinas:** mesma saída byte a byte localmente e no Kaggle.
- Relatório completo: `docs/relatorio-uso-encoder.md`.
