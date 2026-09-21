# Verificador de citações — Jusbrasil × BRACIS 2026

Pipeline só-regras (sem encoder, sem LLM): lê os `.txt`, acha as citações, consulta a base e
classifica cada uma em `real`, `inventada` ou `incompleta`, gerando o `submission.csv` e a nota
oficial. Na amostra dá `score_final ≈ 0,99` (ver `docs/analise_erros_baseline.md`).

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -e ".[dev]"
```

Os dados oficiais ficam em `desafio-jusbrasil-bracis-2026/` (fora do git). Sem
essa pasta, `indexar` / `rodar` / `avaliar` não rodam.

## Comandos

```bash
python -m verificador ambiente
python -m verificador indexar --dados desafio-jusbrasil-bracis-2026
python -m verificador rodar --entrada desafio-jusbrasil-bracis-2026/txt --run smoke
python -m verificador avaliar --run smoke
python -m verificador submeter --run smoke                 # confere árvore limpa e R49; --criar-tag cria a tag
python -m verificador comparar --run antes --run depois     # diferença de nota e de citações entre duas execuções
python -m verificador gerar-sintetico --dados desafio-jusbrasil-bracis-2026 --saida sintetico/ --pares 100
python -m verificador avaliar --run x --conjunto controle   # amostra | ajuste | controle | sintetico
python -m verificador calibrar --run base --run-sintetico sint --gabarito-sintetico sintetico/goldenset_offsets.csv
```

CLI em `argparse` (`python -m verificador` ou o script `verificador` após o install).
Configuração em `verificador.toml` (hash no manifesto).

A nota na amostra é alta por ser a mesma amostra do leaderboard de treino: quem informa
generalização é o conjunto sintético e o controle (ADR-009).

```bash
pytest
```

## Docker

O `Dockerfile` parte de `gcr.io/kaggle-gpu-images/python:v170` (a mesma família
de imagem dos notebooks do Kaggle; ADR-014). **Não foi testado `docker build`
neste repositório**: a imagem GPU do Kaggle tem vários GB e não é o ambiente do
dia a dia. A reprodução das submissões é o notebook em `notebooks/kaggle/`.

## Notebook Kaggle

`notebooks/kaggle/00_esqueleto.ipynb` clona o repositório e chama a CLI. A
configuração da conta (token GitHub, GPU, Input) está em `docs/guia_kaggle.md`
e pode ser feita depois.
