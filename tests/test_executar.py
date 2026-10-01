"""Ponto de entrada único (`run.sh` → `verificador executar`): caminhos livres e CSV igual ao do oficial."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from verificador.cli import CONVERSOR_OFICIAL, cmd_executar, cmd_rodar

# sha256 do `json_to_submission.py` distribuído com a amostra (R16: usado sem modificação).
SHA256_CONVERSOR_OFICIAL = "c6ec4963e884c7fc19939816d7398e512cc8f7d60af472fb1a3bd723f1fee05c"


def test_conversor_no_repositorio_e_o_oficial_sem_modificacao() -> None:
    assert hashlib.sha256(CONVERSOR_OFICIAL.read_bytes()).hexdigest() == SHA256_CONVERSOR_OFICIAL


def test_conversor_no_repositorio_igual_ao_da_pasta_de_dados(pasta_dados: Path) -> None:
    assert CONVERSOR_OFICIAL.read_bytes() == (pasta_dados / "json_to_submission.py").read_bytes()


def test_executar_com_nomes_livres_gera_o_mesmo_csv_do_conversor_oficial(pasta_dados: Path, tmp_path: Path) -> None:
    # Base com outro nome e .txt em outra pasta, longe da pasta de dados (como na avaliação final).
    db = tmp_path / "base" / "qualquer_nome.db"
    db.parent.mkdir()
    shutil.copy(pasta_dados / "desafio1_bracis.db", db)
    txts = tmp_path / "documentos"
    shutil.copytree(pasta_dados / "txt", txts)

    nosso = cmd_executar(db=db, pasta_txt=txts, destino=tmp_path / "saida" / "sub.csv", usar_encoder=False)
    # R15 e manifesto: um JSON por documento, guardados ao lado do CSV.
    execucao = tmp_path / "saida" / "sub_artefatos" / "execucao"
    assert len(list((execucao / "jsons").glob("*.json"))) == len(list(txts.glob("*.txt")))
    assert (execucao / "manifesto.json").is_file()
    # Referência: o `rodar` de sempre, com o conversor da pasta de dados.
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


def test_executar_que_falha_nao_deixa_csv(tmp_path: Path) -> None:
    db = tmp_path / "ruim.db"
    db.write_text("isto não é sqlite", encoding="utf-8")
    (tmp_path / "txt").mkdir()
    (tmp_path / "txt" / "a.txt").write_text("texto", encoding="utf-8")
    destino = tmp_path / "s.csv"
    with pytest.raises(SystemExit, match="não foi possível ler a base"):
        cmd_executar(db=db, pasta_txt=tmp_path / "txt", destino=destino, usar_encoder=False)
    assert not destino.exists()
