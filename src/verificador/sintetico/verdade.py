"""Verdade do gerador: a classe de uma citação segue as regras do DEFINE sobre a base.

O gerador *escolhe* a citação e *deduz* o gabarito aplicando R6–R9/R40 ao índice, em vez de
confiar na intenção com que a fabricou (um número "emprestado" pode, por acaso, ser consistente
com outro registro). Assim o gabarito sintético nunca contradiz a base.
"""

from __future__ import annotations

from collections.abc import Sequence

from verificador.contratos import RegistroIndice


def consistentes(
    candidatos: Sequence[RegistroIndice],
    *,
    tribunal: str | None = None,
    uf: str | None = None,
    classe: str | None = None,
    cadeia: Sequence[str] = (),
) -> list[RegistroIndice]:
    """Candidatos que nenhum atributo *explícito* da citação contradiz (ADR-007)."""
    saida = []
    for r in candidatos:
        if tribunal and r.tribunal and tribunal != r.tribunal:
            continue
        if uf and r.uf and uf != r.uf:
            continue
        if classe and r.classe_principal and classe != r.classe_principal:
            continue
        if cadeia and tuple(cadeia) != r.cadeia_recursos:
            continue
        saida.append(r)
    return saida


def classificar(
    candidatos: Sequence[RegistroIndice], consistentes_: Sequence[RegistroIndice]
) -> tuple[str, str | None]:
    """(classe, id_canonico): 0 candidatos ou 0 consistentes → inventada; 1 → real; N → incompleta."""
    if not candidatos or not consistentes_:
        return "inventada", None
    if len(consistentes_) == 1:
        return "real", consistentes_[0].id
    return "incompleta", None
