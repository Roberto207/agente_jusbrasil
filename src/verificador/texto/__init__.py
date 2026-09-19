"""Frente B1 — cabeçalho, normalização e mapa de offsets."""

from __future__ import annotations

from verificador.contratos import TextoPreparado
from verificador.texto.cabecalho import delimitar_cabecalho
from verificador.texto.normalizacao import normalizar, voltar_ao_original as _voltar


def preparar(texto: str) -> TextoPreparado:
    original = texto if texto is not None else ""
    corpo_inicio = delimitar_cabecalho(original)
    normalizado, mapa = normalizar(original)
    return TextoPreparado(
        original=original,
        corpo_inicio=corpo_inicio,
        normalizado=normalizado,
        mapa=mapa,
    )


def voltar_ao_original(
    t: TextoPreparado,
    ini_norm: int,
    fim_norm: int,
) -> tuple[int, int]:
    return _voltar(t.original, t.mapa, ini_norm, fim_norm)


def inicio_corpo_normalizado(t: TextoPreparado) -> int:
    for i, orig in enumerate(t.mapa):
        if orig >= t.corpo_inicio:
            return i
    return len(t.mapa)


__all__ = [
    "preparar",
    "voltar_ao_original",
    "inicio_corpo_normalizado",
    "delimitar_cabecalho",
    "normalizar",
]
