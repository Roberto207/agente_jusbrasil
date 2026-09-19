"""Delimita o cabeçalho do parecer (R34)."""

from __future__ import annotations

import re
import unicodedata

_ROTULO = re.compile(
    r"""
    ^\s*
    (?:
        processo|autos|protocolo|memorial|of[ií]cio|valor\s+da\s+causa|
        impetrante|paciente|apelante|apelado|agravante|agravado|
        assistido|autoridade|relator|reclamante|reclamada|
        recorrente|recorrido|autor|r[eé]
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_OAB = re.compile(r"\bOAB\s*/", re.IGNORECASE)


def _sem_acento(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _so_maiusculas(linha: str) -> bool:
    letras = [ch for ch in linha if ch.isalpha()]
    if len(letras) < 3:
        return False
    return all(ch.isupper() for ch in letras)


def _linha_de_cabecalho(linha: str) -> bool:
    compacta = linha.strip()
    if not compacta:
        return True
    if _ROTULO.match(compacta):
        return True
    if _OAB.search(compacta):
        return True
    if _so_maiusculas(compacta) and len(compacta) <= 120:
        return True
    if len(compacta) <= 40 and not any(ch.islower() for ch in _sem_acento(compacta)):
        return True
    return False


def delimitar_cabecalho(texto: str) -> int:
    """Índice do primeiro parágrafo corrido; 0 se não houver cabeçalho detectável."""
    if not texto:
        return 0
    pos = 0
    corpo = None
    for linha in texto.splitlines(keepends=True):
        if _linha_de_cabecalho(linha):
            pos += len(linha)
            continue
        corpo = pos
        break
    if corpo is None:
        return len(texto)
    return corpo
