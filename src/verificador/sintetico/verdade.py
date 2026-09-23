"""Verdade do gerador: a classe de uma citação segue as regras do DEFINE sobre a base.

O gerador *escolhe* a citação e *deduz* o gabarito aplicando R6–R9/R40 (+ família de classe) ao
índice, em vez de confiar na intenção com que a fabricou (um número "emprestado" pode, por acaso,
ser consistente com outro registro). Assim o gabarito sintético nunca contradiz a base.

**Por que `consistentes()` abaixo é uma cópia, e não uma chamada a `decisao.caminhos.consistentes`:**
se o gabarito chamasse a própria função de decisão, um bug futuro em `decisao/caminhos.py` seria
"correto" pelo gabarito sintético por construção — a mesma função erraria dos dois lados e nenhum
teste veria divergência. `familias_classe.json` (dado declarativo, sem lógica de decisão) é
compartilhado via `tabelas.mesma_familia_classe`, do mesmo jeito que `ocr.json` já é compartilhado
com o gerador de ruído — só a REGRA de filtro é reimplementada, de propósito, para que o sintético
continue sendo um oráculo independente de `decisao/`. (Achado de revisão de 22/09: a versão anterior
desta função delegava a `decisao.caminhos.consistentes`, o que zerou o poder do sintético de pegar
regressão na etapa de decisão — ver `taxa_acerto.json`, que tinha ido a 100%/Brier=0 em todo
caminho.)
"""

from __future__ import annotations

from collections.abc import Sequence

from verificador.contratos import RegistroIndice
from verificador.tabelas import mesma_familia_classe


def consistentes(
    candidatos: Sequence[RegistroIndice],
    *,
    tribunal: str | None = None,
    uf: str | None = None,
    classe: str | None = None,
    cadeia: Sequence[str] = (),
) -> list[RegistroIndice]:
    """Candidatos que nenhum atributo *explícito* da citação contradiz (ADR-007 + família de classe).

    Atributo ausente (na citação ou no registro) nunca elimina ninguém. Com **2+** candidatos,
    classe e cadeia precisam bater exato (é o desempate). Com **exatamente 1**, classe de outra
    família processual veta (número emprestado); classe de outro *estágio da mesma família*
    (`ARR` vs `AIRR`) não veta, e nesse caso a cadeia diverge junto — é tolerada só ali. Cadeia
    divergente com a mesma classe continua vetando.
    """
    cadeia = tuple(cadeia)
    unico = len(candidatos) == 1
    saida = []
    for r in candidatos:
        if tribunal and r.tribunal and tribunal != r.tribunal:
            continue
        if uf and r.uf and uf != r.uf:
            continue
        classe_bate = not classe or not r.classe_principal or classe == r.classe_principal
        mesmo_estagio = classe == r.classe_principal
        outro_estagio = (
            unico and classe and r.classe_principal and not mesmo_estagio
            and mesma_familia_classe(classe, r.classe_principal)
        )
        if not classe_bate and not outro_estagio:
            continue
        cadeia_bate = not cadeia or cadeia == tuple(r.cadeia_recursos)
        if not cadeia_bate and not outro_estagio:
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
