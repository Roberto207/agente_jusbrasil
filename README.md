# Verificador de citações — Jusbrasil × BRACIS 2026

Lê pareceres jurídicos (`.txt`), acha as citações de jurisprudência e de lei, consulta a base do
desafio e classifica cada uma em `real`, `inventada` ou `incompleta`, gerando o `submission.csv` e a
nota oficial.

**Como acha as citações:** regras (regex) são a camada principal. Um **encoder** (BERTimbau ajustado,
rodando em CPU) funciona como rede de segurança: só acrescenta citações onde as regras não acharam nada,
e cada uma passa por filtros antes de entrar (ADR-011, decisão da equipe em 25/09). **A classificação é
sempre por regras e pela base**, nunca por modelo. Não há LLM na execução.

**Estado (25/09):** nota **1,100** na amostra oficial (192/192 citações), mesma saída byte a byte na
nossa máquina e no Kaggle. Histórico e números em `docs/resultado_submissoes.md`; decisão do encoder em
`docs/relatorio-uso-encoder.md`; plano em `tarefas_equipe.md`.

## Modelos e dados publicados

| Artefato | Link | Revisão fixa |
|---|---|---|
| Encoder (pesos, tokenizador, card) | [`Roberto2799/jusbrasil-encoder-citacoes`](https://huggingface.co/Roberto2799/jusbrasil-encoder-citacoes) | `d91d09142fdc2601cad04b8df1d509d87c5a1552` |
| Dataset sintético (camadas 1 e 2) | [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado) | `0209a853e6e59b263b138200963b579105baca24` |

O link e a revisão do encoder estão em `verificador.toml`. Na primeira execução, os pesos (~420 MB) são
baixados do Hugging Face **sem token** (repositório público). Sem internet, baixe antes (ou use o cache
do Hugging Face) — é a única chamada de rede da execução.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # o encoder roda em CPU
pip install -r requirements.txt
pip install --no-deps -e .
```

Os dados oficiais ficam em `desafio-jusbrasil-bracis-2026/` (fora do git): `txt/`,
`desafio1_bracis.db`, `json_to_submission.py`, `kaggle_metric.py` e, na fase de treino,
`goldenset_offsets.csv`.

## Comando exato que gera a submissão

```bash
D=desafio-jusbrasil-bracis-2026
python -m verificador indexar --dados $D
python -m verificador rodar   --entrada $D/txt --run final --saida runs --dados $D
# → runs/final/submission.csv  (+ jsons/, rastro.jsonl, manifesto.json)
```

Com gabarito (fase de treino), a nota sai com:

```bash
python -m verificador avaliar --run final --saida runs --dados $D
```

Na amostra, o `submission.csv` tem sha256 `4c6e3538b46fc0be…` e a nota é 1,099999951 (o Kaggle mostra
1,100 ou 1,09999, conforme arredonda ou corta).

## Reprodução e determinismo

- **Toda submissão sai de uma tag git `sub-NNN`** e de um notebook do Kaggle (`notebooks/kaggle/`,
  o mais recente é o `08_sub-006.ipynb`), na imagem `gcr.io/kaggle-gpu-images/python:v170`.
- `python -m verificador submeter --run <run> --criar-tag` confere árvore limpa, repete a execução duas
  vezes (R49) e só cria a tag se os CSVs forem idênticos.
- O `Dockerfile` parte da mesma imagem do Kaggle. **`docker build` não foi testado** aqui (a imagem tem
  vários GB); a reprodução de referência é o notebook.
- Cada execução grava `manifesto.json`: commit, configuração, versões das bibliotecas, GPU e hashes.

## Outros comandos

```bash
python -m verificador ambiente                                       # só o manifesto
python -m verificador rodar ... --sem-encoder                        # só regras
python -m verificador comparar --run antes --run depois              # diferença de nota e de citações
python -m verificador avaliar --run x --conjunto controle            # amostra | ajuste | controle | sintetico
python -m verificador gerar-sintetico --dados $D --saida sintetico/ --pares 100
python -m verificador calibrar --run base --run-sintetico sint --gabarito-sintetico sintetico/goldenset_offsets.csv
python -m verificador.treino.regua --splits train dev                # régua do encoder no LeNER-Br
```

Configuração em `verificador.toml` (o hash entra no manifesto). A nota alta na amostra não prova
generalização: ela é a mesma do leaderboard de treino. Quem mede generalização é o controle, o
sintético e o LeNER-Br (ADR-009).

## Testes

```bash
pytest          # só regras por padrão; os testes do encoder usam um encoder falso
VERIFICADOR_USAR_ENCODER=1 pytest   # com o encoder de verdade (precisa de torch e baixa os pesos)
```

## Encoder: treino e reprodução dos pesos

`notebooks/kaggle/07_treino_encoder_enc-001.ipynb` (tag `enc-001`) refaz o dataset de treino
(`python -m verificador.treino.dataset`), confere o sha256 e treina o modelo. Fontes, hiperparâmetros e
métricas estão no card do modelo (`docs/modelos/card-jusbrasil-encoder-citacoes.md`).
