"""Divisão fixa da amostra em *ajuste* e *controle* (ADR-009).

Regras só podem ser ajustadas olhando o conjunto de **ajuste**; o **controle** existe
para medir. A divisão é estratificada por nível e fica num arquivo versionado
(`divisao.json`): nunca se sorteia de novo depois de decidida, senão o controle
contamina. O arquivo é dado, não código (R43 vale para o código-fonte).
"""

from __future__ import annotations

import csv
import json
import random
from functools import lru_cache
from importlib import resources
from pathlib import Path

CONJUNTOS = ("amostra", "ajuste", "controle")
CONTROLE_POR_NIVEL = 6
SEMENTE = 0


def gerar_divisao(
    gabarito: Path,
    semente: int = SEMENTE,
    controle_por_nivel: int = CONTROLE_POR_NIVEL,
) -> dict[str, object]:
    """Sorteia a divisão a partir do gabarito. Usada uma vez; o resultado é versionado."""
    niveis: dict[int, set[str]] = {}
    with gabarito.open(encoding="utf-8-sig", newline="") as fh:
        for linha in csv.DictReader(fh):
            niveis.setdefault(int(linha["nivel"]), set()).add(linha["documento_id"])

    rng = random.Random(semente)
    ajuste: list[str] = []
    controle: list[str] = []
    for nivel in sorted(niveis):
        ids = sorted(niveis[nivel])
        rng.shuffle(ids)
        controle.extend(ids[:controle_por_nivel])
        ajuste.extend(ids[controle_por_nivel:])
    return {"semente": semente, "ajuste": sorted(ajuste), "controle": sorted(controle)}


@lru_cache(maxsize=1)
def carregar_divisao() -> dict[str, object]:
    caminho = Path(str(resources.files("verificador.avaliacao"))) / "divisao.json"
    return json.loads(caminho.read_text(encoding="utf-8"))


def conjuntos_disponiveis(gabarito: Path) -> tuple[str, ...]:
    """A divisão ajuste/controle vale só para a amostra oficial; outro gabarito é um conjunto único.

    Decide pelos documentos do gabarito, não pelo nome do arquivo (o sintético usa o mesmo nome).
    Um `divisao.json` ao lado do gabarito sintético acrescenta o treino e o controle dele (ADR-009).
    """
    with gabarito.open(encoding="utf-8-sig", newline="") as fh:
        ids = {linha["documento_id"] for linha in csv.DictReader(fh)}
    if ids == set(documentos("amostra")):
        return ("amostra", "ajuste", "controle")
    if (gabarito.parent / "divisao.json").is_file():
        return ("sintetico", "sintetico_treino", "sintetico_controle")
    return ("sintetico",)


def documentos_do_conjunto(nome: str, gabarito: Path) -> set[str] | None:
    """Documentos de um conjunto da amostra ou do sintético; `None` = o gabarito inteiro."""
    if nome == "sintetico":
        return None
    if nome in ("sintetico_treino", "sintetico_controle"):
        dados = json.loads((gabarito.parent / "divisao.json").read_text(encoding="utf-8"))
        return set(dados[nome.removeprefix("sintetico_")])
    return set(documentos(nome))


def documentos(conjunto: str) -> frozenset[str]:
    """Documentos de `ajuste`, `controle` ou `amostra` (a união dos dois)."""
    if conjunto not in CONJUNTOS:
        raise ValueError(f"conjunto {conjunto!r} desconhecido; use {CONJUNTOS}")
    divisao = carregar_divisao()
    if conjunto == "amostra":
        return frozenset(divisao["ajuste"]) | frozenset(divisao["controle"])  # type: ignore[arg-type]
    return frozenset(divisao[conjunto])  # type: ignore[arg-type]
