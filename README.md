# Verificador de citações — Jusbrasil × BRACIS 2026

Lê pareceres jurídicos (`.txt`), acha as citações de jurisprudência e de lei, consulta a base do
desafio (`.db`) e classifica cada uma em `real`, `inventada` ou `incompleta`, gerando o CSV de submissão.

## Execução (avaliação final)

Um comando, sem internet, com `.db` e pasta de `.txt` de qualquer nome e em qualquer lugar.

### Com Docker (ambiente declarado)

```bash
docker build -t verificador .          # único passo com rede: instala dependências e baixa os pesos

docker run --rm --network none \
    -v /caminho/dos/dados:/dados:ro \
    -v /caminho/da/saida:/saida \
    verificador /dados/<base>.db /dados/<pasta_txt> /saida/submission.csv
```

O `ENTRYPOINT` da imagem é o `run.sh`; os três argumentos são os mesmos dele. Só com regras (sem encoder,
sem `torch`):

```bash
docker run --rm --network none -v ...:/dados:ro -v ...:/saida --entrypoint bash \
    verificador run_sem_encoder.sh /dados/<base>.db /dados/<pasta_txt> /saida/submission.csv
```

### Sem Docker

```bash
pip install -r requirements.txt        # Python ≥ 3.11 (validado em 3.13); torch só de CPU
python -c "from huggingface_hub import snapshot_download; \
  snapshot_download('Roberto2799/jusbrasil-encoder-citacoes', revision='d91d09142fdc2601cad04b8df1d509d87c5a1552')"

bash run.sh            <caminho_db> <pasta_txt> <arquivo_saida>   # regras + encoder (padrão)
bash run_sem_encoder.sh <caminho_db> <pasta_txt> <arquivo_saida>  # só regras
```

### O que sai

```
<arquivo_saida>                          CSV no formato das submissões (documento_id, citacoes)
<arquivo_saida sem extensão>_artefatos/execucao/
    jsons/<documento_id>.json            um JSON por documento, no contrato do desafio
    rastro.jsonl                         caminho de decisão de cada citação
    manifesto.json                       commit, imagem, versões, revisão do modelo, hashes, tempos
    submission.csv                       o mesmo CSV
```

O CSV é gerado pelo `json_to_submission.py` **oficial, sem modificação** (cópia em
`src/verificador/saida/oficial/`, hash conferido por teste). Se qualquer etapa falhar, o comando sai com
código ≠ 0, mensagem `erro: …` e **não grava CSV**. Se o encoder não puder ser carregado, a mensagem indica o
`run_sem_encoder.sh`.

## Abordagem

1. **Índice da base** (`src/verificador/base/`): a cada execução, o `.db` recebido é lido **em modo somente
   leitura** e vira um índice por número próprio do processo, súmula ou lei + artigo, com tribunal, classe,
   UF, ano e relator. É o nosso "enriquecimento do `.db`": gerado do zero a partir de qualquer `.db` no
   formato original, sem arquivo pré-calculado e sem gravar nada na base.
2. **Texto** (`texto/`): separa o cabeçalho (números de autos e protocolo não são citações) e normaliza
   ruído de OCR mantendo um mapa para os offsets do texto original.
3. **Extração** (`extracao/`): **regras (regex)** são a camada principal, nas quatro formas de citação. Um
   **encoder** (BERTimbau-base ajustado, em CPU) é rede de segurança: só acrescenta citações onde as regras
   não acharam nada, e cada uma passa por filtros (âncora, fora do cabeçalho, campos legíveis) — ADR-011.
4. **Decisão** (`decisao/`): **sempre por regras e pela base**, nunca por modelo. Sem número → `incompleta`;
   sem candidato consistente na base → `inventada`; exatamente um → `real` com o `id_canonico`; mais de um →
   `incompleta`. A `confianca` vem de uma tabela por caminho de decisão.
5. **Saída** (`saida/`): JSON por documento validado contra o contrato (`trecho == texto[inicio:fim]`,
   classes, ids) → conversor oficial → CSV.

Não há LLM nem chamada de rede na execução. Especificação: `specs/DEFINE.md` (requisitos R#) e
`specs/DESIGN.md`; decisões em `docs/decisions/`.

## Modelo e dados publicados

| Artefato | Link | Revisão fixa |
|---|---|---|
| Encoder (pesos, tokenizador, card) | [`Roberto2799/jusbrasil-encoder-citacoes`](https://huggingface.co/Roberto2799/jusbrasil-encoder-citacoes) | `d91d09142fdc2601cad04b8df1d509d87c5a1552` |
| Dataset sintético de treino (camadas 1 e 2) | [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado) | `0209a853e6e59b263b138200963b579105baca24` |

Os pesos estão em `safetensors` (433 MB, sha256 `4e52bfb66fe10ba9c1802a7205047d777f0766745a92992b0f8973091971a2bc`).
O `docker build` baixa essa revisão e confere o sha256; na execução, o encoder só lê do disco
(`local_files_only=True`, `HF_HUB_OFFLINE=1`). Link e revisão também ficam em `verificador.toml` e em cada
`manifesto.json`. O modelo de linguagem usado para gerar parte do sintético rodou só no desenvolvimento.

## Ambiente, tempo e determinismo

- Imagem: `python:3.13-slim` com digest fixo, `torch` 2.14.1 só de CPU e `requirements.txt` com versões
  exatas (ADR-014, revisão de 01/10). Imagem final ≈ 2,6 GB; build ≈ 5 min.
- **Não usa GPU.** O encoder roda em CPU com 4 threads; validado num Docker limitado a 2 CPUs e 4 GB de RAM.
- Tempo medido no Docker com 2 CPUs: ~15 s fixos (carregar bibliotecas e modelo) + ~3,5–4 s por documento
  de ~3 mil caracteres com encoder; só regras, ~0,2 s por documento.
- Sem amostragem nem aleatoriedade na execução; arquivos em ordem fixa; semente e `PYTHONHASHSEED` fixos.
  Duas execuções geram CSV idêntico byte a byte. Na amostra de desenvolvimento, o CSV tem sha256
  `4c6e3538b46fc0bec819dbd4ad765e1462a897448635a0c5c182d920d30f9ffb` nos dois modos.
- `run.sh` usa sempre o `verificador.toml` do repositório (variáveis `VERIFICADOR_*` do ambiente são
  ignoradas).

## Desenvolvimento

```bash
pip install -r requirements.txt && pip install -e ".[dev]"
pytest                                   # testes com regras; os do encoder usam um encoder falso

D=desafio-jusbrasil-bracis-2026          # dados da amostra (fora do git)
python -m verificador rodar   --entrada $D/txt --run x --saida runs --dados $D
python -m verificador avaliar --run x --saida runs --dados $D --conjunto controle   # nota pelo kaggle_metric.py
python -m verificador comparar --run antes --run depois
```

Histórico de notas em `docs/resultado_submissoes.md`; plano e checklist da entrega em `tarefas_equipe.md`
(Fase 7) e `docs/gerais/registro_mudancas_entrega_final.md`. A nota na amostra não prova generalização;
quem mede é o conjunto de controle, o sintético e o LeNER-Br (ADR-009).

**Treino do encoder:** `notebooks/kaggle/07_treino_encoder_enc-001.ipynb` (tag `enc-001`) refaz o dataset
(`python -m verificador.treino.dataset`), confere o sha256 e treina. Fontes, hiperparâmetros e métricas no
card (`docs/modelos/card-jusbrasil-encoder-citacoes.md`).
