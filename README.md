# Verificador de citações — Jusbrasil × BRACIS 2026

Lê pareceres jurídicos (`.txt`), acha as citações de jurisprudência e de lei, consulta a base do
desafio (`.db`) e classifica cada uma em `real`, `inventada` ou `incompleta`, gerando o CSV de submissão.

**Equipe:** Guerreiros da T7 · **Integrantes:** Roberto Caetano Neto, Caio Gonçalves Sardinha, Beatriz de Moura Guimarães

## Início rápido

**Recomendado: Docker.** O `docker build` instala as dependências nas versões exatas **e já baixa e confere os
pesos do encoder** (revisão fixa + sha256); depois disso a execução não depende de nada fora da imagem. Sem
Docker, esses passos ficam por sua conta (seção "Sem Docker").

Pré-requisitos: Docker (testado em Linux e no Docker Desktop do Windows), ~3 GB de disco e internet **só no
`docker build`**. Não usa GPU (não precisa de `--gpus`).

Supondo os dados num layout como o da amostra (`/caminho/dados/base.db` e `/caminho/dados/txt/*.txt`):

```bash
git clone https://github.com/Roberto207/agente_jusbrasil.git && cd agente_jusbrasil
docker build -t verificador .            # instala as dependências e baixa os pesos (~5 min)

mkdir -p /caminho/saida
docker run --rm --network none \
    -v /caminho/dados:/dados:ro \
    -v /caminho/saida:/saida \
    verificador /dados/base.db /dados/txt /saida/submission.csv
echo $?                                  # 0 = deu certo; o CSV está em /caminho/saida/submission.csv
```

Os três argumentos são os do `run.sh` (o `ENTRYPOINT` da imagem): `<caminho_db> <pasta_txt> <arquivo_saida>`,
todos **caminhos de dentro do container**. Os nomes são livres. Se o `.db` e a pasta de `.txt` estiverem em
lugares diferentes no host, monte cada um separadamente:

```bash
docker run --rm --network none \
    -v /outro/lugar/base_final.db:/dados/base.db:ro \
    -v /mais/um/lugar/pareceres:/dados/txt:ro \
    -v /caminho/saida:/saida \
    verificador /dados/base.db /dados/txt /saida/submission.csv
```

## Dois modos

| Comando | O que roda | Quando usar |
|---|---|---|
| `run.sh` (padrão da imagem) | regras + encoder | é o modo da entrega |
| `run_sem_encoder.sh` | só regras, sem `torch` e sem pesos | se o encoder não carregar na sua máquina |

No Docker, o modo só regras é:

```bash
docker run --rm --network none -v /caminho/dados:/dados:ro -v /caminho/saida:/saida \
    --entrypoint bash verificador run_sem_encoder.sh /dados/base.db /dados/txt /saida/submission.csv
```

Não há troca automática de modo: se o encoder falhar, o `run.sh` para com erro e indica o comando acima.

## Sem Docker

Possível, mas **o recomendado é o Docker**: sem ele, você instala as dependências e baixa os pesos do encoder à
mão (passos abaixo), e o ambiente deixa de ser exatamente o testado.

| Sistema | Situação |
|---|---|
| Linux | testado |
| Windows | testado com Git Bash (o `run.sh` é bash; no PowerShell/cmd puro não roda — use Git Bash ou WSL) |
| macOS | **use o Docker**: o `torch==…+cpu` do `requirements.txt` não existe para Mac, então o `pip install` falha. O modo só regras roda sem `torch` (basta `pip install pandas numpy`) |

Python ≥ 3.11 (validado em 3.13).

```bash
pip install -r requirements.txt
# baixa os pesos do encoder para o cache local (no Docker isso acontece sozinho no build)
python -c "from huggingface_hub import snapshot_download; \
  snapshot_download('Roberto2799/jusbrasil-encoder-citacoes', revision='d91d09142fdc2601cad04b8df1d509d87c5a1552')"
# a partir daqui, sem rede
bash run.sh             <caminho_db> <pasta_txt> <arquivo_saida>   # regras + encoder
bash run_sem_encoder.sh <caminho_db> <pasta_txt> <arquivo_saida>   # só regras
```

## O que sai e como conferir

```
<arquivo_saida>                                  CSV no formato das submissões (documento_id, citacoes)
<pasta do CSV>/<nome do CSV sem extensão>_artefatos/execucao/
    jsons/<documento_id>.json                    um JSON por documento, no contrato do desafio
    rastro.jsonl                                 caminho de decisão de cada citação
    manifesto.json                               imagem, versões, revisão do modelo, hashes, tempos
    submission.csv                               o mesmo CSV
```

A pasta `_artefatos/` é criada **ao lado do CSV**, então a pasta de saída precisa aceitar escrita. No Docker
os arquivos saem com dono `root`; para sair com o seu usuário, acrescente `--user "$(id -u):$(id -g)"` ao
`docker run`.

O CSV é gerado pelo `json_to_submission.py` **oficial, sem modificação** (cópia em
`src/verificador/saida/oficial/`, hash conferido por teste).

**Conferência na amostra de desenvolvimento:** com o `.db` e os 26 `.txt` da amostra, o CSV tem sha256
`4c6e3538b46fc0bec819dbd4ad765e1462a897448635a0c5c182d920d30f9ffb`, nos dois modos e em execuções repetidas.

### Erros

Toda falha sai com código ≠ 0, mensagem `erro: …` no terminal e **nenhum CSV gravado**.

| Mensagem / código | Causa |
|---|---|
| código 2, `uso: bash run.sh …` | número errado de argumentos |
| `erro: base não encontrada` / `não foi possível ler a base` | caminho do `.db` errado (lembre: caminho de dentro do container) ou arquivo que não é SQLite |
| `erro: pasta de .txt não encontrada` / `nenhum .txt em …` | pasta errada ou sem arquivos `.txt` |
| `erro: não foi possível carregar o encoder …` | pesos ou `torch` ausentes; a mensagem traz o repositório e a revisão dos pesos e o comando `run_sem_encoder.sh` |

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

Não há LLM nem chamada de rede na execução. Requisitos em `specs/DEFINE.md` (R#), arquitetura em
`specs/DESIGN.md`, decisões em `docs/decisions/`.

## Modelo e dados publicados

| Artefato | Link | Revisão fixa |
|---|---|---|
| Encoder (pesos, tokenizador, card) | [`Roberto2799/jusbrasil-encoder-citacoes`](https://huggingface.co/Roberto2799/jusbrasil-encoder-citacoes) | `d91d09142fdc2601cad04b8df1d509d87c5a1552` |
| Dataset sintético de treino (camadas 1 e 2) | [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado) | `0209a853e6e59b263b138200963b579105baca24` |

Os pesos estão em `safetensors` (433 MB, sha256 `4e52bfb66fe10ba9c1802a7205047d777f0766745a92992b0f8973091971a2bc`).
O `docker build` baixa essa revisão e confere o sha256 (se não bater, o build falha); na execução, o encoder
só lê do disco (`local_files_only=True`, `HF_HUB_OFFLINE=1`). Link e revisão também ficam em
`verificador.toml` e em cada `manifesto.json`. O modelo de linguagem usado para gerar parte do sintético rodou
só no desenvolvimento.

## Ambiente, tempo e determinismo

- Imagem: `python:3.13-slim` com digest fixo, `torch` 2.14.1 só de CPU e `requirements.txt` com versões
  exatas (ADR-014, revisão de 01/10). Imagem final ≈ 2,6 GB; build ≈ 5 min.
- O encoder roda em CPU com 4 threads; validado em Docker limitado a 2 CPUs e 4 GB de RAM.
- Tempo com 2 CPUs: ~15 s fixos (bibliotecas e modelo) + ~3,5–4 s por documento de ~3 mil caracteres com
  encoder; só regras, ~0,2 s por documento.
- Sem amostragem nem aleatoriedade na execução; arquivos em ordem fixa; semente e `PYTHONHASHSEED` fixos.
- `run.sh` usa sempre o `verificador.toml` do repositório (variáveis `VERIFICADOR_*` do ambiente são
  ignoradas).

## Mapa do repositório

| Caminho | O que é |
|---|---|
| `run.sh`, `run_sem_encoder.sh` | pontos de entrada da avaliação (definem modo offline e semente) |
| `Dockerfile`, `requirements.txt` | ambiente declarado |
| `verificador.toml` | configuração entregue: encoder ligado, link + revisão, semente |
| `src/verificador/cli.py` | subcomando `executar` (o que o `run.sh` chama) e os de desenvolvimento |
| `src/verificador/{base,texto,extracao,decisao,saida}/` | as etapas da abordagem acima |
| `src/verificador/saida/oficial/json_to_submission.py` | conversor oficial, sem modificação |
| `tests/` | `pytest`; os testes do encoder usam um encoder falso |
| `specs/`, `docs/decisions/` | requisitos, arquitetura e ADRs |
| `docs/gerais/registro_mudancas_entrega_final.md` | o que mudou para a entrega final e como foi testado |

## Desenvolvimento

```bash
pip install -r requirements.txt && pip install -e ".[dev]"
pytest

D=desafio-jusbrasil-bracis-2026          # dados da amostra (fora do git)
python -m verificador rodar   --entrada $D/txt --run x --saida runs --dados $D
python -m verificador avaliar --run x --saida runs --dados $D --conjunto controle   # nota pelo kaggle_metric.py
python -m verificador comparar --run antes --run depois
```

Histórico de notas em `docs/resultado_submissoes.md`; plano e checklist da entrega em `tarefas_equipe.md`
(Fase 7). A nota na amostra não prova generalização; quem mede é o conjunto de controle, o sintético e o
LeNER-Br (ADR-009).

**Treino do encoder:** `notebooks/kaggle/07_treino_encoder_enc-001.ipynb` (tag `enc-001`) refaz o dataset
(`python -m verificador.treino.dataset`), confere o sha256 e treina. Fontes, hiperparâmetros e métricas no
card (`docs/modelos/card-jusbrasil-encoder-citacoes.md`).
