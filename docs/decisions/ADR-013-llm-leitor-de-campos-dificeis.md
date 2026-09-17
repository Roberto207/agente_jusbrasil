# ADR-013: LLM opcional como leitor de campos difíceis

**Status:** Aceito — ligado só se a medição mostrar ganho
**Data:** 2026-09-17

## Contexto

Algumas citações não são lidas pelas regras: classe depois do número (`RE 123 AgR`), OCR pesado,
apelido de lei fora da tabela. Sem os campos, a citação cai em caminho errado. O ambiente de
avaliação tem GPU de 24 GB.

## Decisão

Citações que o leitor por regras não consegue ler vão para uma fila. Um LLM de licença Apache 2.0
(candidatos: Qwen3 8B, Gemma 4 E4B), carregado uma vez, lê a fila **em lote**, com temperatura 0 e
semente fixa, e devolve JSON com os campos. **O número só é aceito se seus dígitos puderem ser
obtidos do trecho normalizado**; senão, a citação fica sem número. O LLM nunca decide a classe. Fica
atrás de uma chave; entra na submissão só se melhorar o score no conjunto de controle.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| LLM para todas as citações | Custo sem ganho onde as regras já leem |
| Aceitar o número do LLM sem conferência | LLM "corrige" OCR inventando dígitos |
| Fine-tuning do LLM | Custo alto, ganho incerto no prazo |

## Consequências

### Positivas
Cobre casos raros sem virar o centro do sistema.

### Negativas
GPU na execução; risco de saída diferente entre hardwares (ADR-014).

### Mitigação
Conferência de dígitos torna variações pequenas irrelevantes; modo sem LLM sempre disponível.
