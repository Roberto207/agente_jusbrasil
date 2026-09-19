"""Leitura de campos por regras. None → fila de difíceis."""

from __future__ import annotations

import re
import unicodedata

from dataclasses import replace

from verificador.contratos import Campos, Candidata
from verificador.tabelas import classes, ocr, resolver_lei, resolver_uf
from verificador.texto.normalizacao import normalizar

_DIGITO = re.compile(r"\d+")
_ANO = re.compile(r"\b(19|20)\d{2}\b")
_TRIBUNAL = re.compile(r"\b(STF|STJ|STM|TSE|TST)\b", re.IGNORECASE)
_UF_CAND = re.compile(
    r"(?:/|-|\()\s*([A-Z]{2})\s*\)?",
    re.IGNORECASE,
)
_RELATOR = re.compile(
    r"(?:relatoria\s+(?:de|dc)|rel\.\s*min\.|sob\s+relatoria\s+(?:de|dc))\s+"
    r"(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_ARTIGO = re.compile(
    r"art(?:igo)?\.?\s*(\d+(?:\.\d+)?)º?",
    re.IGNORECASE,
)
_LEI_IDENT = re.compile(
    r"\bd[oa]s?\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_SUMULA_VINC = re.compile(r"vinculante", re.IGNORECASE)
_TST_TOKEN = re.compile(
    r"\b(ED|EDcl|E|ARR|AgARR|AgR|AgRg|AgInt|RR|Ag)\b",
    re.IGNORECASE,
)


def _sem_acento(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def normalizar_relator(nome: str) -> str:
    texto = _sem_acento(nome)
    texto = re.sub(r"\bmin\.?\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"[^A-Za-z\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip().lower()


def _digitos(texto: str) -> str:
    return "".join(_DIGITO.findall(texto))


def _tem_ocr_no_numero(texto: str) -> bool:
    tabela = ocr()
    for i, ch in enumerate(texto):
        if ch.isalpha() and ch in tabela:
            esq = i > 0 and texto[i - 1].isdigit()
            dir_ = i + 1 < len(texto) and texto[i + 1].isdigit()
            if esq or dir_:
                return True
    return False


def _numero_com_ocr(trecho: str, bruto: str) -> tuple[str | None, bool]:
    saida: list[str] = []
    for ch in bruto:
        if ch.isalpha() and ch in tabela:
            saida.append(tabela[ch])
        elif ch.isdigit():
            saida.append(ch)
    numero = "".join(saida) or _digitos(bruto) or _digitos(trecho)
    if not numero:
        return None, False
    return numero, _tem_ocr_no_numero(trecho) or _tem_ocr_no_numero(bruto)


def _classes_no_texto(texto: str) -> list[str]:
    achadas: list[tuple[int, int, str]] = []
    for padrao, sigla in classes():
        for m in re.finditer(rf"(?<![A-Za-z])(?:{padrao})(?![A-Za-z])", texto, re.IGNORECASE):
            achadas.append((m.start(), m.end(), sigla))
    if not achadas:
        return []
    achadas.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    usadas: list[str] = []
    fim_livre = -1
    for ini, fim, sigla in achadas:
        if ini < fim_livre:
            continue
        usadas.append(sigla)
        fim_livre = fim
    return usadas


def _tribunal(texto: str) -> str | None:
    m = _TRIBUNAL.search(texto)
    return m.group(1).upper() if m else None


def _uf(texto: str) -> str | None:
    m = _UF_CAND.search(texto)
    if not m:
        return None
    return resolver_uf(m.group(1))


def _campos_com_numero(trecho: str) -> Campos | None:
    tema = re.search(r"tem[aã]\s+(\d+(?:\.\d+)?)\s+da\s+repercuss", trecho, re.I)
    if tema:
        numero, ocr_ok = _numero_com_ocr(trecho, tema.group(1))
        if not numero:
            return None
        return Campos(
            tribunal=None,
            classe_principal=None,
            cadeia_recursos=(),
            numero=numero,
            uf=None,
            ano=None,
            relator=None,
            lei_chave=None,
            artigo=None,
            correcao_ocr=ocr_ok,
            fonte="regras",
        )

    tst = re.search(
        r"(?:processo\s+nº\s+)?(?:TST-)?((?:(?:ED|EDcl|E|ARR|AgARR|AgR|RR|Ag)-)+)([\d.\-]+)",
        trecho,
        re.I,
    )
    if tst and re.search(r"\d{4}\.\d\.\d{2}\.\d{4}", tst.group(2)):
        tokens = [t.upper() for t in _TST_TOKEN.findall(tst.group(1))]
        mapa = {"ED": "EDcl", "AGR": "AgRg", "AG": "AgRg"}
        tokens = [mapa.get(t, t) for t in tokens]
        numero, ocr_ok = _numero_com_ocr(trecho, tst.group(2))
        if not numero:
            return None
        principal = tokens[-1] if tokens else "RR"
        cadeia = tuple(tokens[:-1]) if len(tokens) > 1 else ()
        return Campos(
            tribunal="TST",
            classe_principal=principal,
            cadeia_recursos=cadeia,
            numero=numero,
            uf=_uf(trecho),
            ano=None,
            relator=None,
            lei_chave=None,
            artigo=None,
            correcao_ocr=ocr_ok,
            fonte="regras",
        )

    siglas = _classes_no_texto(trecho)
    if not siglas:
        return None
    m_num = re.search(
        r"n[oº°.]?\s*(\d+(?:[.\-]\d+)*)|(\d+(?:[.\-]\d+)*)",
        trecho,
        re.I,
    )
    bruto = (m_num.group(1) or m_num.group(2) or "") if m_num else ""
    numero, ocr_ok = _numero_com_ocr(trecho, bruto)
    if not numero:
        return None
    principal = siglas[-1]
    cadeia = tuple(siglas[:-1])
    return Campos(
        tribunal=_tribunal(trecho),
        classe_principal=principal,
        cadeia_recursos=cadeia,
        numero=numero,
        uf=_uf(trecho),
        ano=None,
        relator=None,
        lei_chave=None,
        artigo=None,
        correcao_ocr=ocr_ok,
        fonte="regras",
    )


def _campos_sumula(trecho: str) -> Campos | None:
    m = re.search(r"(\d+)", trecho)
    if not m:
        return None
    vinc = bool(_SUMULA_VINC.search(trecho))
    numero = f"SV{m.group(1)}" if vinc else f"S{m.group(1)}"
    return Campos(
        tribunal=_tribunal(trecho),
        classe_principal=None,
        cadeia_recursos=(),
        numero=numero,
        uf=None,
        ano=None,
        relator=None,
        lei_chave=None,
        artigo=None,
        correcao_ocr=False,
        fonte="regras",
    )


def _campos_lei(trecho: str) -> Campos | None:
    art = _ARTIGO.search(trecho)
    if not art:
        return None
    artigo = art.group(1)
    if artigo.endswith("."):
        artigo = artigo[:-1]
    artigo = artigo.lstrip("0") or "0"
    if "." in artigo:
        artigo = artigo.replace(".", "")
    lei_m = _LEI_IDENT.search(trecho)
    identificador = lei_m.group(1).strip() if lei_m else ""
    lei_chave = resolver_lei(identificador) if identificador else None
    return Campos(
        tribunal=None,
        classe_principal=None,
        cadeia_recursos=(),
        numero=None,
        uf=None,
        ano=None,
        relator=None,
        lei_chave=lei_chave,
        artigo=artigo,
        correcao_ocr=False,
        fonte="regras",
    )


def _campos_sem_numero(trecho: str) -> Campos | None:
    ano_m = _ANO.search(trecho)
    rel_m = _RELATOR.search(trecho)
    if not ano_m or not rel_m:
        return None
    relator = normalizar_relator(rel_m.group(1))
    if not relator:
        return None
    siglas = _classes_no_texto(trecho)
    tribunal = _tribunal(trecho)
    if not tribunal and not siglas:
        return None
    return Campos(
        tribunal=tribunal,
        classe_principal=siglas[-1] if siglas else None,
        cadeia_recursos=tuple(siglas[:-1]) if len(siglas) > 1 else (),
        numero=None,
        uf=None,
        ano=int(ano_m.group(0)),
        relator=relator,
        lei_chave=None,
        artigo=None,
        correcao_ocr=False,
        fonte="regras",
    )


def ler_campos(c: Candidata) -> Campos | None:
    norm, _ = normalizar(c.trecho)
    if c.forma == "com_numero":
        campos = _campos_com_numero(norm)
        if campos is not None:
            return replace(campos, correcao_ocr=_tem_ocr_no_numero(c.trecho))
        return None
    if c.forma == "sumula":
        return _campos_sumula(norm)
    if c.forma == "lei_artigo":
        return _campos_lei(norm)
    if c.forma == "sem_numero":
        return _campos_sem_numero(norm)
    return None
