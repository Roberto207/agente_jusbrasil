# ADR-013: LLM opcional como leitor de campos difíceis

**Status:** **Não adotado** (25/09) — era "Aceito, ligado só se a medição mostrar ganho"
**Data:** 2026-09-17 · **Revisão:** 2026-09-25

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

## Revisão de 25/09 — por que não foi adotado

A medição foi feita antes de implementar: a **fila de difíceis está vazia**. Nenhuma citação extraída
ficou sem campos lidos na amostra (192), no sintético base e no diversificado (994 cada) e no texto real
do LeNER-Br `train`+`dev` (1.426). Isso é estrutural: o padrão que extrai e o leitor de campos usam a
mesma gramática, e o encoder (ADR-011) só deixa passar citação que as regras conseguem ler. Os casos do
Contexto também não geram fila: em `RE 123 AgR` o regex extrai a parte que sabe ler (`RE 123`) e deixa o
sufixo `AgR` fora do span. Esse sufixo continua sem regra, mas o LLM não o resolveria, porque ele só é
chamado quando os campos **não** são lidos.

Sem fila, o LLM não teria o que ler, e custaria ~15 GB de GPU, carregamento a cada execução e o risco
de saída diferente entre hardwares. Decisão da equipe: Fase 5 deixada de lado, `usar_llm = false`. O
código dormente (`decisao/llm.py` e correlatos) está listado para remoção em
`docs/gerais/auditoria_codigo.md`, seção 0. O LLM **foi** usado fora da execução, para gerar dados
(Qwen2.5-7B-Instruct, camada 2 do sintético — ADR-012).
