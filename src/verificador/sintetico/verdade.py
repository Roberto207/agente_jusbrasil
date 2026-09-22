"""Verdade do gerador: a classe de uma citação segue as regras do DEFINE sobre a base.

O gerador *escolhe* a citação e *deduz* o gabarito aplicando a mesma `decidir`/`consistentes`
do pipeline, em vez de confiar na intenção com que a fabricou (um número "emprestado" pode, por
acaso, ser consistente com outro registro). Assim o gabarito sintético nunca contradiz a base —
hoje e em gerações futuras.
"""

from __future__ import annotations

from collections.abc import Sequence

from verificador.contratos import Campos, RegistroIndice
from verificador.decisao.caminhos import consistentes as _consistentes_campos


def _campos(
    *,
    tribunal: str | None = None,
    uf: str | None = None,
    classe: str | None = None,
    cadeia: Sequence[str] = (),
) -> Campos:
    return Campos(
        tribunal=tribunal,
        classe_principal=classe,
        cadeia_recursos=tuple(cadeia),
        numero=None,
        uf=uf,
        ano=None,
        relator=None,
        lei_chave=None,
        artigo=None,
        correcao_ocr=False,
        fonte="regras",
    )


def consistentes(
    candidatos: Sequence[RegistroIndice],
    *,
    tribunal: str | None = None,
    uf: str | None = None,
    classe: str | None = None,
    cadeia: Sequence[str] = (),
) -> list[RegistroIndice]:
    """Delega ao filtro da frente D: o ouro sintético não tem regra própria."""
    return _consistentes_campos(_campos(tribunal=tribunal, uf=uf, classe=classe, cadeia=cadeia), candidatos)


def classificar(
    candidatos: Sequence[RegistroIndice], consistentes_: Sequence[RegistroIndice]
) -> tuple[str, str | None]:
    """(classe, id_canonico): 0 candidatos ou 0 consistentes → inventada; 1 → real; N → incompleta."""
    if not candidatos or not consistentes_:
        return "inventada", None
    if len(consistentes_) == 1:
        return "real", consistentes_[0].id
    return "incompleta", None
