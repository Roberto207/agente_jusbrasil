"""Smoke test do pipeline: indexar → rodar → avaliar."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from verificador.cli import cmd_avaliar, cmd_indexar, cmd_rodar

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "desafio-jusbrasil-bracis-2026"


@pytest.fixture(scope="module")
def dados() -> Path:
    if not (DADOS / "desafio1_bracis.db").is_file():
        pytest.skip("pasta desafio-jusbrasil-bracis-2026 ausente")
    return DADOS


def test_indexar_le_a_base(dados: Path) -> None:
    assert cmd_indexar(dados) == 1014


def test_pipeline_ate_a_nota(dados: Path, tmp_path: Path) -> None:
    saida = tmp_path / "runs"
    submission = cmd_rodar(
        entrada=dados / "txt",
        run_id="smoke",
        saida=saida,
        dados=dados,
    )
    assert submission.is_file()

    with submission.open(encoding="utf-8", newline="") as fh:
        linhas = list(csv.reader(fh))
    assert linhas[0] == ["documento_id", "citacoes"]
    documentos = linhas[1:]
    assert len(documentos) == 26
    assert all(documento_id for documento_id, _ in documentos)
    assert any(citacoes != "-" for _, citacoes in documentos)

    resultado = cmd_avaliar(
        run_id="smoke",
        saida=saida,
        gabarito=dados / "goldenset_offsets.csv",
        dados=dados,
    )
    assert "score_final" in resultado
    assert resultado["score_final"] > 0.9
    relatorio = saida / "smoke" / "relatorio.md"
    assert relatorio.is_file()
    texto = relatorio.read_text(encoding="utf-8")
    assert "score_final" in texto
    assert (saida / "smoke" / "jsons").is_dir()
    assert len(list((saida / "smoke" / "jsons").glob("*.json"))) == 26
