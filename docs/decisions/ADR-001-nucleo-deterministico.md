# ADR-001: Decisão determinística; IA na leitura

**Status:** Aceito
**Data:** 2026-09-17
**Revisão:** 2026-09-17 — a versão anterior deixava o LLM "só se a análise de erro justificar".
Revisto porque a análise de erro só enxerga a amostra (poucos moldes) e porque o ambiente de
avaliação tem GPU de 24 GB. Detalhes em `docs/ia_no_pipeline.md`.

## Contexto

A classe depende do que existe na base, não de "entender" o parecer: na amostra, 32/32
incompletas não têm número e 50/50 inventadas de jurisprudência têm número ausente da base. LLMs
não conhecem a cobertura congelada (no benchmark CITE, o melhor verificador por LLM teve F1 de 55%).
Mas regex só cobre os moldes vistos, e o conjunto final pode trazer frases novas.

## Decisão

A **decisão da classe** ([A] índice, [4] decisão) é sempre determinística. A **leitura** do texto
usa IA onde agrega: encoder NER em união com o regex na extração (ADR-011) e LLM opcional para
campos difíceis (ADR-013). LLM também gera dados sintéticos fora da execução (ADR-012).

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| LLM extrai e classifica tudo | Não conhece a base; alucina "real" (τ) |
| RAG decide por semelhança | Parecido não é igual (viola R14) |
| Só regex | Recall frágil no conjunto final |

## Consequências

### Positivas
Decisão explicável e sem τ por construção; leitura mais robusta a frases novas.

### Negativas
Treino, publicação de pesos e GPU na execução.

### Mitigação
Cada componente de IA atrás de chave, com modo só-regras sempre funcional (ADR-014).
