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

## Revisão de 01/10 — `Dockerfile` enxuto para a avaliação final

**O que mudou no contexto.** Pelas regras finais da Jusbrasil (30/09,
`docs/gerais/regras_envio_final_jusbrasil.md`), a nota sai da **execução da organização com o nosso
Docker**, offline, e o Kaggle não entra no ranking. O motivo da escolha original ("a organização roda no
mesmo ambiente de software das submissões do Kaggle") deixou de valer: o ambiente que conta agora é a
imagem que entregamos.

**Decisão.** O `Dockerfile` parte de `python:3.13-slim` com digest fixo, instala `torch` **só de CPU** e o
`requirements.txt` com versões exatas (`==`), e baixa os pesos do encoder no `docker build`, conferindo o
sha256. A alternativa rejeitada em 17/09 ("`Dockerfile` enxuto") passa a ser a escolhida.

**Por quê.**
- A execução é só CPU (revisão de 25/09); a imagem do Kaggle traz CUDA e milhares de pacotes que não usamos
  e tem dezenas de GB. A enxuta tem 3,44 GB e o build leva ~6 min.
- Um `docker build` que não fecha na máquina da organização é nota zero; uma imagem pequena reduz esse risco
  e permitiu testar o build de verdade antes da entrega (a do Kaggle nunca tinha sido construída aqui).
- Python 3.13 é o mesmo do ambiente local em que o `sha256` foi conferido.

**Custo aceito.** As versões de `torch`/`transformers` não são as da imagem `v170` do Kaggle (que nunca
foram registradas). Em textos onde o encoder acrescenta citações, versões diferentes podem dar previsões
diferentes; na amostra, o encoder não acrescenta nenhuma e o CSV é idêntico.

**Verificação (01/10).** `docker build` ok (pesos com sha256 `4e52bfb6…` conferido no build);
`docker run --network none` com `.db` renomeado e `.txt` montados de fora: duas execuções com encoder e uma
só regex, os três CSVs com sha256 `4c6e3538…` (= `sub-005`/`sub-006`). Detalhes em
`docs/gerais/registro_mudancas_entrega_final.md`, seção 5. O manifesto passa a gravar a imagem real
(`IMAGEM_DOCKER`, definida no `Dockerfile`) em vez do texto fixo `v170`.

