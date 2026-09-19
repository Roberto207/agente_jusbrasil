"""Frente B2 — extração das quatro formas e leitura de campos.

Débito consciente (não extraído): artigo sem lei, súmula sem número,
citações no plural (`arts. 489 e 1.022`) e referência vaga (ADR-005).
"""

from __future__ import annotations

from verificador.configuracao import carregar
from verificador.contratos import Candidata, TextoPreparado
from verificador.extracao.campos import ler_campos
from verificador.extracao.padroes import COM_NUMERO, LEI_ARTIGO, SEM_NUMERO, SUMULA
from verificador.extracao.sobreposicao import resolver
from verificador.texto import inicio_corpo_normalizado, voltar_ao_original

_FORMAS = (
    (COM_NUMERO, "com_numero", "jurisprudencia", "com_numero"),
    (SUMULA, "sumula", "jurisprudencia", "sumula"),
    (LEI_ARTIGO, "lei_artigo", "lei", "lei_artigo"),
    (SEM_NUMERO, "sem_numero", "jurisprudencia", "sem_numero"),
)


def _candidata(
    t: TextoPreparado,
    ini_norm: int,
    fim_norm: int,
    forma: str,
    tipo: str,
    padrao: str,
) -> Candidata | None:
    inicio, fim = voltar_ao_original(t, ini_norm, fim_norm)
    if inicio < t.corpo_inicio:
        return None
    if inicio >= fim or fim > len(t.original):
        return None
    return Candidata(
        inicio=inicio,
        fim=fim,
        trecho=t.original[inicio:fim],
        tipo=tipo,  # type: ignore[arg-type]
        forma=forma,  # type: ignore[arg-type]
        padrao=padrao,
        origem=frozenset({"regex"}),
    )


def extrair(t: TextoPreparado, encoder=None) -> list[Candidata]:
    del encoder  # Fase 4: união com NER; hoje só regex.
    cfg = carregar()
    del cfg  # extrair_referencia_vaga fica desligada (ADR-005)
    corpo = inicio_corpo_normalizado(t)
    faixa = t.normalizado[corpo:]
    cruas: list[Candidata] = []
    for padrao, forma, tipo, nome in _FORMAS:
        for m in padrao.finditer(faixa):
            cand = _candidata(
                t,
                corpo + m.start(),
                corpo + m.end(),
                forma,
                tipo,
                nome,
            )
            if cand is not None:
                cruas.append(cand)
    return resolver(cruas)


__all__ = ["extrair", "ler_campos"]
