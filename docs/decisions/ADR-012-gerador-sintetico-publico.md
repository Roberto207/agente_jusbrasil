# ADR-012: Gerador de dados sintéticos em duas camadas, publicado

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

192 citações anotadas não bastam para treinar o encoder (ADR-011) nem para medir generalização
(ADR-009). As regras permitem datasets públicos no treino; dados gerados pela equipe valem desde que
publicados. Rotular ou ler o conjunto final é proibido (Foundational 4b).

## Decisão

Duas camadas. (1) **Por código**, com semente fixa: escolhe citações reais da base, fabrica
inventadas (número inexistente, número emprestado com UF ou classe trocada, artigo inexistente de lei
conhecida), incompletas (tribunal + ano + relator) e ruído de OCR; o gabarito sai junto. (2) **Por
LLM** de licença Apache 2.0, temperatura 0 e semente fixa: redige o parecer em volta das citações com
frases variadas, sem alterar os trechos. O dataset gerado e o script são publicados (Hugging Face,
revisão fixa) dentro do prazo. Uma fatia fica reservada como conjunto de controle, nunca usada no
treino.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Só templates por código | Pouca variedade de redação |
| Só LLM | Gabarito e ruído sem controle |

## Consequências

### Positivas
Dados de treino e de teste com gabarito exato; mede generalização.

### Negativas
Reproduz os vieses de quem escreve os moldes e os prompts.

### Mitigação
Moldes e prompts escritos por quem não escreveu os padrões de extração.

## Revisão de 25/09 — como ficou

Camada 2 gerada com **Qwen2.5-7B-Instruct** (Apache 2.0) — o Gemma saiu pela licença (não OSI) —,
decodificação gulosa, o trecho da citação vai ao modelo como marcador e volta byte a byte. As duas
camadas estão publicadas em `Roberto2799/jusbrasil-sintetico-diversificado` @ `0209a853…` (camada 1 em
`base/`). O sintético entrou no treino do encoder (ADR-011) e hoje é resolvido 100% pelo sistema.
