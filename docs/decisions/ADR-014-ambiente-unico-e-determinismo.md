# ADR-014: Ambiente único de execução e determinismo

**Status:** Aceito
**Data:** 2026-09-17
**Revisão:** 2026-09-17 — o notebook do Kaggle não aceita imagem Docker própria. O ambiente único
passa a ser a imagem oficial do Kaggle com versão fixa, e o `Dockerfile` entregue parte dela.

## Contexto

As regras desclassificam pipeline que não caiba no ambiente de avaliação (1 GPU de 24 GB, ~8 vCPUs,
32 GB de RAM) e exigem reproduzir **as saídas submetidas** com decodificação determinística. As
submissões são geradas em notebook do Kaggle (T4 16 GB, sem bfloat16), que roda sobre a imagem do
próprio Kaggle; a organização roda em L4/A10/4090. Tipo numérico, bibliotecas e hardware diferentes
podem mudar a saída.

## Decisão

Treino e geração de dados rodam em qualquer ambiente. **Toda submissão** sai de um notebook do Kaggle
com: ambiente fixado, código numa tag git, `requirements.txt` com versões fixas, float16, uma única GPU
(guia em `docs/gerais/guia_kaggle.md`). O `Dockerfile` entregue parte da **mesma imagem pública do Kaggle**
(`gcr.io/kaggle-gpu-images/python`, tag fixa) mais o mesmo `requirements.txt`. Cada submissão é gerada
duas vezes; só vale se os CSVs forem idênticos.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Imagem Docker própria no notebook | O Kaggle não permite |
| `Dockerfile` enxuto com as mesmas versões | Menos fiel ao ambiente das submissões |
| Duas T4 juntas | Não prova que cabe em uma GPU |

## Consequências

### Positivas
Organização roda no mesmo ambiente de software das submissões.

### Negativas
Imagem do Kaggle é grande; hardware continua diferente.

### Mitigação
LLM só com conferência (ADR-013); manifesto registra imagem, GPU e driver.

## Revisão de 25/09 — como ficou

- **Determinismo entre máquinas conferido:** a `sub-006` (regex + encoder) deu `submission.csv`, JSONs
  e rastro idênticos byte a byte na máquina local e no Kaggle, e duas execuções no Kaggle também.
- **A execução não usa GPU:** o encoder roda em CPU justamente para a saída não depender de hardware.
  "float16, uma GPU" continua valendo só para o treino e para a geração de dados.
- **Imagem:** o Kaggle expõe o hash real em `KAGGLE_DOCKER_IMAGE`
  (`gcr.io/kaggle-gpu-images/python@sha256:37c64f7dd9c54116…` na `sub-006`). A tag `v170` gravada no
  manifesto é texto fixo, não conferido. O `Dockerfile` final deve fixar o hash.
- A execução da `sub-006` usou duas T4 por engano; para a próxima, **T4 ×1**.
