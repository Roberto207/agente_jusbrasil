"""Resolução de sobreposição entre candidatas (R3)."""

from __future__ import annotations

from verificador.contratos import Candidata

_ESPECIFICA = {
    "com_numero": 3,
    "sumula": 2,
    "lei_artigo": 1,
    "sem_numero": 0,
    "referencia_vaga": -1,  # ADR-005: menos informação que qualquer outra forma, inclusive sem_numero
}


def iou(a: Candidata, b: Candidata) -> float:
    inter = max(0, min(a.fim, b.fim) - max(a.inicio, b.inicio))
    if inter == 0:
        return 0.0
    uniao = (a.fim - a.inicio) + (b.fim - b.inicio) - inter
    return inter / uniao if uniao else 0.0


def _contida(interna: Candidata, externa: Candidata) -> bool:
    return interna.inicio >= externa.inicio and interna.fim <= externa.fim and (
        interna.inicio != externa.inicio or interna.fim != externa.fim
    )


def _chave(c: Candidata) -> tuple:
    return (
        _ESPECIFICA.get(c.forma, 0),
        len(c.origem),
        c.fim - c.inicio,
        -c.inicio,
    )


def resolver(candidatas: list[Candidata]) -> list[Candidata]:
    if not candidatas:
        return []
    ordenadas = sorted(candidatas, key=_chave, reverse=True)
    escolhidas: list[Candidata] = []
    for cand in ordenadas:
        if any(_contida(cand, outra) for outra in escolhidas):
            continue
        conflito = False
        substituir: list[Candidata] = []
        for outra in escolhidas:
            if _contida(outra, cand):
                substituir.append(outra)
                continue
            if iou(cand, outra) >= 0.5:
                if _chave(cand) > _chave(outra):
                    substituir.append(outra)
                else:
                    conflito = True
                    break
        if conflito:
            continue
        escolhidas = [o for o in escolhidas if o not in substituir]
        escolhidas.append(cand)
    escolhidas.sort(key=lambda c: (c.inicio, c.fim))
    return escolhidas
