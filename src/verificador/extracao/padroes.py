"""Regex das quatro formas de citação, sobre o corpo normalizado."""

from __future__ import annotations

import re

from verificador.tabelas import classes, padrao_ufs

_FLAGS = re.IGNORECASE
_CONECTOR = r"(?:no|na|nos|nas|-)"
_ORDINAL = r"(?:primeiro|segundo|terceiro|quarto)\s+"
_PROCESSO = r"(?:processo\s+n[oº°.]?\s+)?"
_N = r"(?:n[oº°.]?\s*)?"
_NUMERO = (
    r"(?:"
    r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
    r"|\d{1,7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
    r"|\d{7}-\d{8,20}"
    r"|\d{1,3}(?:\.\d{3}){1,4}"
    r"|\d{4,22}"
    r")"
)
_TRIBUNAL = r"(?:STF|STJ|STM|TSE|TST)"
_GRAU = "\u00ba"


def _padrao_classe() -> str:
    partes = []
    for bruto, _sigla in classes():
        partes.append(re.sub(r"\s+", r"\\s+", bruto))
    return r"(?<![A-Za-z])(?:" + "|".join(f"(?:{p})" for p in partes) + r")(?![A-Za-z])"


def _padrao_uf() -> str:
    ufs = padrao_ufs()
    return rf"(?:/\s*(?:{ufs})|-\s*(?:{ufs})|\(\s*(?:{ufs})\s*\))"


def _compilar_com_numero() -> re.Pattern[str]:
    classe = _padrao_classe()
    cadeia = rf"(?:{classe}\s*{_CONECTOR}\s*)*"
    uf = _padrao_uf()
    comum = (
        rf"(?:{_ORDINAL})?{_PROCESSO}(?P<cadeia>{cadeia})(?P<classe>{classe})"
        rf"\s*{_N}(?P<numero>{_NUMERO})(?:\s*(?P<uf>{uf}))?"
    )
    tst = (
        rf"{_PROCESSO}(?P<tst>TST-)?"
        rf"(?P<cadeia_tst>(?:(?:ED|EDcl|E|ARR|AgARR|AgR|RR|Ag)-)+)"
        rf"(?P<numero_tst>{_NUMERO})"
    )
    tema = (
        r"[Tt]em[aã]\s+(?P<numero_tema>\d+(?:\.\d+)?)\s+da\s+repercuss[aã]o\s+geral"
    )
    return re.compile(rf"(?:(?P<tema>{tema})|(?P<tst_bloco>{tst})|(?P<comum>{comum}))", _FLAGS)


def _compilar_sumula() -> re.Pattern[str]:
    return re.compile(
        rf"(?:S[úu]mula\s+Vinculante|S[ÚU]MULA\s+VINCULANTE)\s*(?P<numero_sv>\d+)"
        rf"|(?:S[úu]mula|S[ÚU]MULA|S[úu]m\.)\s*(?P<numero>\d+)"
        rf"(?:\s+do\s+(?P<tribunal>{_TRIBUNAL}))?",
        _FLAGS,
    )


def _compilar_lei() -> re.Pattern[str]:
    complemento = (
        r"(?:\s*,\s*(?:"
        rf"\u00a7\s*[\d{_GRAU}\-Aª]+"
        r"|inciso\s+[IVXLC]+"
        r"|[IVXLC]{1,6}"
        r"|['\"“”][a-z]['\"“”]"
        r"))*"
    )
    lei = (
        r"(?:"
        r"constitui[cç][aã]o(?:\s+fed[ce]ral|\s+da\s+rep[uú]blica(?:\s+federativa)?)?"
        r"|consolida[cç][aã]o\s+das\s+leis\s+do\s+trabalho"
        r"|c[oó]digo\s+de\s+defesa\s+do\s+consumidor"
        r"|c[oó]digo\s+de\s+processo\s+civil"
        r"|c[oó]digo\s+de\s+processo\s+penal"
        r"|c[oó]digo\s+penal\s+militar"
        r"|c[oó]digo\s+eleitoral"
        r"|c[oó]digo\s+civil"
        rf"|lei\s+complementar\s+n[{_GRAU}o.]?\s*\d+(?:\.\d+)*\s*/\s*\d{{4}}"
        rf"|lei\s+n[{_GRAU}o.]?\s*\d+(?:\.\d+)*\s*/\s*\d{{4}}"
        r"|CLT|CPC|CDC|CPP|CPM|CC\b"
        r")"
    )
    return re.compile(
        rf"(?P<rotulo>art(?:igo)?\.?)\s*(?P<artigo>\d+(?:\.\d+)?){_GRAU}?"
        rf"{complemento}\s*,?\s+d[oa]s?\s+(?P<lei>{lei})",
        _FLAGS,
    )


def _compilar_sem_numero() -> re.Pattern[str]:
    classe = _padrao_classe()
    nome = (
        r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]*"
        r"(?:\s+(?:d[aeo]s?|e|dc)\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]*)*"
        r"(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]*){0,4}"
    )
    julgado = (
        rf"(?P<tipo_j>julgado|precedente|ac[oó]rd[aã]o)\s+do\s+(?P<tribunal_j>{_TRIBUNAL})\s+"
        rf"(?:prof[ce]rido\s+em\s+(?P<ano_j1>\d{{4}})\s+pela\s+relatoria\s+(?:de|dc)\s+"
        rf"|(?:de|julgado\s+em)\s+(?P<ano_j2>\d{{4}}),?\s+"
        rf"(?:da\s+relatoria\s+(?:de|dc)|sob\s+relatoria\s+(?:de|dc))\s+)"
        rf"(?P<relator_j>{nome})"
    )
    classe_ano = (
        rf"(?P<classe_d>{classe})(?:\s+do\s+(?P<tribunal_d>{_TRIBUNAL}))?"
        rf"\s*,?\s*de\s+(?P<ano_d>\d{{4}})\s*,?\s+"
        rf"Rel\.?\s*Min\.?\s+(?P<relator_d>{nome})"
    )
    return re.compile(rf"(?:{julgado}|{classe_ano})", _FLAGS)


COM_NUMERO = _compilar_com_numero()
SUMULA = _compilar_sumula()
LEI_ARTIGO = _compilar_lei()
SEM_NUMERO = _compilar_sem_numero()
