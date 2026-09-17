# Verificador de citações — Jusbrasil × BRACIS 2026

Esqueleto andante: o pipeline já vai dos `.txt` até o `submission.csv` e a nota
oficial, mas **ainda não extrai citações** (cada documento sai com lista vazia).
Serve para travar o formato de entrega antes da lógica das frentes A–D.

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
python -m verificador submeter --run smoke
```

CLI em `argparse` (`python -m verificador` ou o script `verificador` após o install).
Configuração em `verificador.toml` (hash no manifesto).

O `score_final` desta etapa fica perto de 0 — não há citação nenhuma. O teste é
o cálculo funcionar, não a nota.

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
