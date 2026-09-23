"""Regex das quatro formas de citação (+ referência vaga, opcional, ADR-005), sobre o corpo normalizado."""

from __future__ import annotations

import re

from verificador.tabelas import classes, frases_referencia_vaga, padrao_ufs, tst_tokens

_FLAGS = re.IGNORECASE
_CONECTOR = r"(?:no|na|nos|nas|-)"
_ORDINAL = r"(?:primeiro|segundo|terceiro|quarto)\s+"
_PROCESSO = r"(?:processo\s+n[oº°.]?\s+)?"
_N = r"(?:n[oº°.]?\s*)?"
# Marcador obrigatório: a normalização já reduz `n.`/`n°`/`No` a `nº` antes de um número.
_N_EXPLICITO = "nº\\s*"
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

# \u00c2ncoras da forma (d) \u2014 ADR-015. O vocabul\u00e1rio sai das 31 cita\u00e7\u00f5es `incompleta` da amostra oficial.
# `entendimento` foi testado e **rejeitado**: nas 31 cita\u00e7\u00f5es reais da amostra o gatilho nunca \u00e9 essa
# palavra, e admiti-la estendia o span \u00e0 esquerda em `gen_n1_007`
# (`Rcl de 2025, Rel. Min. C\u00c1RMEN L\u00daCIA` virava `entendimento a Rcl de 2025, \u2026`). O molde de estresse
# que a usa continua no gerador como falha conhecida \u2014 ver `specs/forma_d_ancorada.md`.
_GATILHO_D = r"(?:julgad[oa]|precedente|ac[o\u00f3]rd[a\u00e3]o|decis[a\u00e3]o|aresto)"
# Alternativas longas primeiro: senão `Min\.?` casaria só o começo de `Ministro`.
# Público porque `campos.py` usa o mesmo marcador: se as duas listas divergirem, a citação é extraída
# mas o relator não é lido, e o caminho de decisão cai em `campos_nao_lidos`.
MARCADOR_RELATOR = r"(?:Ministr[oa]|relatori[ao]|relatad[oa]|relator[ae]?|Rel\.?|Min\.?)"
_ANO_D = r"(?:19|20)\d{2}"
# Preenchimento entre \u00e2ncoras: sem d\u00edgito (impede o span de engolir n\u00famero de processo \u2014 a resolu\u00e7\u00e3o
# de sobreposi\u00e7\u00e3o n\u00e3o protege disso, porque o candidato maior substitui o menor) e sem atravessar
# fim de frase. Nenhuma conjun\u00e7\u00e3o literal entra aqui: \u00e9 o que impede o padr\u00e3o de decorar molde.
_ENCHE = r"(?:(?!\.\s+(?-i:[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00c2\u00ca\u00d4\u00c3\u00d5\u00c7]))[^;\d\n])"


def _padrao_classe() -> str:
    partes = []
    for bruto, _sigla in classes():
        partes.append(re.sub(r"\s+", r"\\s+", bruto))
    return r"(?<![A-Za-z])(?:" + "|".join(f"(?:{p})" for p in partes) + r")(?![A-Za-z])"


def _padrao_uf() -> str:
    ufs = padrao_ufs()
    return rf"(?:/\s*(?:{ufs})|-\s*(?:{ufs})|\(\s*(?:{ufs})\s*\))"


_NUMERO_CNJ = (
    r"(?:"
    r"\d{1,7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
    r"|\d{7}-\d{8,20}"
    r")"
)


def _padrao_tst() -> str:
    """Número do TST: `[TST-]<recurso>-…-<classe>-<CNJ>`.

    Com o prefixo `TST-` qualquer sequência de siglas serve (classes que a tabela ainda
    não conhece); sem ele só vale sigla conhecida, para `PJe-…` ou `TJSP-…` não virarem
    citação. A borda de palavra impede casar `RR-…` no meio de `AIRR-…`.
    """
    conhecidas = "|".join(re.escape(t) for t in tst_tokens())
    com_prefixo = r"TST-(?:[A-Za-z]{1,7}-)+"
    sem_prefixo = rf"(?:(?:{conhecidas})-)+"
    return (
        rf"{_PROCESSO}(?<![A-Za-z])(?P<cadeia_tst>{com_prefixo}|{sem_prefixo})"
        rf"(?P<numero_tst>{_NUMERO_CNJ})"
    )


def _compilar_com_numero() -> re.Pattern[str]:
    classe = _padrao_classe()
    cadeia = rf"(?:{classe}\s*{_CONECTOR}\s*)*"
    uf = _padrao_uf()
    # O hífen só vale como conector quando o que vem depois é número CNJ (`DCG-1340-57.2017.5.17.0010`):
    # é formato distintivo o bastante para não capturar por engano. Classes do TST já entram pelo `tst_bloco`.
    # Número curto (`CautInom nº 87`) exige o marcador `nº` explícito — sem ele, `AC 50` viraria citação.
    comum = (
        rf"(?:{_ORDINAL})?{_PROCESSO}(?P<cadeia>{cadeia})(?P<classe>{classe})"
        rf"(?:\s*{_N}(?P<numero>{_NUMERO})"
        rf"|-(?P<numero_hifen>{_NUMERO_CNJ})"
        rf"|\s*{_N_EXPLICITO}(?P<numero_curto>\d{{1,3}})(?!\d))"
        rf"(?:\s*(?P<uf>{uf}))?"
    )
    tema = (
        r"[Tt]em[aã]\s+(?P<numero_tema>\d+(?:\.\d+)?)\s+da\s+repercuss[aã]o\s+geral"
    )
    return re.compile(
        rf"(?:(?P<tema>{tema})|(?P<tst_bloco>{_padrao_tst()})|(?P<comum>{comum}))", _FLAGS
    )


def _compilar_sumula() -> re.Pattern[str]:
    return re.compile(
        rf"(?:S[úu]mula\s+Vinculante|S[ÚU]MULA\s+VINCULANTE)\s*{_N}(?P<numero_sv>\d+)"
        rf"|(?:S[úu]mula|S[ÚU]MULA|S[úu]m\.)\s*{_N}(?P<numero>\d+)"
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
    # `_FLAGS` tem IGNORECASE, que faria `[A-Z…]` casar minúscula: sem `(?-i:…)` o nome pode começar
    # no meio de uma palavra (em `Rel. Min. Celso`, o span parava com o nome valendo `n`).
    inicial = r"(?-i:[A-ZÁÉÍÓÚÂÊÔÃÕÇ])"
    resto = r"[A-Za-záéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]*"
    nome = (
        rf"{inicial}{resto}"
        rf"(?:\s+(?:d[aeo]s?|e|dc)\s+{inicial}{resto})*"
        rf"(?:\s+{inicial}{resto}){{0,4}}"
    )
    # ADR-015: âncoras, não conjunções. O padrão anterior transcrevia as quatro ligações da amostra
    # (`proferido em … pela relatoria de`, `sob relatoria de`, `Rel. Min.`) e cegava quando a frase
    # mudava. Aqui só entram as peças que toda citação da forma (d) tem — gatilho, tribunal, ano,
    # marcador de relator, nome — e o que as liga é preenchimento genérico.
    # Sem grupos nomeados: as duas ordens abaixo repetiriam os mesmos nomes, e ninguém os consome —
    # `extrair` usa só o span e `ler_campos` reanalisa o trecho.
    cabeca = (
        rf"(?:{_GATILHO_D}|{classe})"
        rf"{_ENCHE}{{0,25}}"
        rf"(?:{_TRIBUNAL}{_ENCHE}{{0,25}})?"
    )
    # O marcador repete porque `Rel. Min.` são dois: sem isso o `Min` vira o nome e o span para
    # antes do relator.
    relator = rf"(?:{MARCADOR_RELATOR}{_ENCHE}{{0,7}}){{1,3}}{nome}"

    # Duas ordens, porque as duas existem na escrita jurídica: ano antes do relator (`… de 2020,
    # Rel. Min. X`) e relator antes do ano, no formato parentético (`… (Rel. Min. X, 2020)`).
    # É variação de ordem **entre âncoras**, não conjunção literal — a regra do ADR-015 continua de pé.
    ano_primeiro = rf"{cabeca}{_ANO_D}{_ENCHE}{{0,25}}{relator}"
    relator_primeiro = rf"{cabeca}{relator}{_ENCHE}{{0,15}}{_ANO_D}"
    return re.compile(rf"(?:{ano_primeiro}|{relator_primeiro})", _FLAGS)


def _compilar_referencia_vaga() -> re.Pattern[str]:
    """ADR-005, atrás de `extrair_referencia_vaga` (desligada por padrão) — vocabulário fechado
    em `tabelas/referencia_vaga.json`, mesmo princípio de âncora do `_padrao_classe()` acima."""
    partes = [re.sub(r"\s+", r"\\s+", frase) for frase in frases_referencia_vaga()]
    return re.compile(r"(?:" + "|".join(f"(?:{p})" for p in partes) + r")", _FLAGS)


COM_NUMERO = _compilar_com_numero()
TST_NUMERO = re.compile(_padrao_tst(), _FLAGS)
SUMULA = _compilar_sumula()
LEI_ARTIGO = _compilar_lei()
SEM_NUMERO = _compilar_sem_numero()
REFERENCIA_VAGA = _compilar_referencia_vaga()
