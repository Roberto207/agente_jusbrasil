"""Frente B2 — extração das quatro formas e leitura de campos.

Débito consciente (não extraído): artigo sem lei, súmula sem número, e
artigos no plural (`arts. 489 e 1.022`). Súmulas no plural (`Súmulas 219 e 329
do TST`) saem como um span só, com o primeiro número. Referência vaga tem forma própria
(ADR-005), mas fica atrás da flag `extrair_referencia_vaga` (desligada por
padrão) — ver docs/gerais/conformidade_dados_externos.md.
"""

from __future__ import annotations

from verificador.configuracao import carregar
from verificador.contratos import Candidata, TextoPreparado
from verificador.extracao.campos import ler_campos
from verificador.extracao.encoder import candidatas_do_encoder
from verificador.extracao.padroes import COM_NUMERO, LEI_ARTIGO, REFERENCIA_VAGA, SEM_NUMERO, SUMULA
from verificador.extracao.sobreposicao import resolver
from verificador.texto import inicio_corpo_normalizado, voltar_ao_original

_FORMAS = (
    (COM_NUMERO, "com_numero", "jurisprudencia", "com_numero"),
    (SUMULA, "sumula", "jurisprudencia", "sumula"),
    (LEI_ARTIGO, "lei_artigo", "lei", "lei_artigo"),
    (SEM_NUMERO, "sem_numero", "jurisprudencia", "sem_numero"),
)
_FORMA_REFERENCIA_VAGA = (REFERENCIA_VAGA, "referencia_vaga", "jurisprudencia", "referencia_vaga")


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
    """Candidatas do regex e, com `encoder`, as que só ele acha (ADR-011: união, nunca troca)."""
    cfg = carregar()
    formas = _FORMAS + (_FORMA_REFERENCIA_VAGA,) if cfg.extrair_referencia_vaga else _FORMAS
    corpo = inicio_corpo_normalizado(t)
    faixa = t.normalizado[corpo:]
    cruas: list[Candidata] = []
    for padrao, forma, tipo, nome in formas:
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
    regex = resolver(cruas)
    if encoder is None:
        return regex
    extras = candidatas_do_encoder(t, encoder.spans(t.original), regex)
    return sorted(regex + extras, key=lambda c: (c.inicio, c.fim))


__all__ = ["extrair", "ler_campos"]
