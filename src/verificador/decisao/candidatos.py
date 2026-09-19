"""Etapa 1 da decisão: quais registros da base a citação pode estar apontando (DESIGN [4])."""

from __future__ import annotations

import re

from verificador.base.indice import Indice
from verificador.contratos import Campos, RegistroIndice

_SUMULA = re.compile(r"(SV|S)(\d+)")


def normalizar_sumula(numero: str) -> str:
    """`S083` → `S83`, `SV010` → `SV10`: o índice guarda o número da súmula sem zeros à esquerda."""
    m = _SUMULA.fullmatch(numero)
    return f"{m.group(1)}{int(m.group(2))}" if m else numero


def buscar_candidatos(campos: Campos, forma: str, indice: Indice) -> list[RegistroIndice]:
    """Registros com o mesmo número (formas a e b) ou a mesma lei e artigo (forma c).

    Forma (a) sem classe processual não consulta nada: é o caso do "Tema N da repercussão geral",
    que a base não tem e cujo número não pode casar por acaso com um processo de número curto.
    """
    if forma == "com_numero":
        if not campos.numero or campos.classe_principal is None:
            return []
        return indice.por_numero(campos.numero)
    if forma == "sumula":
        return indice.por_numero(normalizar_sumula(campos.numero)) if campos.numero else []
    if forma == "lei_artigo":
        if not campos.lei_chave or not campos.artigo:
            return []
        return indice.por_lei_artigo(campos.lei_chave, campos.artigo)
    return []
