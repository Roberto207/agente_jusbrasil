"""Smoke test do índice; o pipeline inteiro (rodar → avaliar) está em `test_pipeline.py`."""

from __future__ import annotations

from pathlib import Path

from verificador.cli import cmd_indexar


def test_indexar_le_a_base(pasta_dados: Path) -> None:
    assert cmd_indexar(pasta_dados) == 1014
