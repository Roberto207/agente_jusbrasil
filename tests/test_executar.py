"""Ponto de entrada único (`run.sh` → `verificador executar`): caminhos livres e CSV igual ao do oficial."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from verificador.cli import cmd_executar, cmd_rodar
from verificador.saida.submissao import escrever_submission


def test_executar_com_nomes_livres_gera_o_mesmo_csv_do_conversor_oficial(pasta_dados: Path, tmp_path: Path) -> None:
    # Base com outro nome e .txt em outra pasta, longe da pasta de dados (como na avaliação final).
    db = tmp_path / "base" / "qualquer_nome.db"
    db.parent.mkdir()
    shutil.copy(pasta_dados / "desafio1_bracis.db", db)
    txts = tmp_path / "documentos"
    shutil.copytree(pasta_dados / "txt", txts)

    nosso = cmd_executar(db=db, pasta_txt=txts, destino=tmp_path / "saida" / "sub.csv", usar_encoder=False)
    # Referência: o caminho antigo, que chama o json_to_submission.py oficial.
    oficial = cmd_rodar(
        entrada=pasta_dados / "txt", run_id="ref", saida=tmp_path / "runs", dados=pasta_dados, usar_encoder=False
    )
    assert nosso.read_bytes() == oficial.read_bytes()


def test_executar_recusa_base_ausente(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="base não encontrada"):
        cmd_executar(db=tmp_path / "nao.db", pasta_txt=tmp_path, destino=tmp_path / "s.csv", usar_encoder=False)


def test_executar_recusa_pasta_sem_txt(tmp_path: Path) -> None:
    db = tmp_path / "b.db"
    db.write_bytes(b"")
    with pytest.raises(SystemExit, match="nenhum .txt"):
        cmd_executar(db=db, pasta_txt=tmp_path, destino=tmp_path / "s.csv", usar_encoder=False)


def test_conversor_sem_json_nao_deixa_csv(tmp_path: Path) -> None:
    destino = tmp_path / "s.csv"
    with pytest.raises(FileNotFoundError):
        escrever_submission(tmp_path, destino)
    assert not destino.exists()
