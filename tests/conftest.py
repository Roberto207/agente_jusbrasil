from __future__ import annotations

import csv
import os
from pathlib import Path

import pytest

# A suíte testa o pipeline só com regex: o `verificador.toml` liga o encoder (25/09), mas carregá-lo
# baixaria o modelo em cada teste de pipeline e exigiria torch. Os testes do encoder usam um encoder
# falso (`test_encoder_portas.py`). Para rodar a suíte com o encoder de verdade:
# `VERIFICADOR_USAR_ENCODER=1 pytest`.
os.environ.setdefault("VERIFICADOR_USAR_ENCODER", "0")

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "desafio-jusbrasil-bracis-2026"
GABARITO = DADOS / "goldenset_offsets.csv"
TXT = DADOS / "txt"


@pytest.fixture(scope="session")
def pasta_dados() -> Path:
    if not GABARITO.is_file():
        pytest.skip("goldenset_offsets.csv ausente")
    return DADOS


@pytest.fixture(scope="session")
def textos(pasta_dados: Path) -> dict[str, str]:
    pasta = pasta_dados / "txt"
    if not pasta.is_dir():
        pytest.skip("pasta txt/ ausente")
    lidos: dict[str, str] = {}
    for caminho in sorted(pasta.glob("*.txt")):
        lidos[caminho.stem] = caminho.read_text(encoding="utf-8")
    return lidos


@pytest.fixture(scope="session")
def gabarito(pasta_dados: Path) -> list[dict[str, str]]:
    with (pasta_dados / "goldenset_offsets.csv").open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))
