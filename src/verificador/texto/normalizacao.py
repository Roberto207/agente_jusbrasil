"""Cópia normalizada + mapa posição-normalizada → original (ADR-003)."""

from __future__ import annotations

import re
import unicodedata

from verificador.tabelas import ocr

_TRACOS = {
    "\u2010",
    "\u2011",
    "\u2012",
    "\u2013",
    "\u2014",
    "\u2015",
    "\u2212",
}
# O espaço opcional depois do separador mantém `l. 925.456` e `68. l62` como um token só: sem isso a
# letra fica isolada do resto do número e a troca letra→dígito não acontece (causa 4 do recall).
_NUMERO = re.compile(
    r"(?<![\w])(?=[\dIlOSgl.\- ]{0,40}\d)[\dIlOSgl]+(?:[.\-] ?[\dIlOSgl]+)*(?![A-Za-zÀ-ÿ])",
    re.IGNORECASE,
)
_N_NUMERO = re.compile(
    r"(?<![A-Za-zÁ-ú])(?:[nN][º°oO]|[nN]\.)(?=\s*[\dIlOSgl])",
)
_CINCO_UMULA = re.compile(r"5[úu]mula", re.IGNORECASE)
_ESPACO_NO_NUMERO = re.compile(
    r"(?<=\d) +(?=[\d.\-])|(?<=\d\.) +(?=\d)",
)
_SEPARADOR = re.compile(r"([.\- ]+)")
_HIFEN_SOLTO = re.compile(r"\s*-\s*")
_HIFEN_PONTO = re.compile(r"-+\.(?=\d)|\.-+(?=\d)")
_HIFENS_DUPLOS = re.compile(r"-{2,}")


def _e_espaco(ch: str) -> bool:
    return ch in "\n\r\t" or unicodedata.category(ch) == "Zs"


def _aplicar(
    chars: list[str],
    mapa: list[int],
    ini: int,
    fim: int,
    novo: str,
) -> None:
    orig = mapa[ini:fim]
    if not orig:
        return
    if not novo:
        del chars[ini:fim]
        del mapa[ini:fim]
        return
    if len(novo) <= len(orig):
        novo_mapa = orig[: len(novo)]
    else:
        novo_mapa = orig + [orig[-1]] * (len(novo) - len(orig))
    chars[ini:fim] = list(novo)
    mapa[ini:fim] = novo_mapa


def _substituir(
    chars: list[str],
    mapa: list[int],
    padrao: re.Pattern[str],
    reposicao,
) -> None:
    texto = "".join(chars)
    for m in reversed(list(padrao.finditer(texto))):
        novo = reposicao(m) if callable(reposicao) else reposicao
        _aplicar(chars, mapa, m.start(), m.end(), novo)


def _ocr_no_token(token: str) -> str:
    """Troca letra→dígito em token numérico, decidindo por **grupo** entre separadores.

    A regra antiga exigia dígito colado e deixava passar `l.239` (o `l` encosta no ponto). A regra
    pelo token inteiro erra para o outro lado: em `1.111.222-GO` ela transforma a UF em `90`.
    Por grupo, converte quando o grupo já tem dígito (`7I`, `4S5`) ou quando é um caractere só e não
    é o último (`l` em `l.239`, `S` em `...2008.S.19...`). Assim `GO` e um `-S` final ficam de fora.
    """
    if not any(ch.isdigit() for ch in token):
        return token
    tabela = ocr()
    partes = _SEPARADOR.split(token)
    conteudo = [i for i in range(0, len(partes), 2) if partes[i]]
    if not conteudo:
        return token
    ultimo = conteudo[-1]
    for i in conteudo:
        grupo = partes[i]
        tem_digito = any(ch.isdigit() for ch in grupo)
        if tem_digito or (len(grupo) == 1 and i != ultimo):
            partes[i] = "".join(tabela.get(c, c) if c.isalpha() else c for c in grupo)
    return "".join(partes)


def normalizar(texto: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    mapa: list[int] = []
    for i, ch in enumerate(texto):
        if _e_espaco(ch):
            chars.append(" ")
        elif ch in _TRACOS:
            chars.append("-")
        else:
            chars.append(ch)
        mapa.append(i)

    _substituir(chars, mapa, _N_NUMERO, "nº")
    _substituir(chars, mapa, _CINCO_UMULA, "Súmula")
    # OCR antes de colapsar hífen/espaço: senão `7I. 346` e `1. o21` perdem o
    # vizinho digitável, e `21737l8 - SP` cola a UF no token do número (causa 4).
    _substituir(chars, mapa, _NUMERO, lambda m: _ocr_no_token(m.group(0)))
    _substituir(chars, mapa, _HIFEN_SOLTO, "-")
    _substituir(chars, mapa, _ESPACO_NO_NUMERO, "")
    _substituir(chars, mapa, _HIFEN_PONTO, ".")
    _substituir(chars, mapa, _HIFENS_DUPLOS, "-")
    return "".join(chars), mapa


def voltar_ao_original(
    original: str,
    mapa: list[int],
    ini_norm: int,
    fim_norm: int,
) -> tuple[int, int]:
    if ini_norm < 0 or fim_norm < ini_norm:
        raise ValueError("intervalo normalizado inválido")
    if not mapa:
        return 0, 0
    if ini_norm >= len(mapa):
        return len(original), len(original)
    inicio = mapa[ini_norm]
    if fim_norm <= ini_norm:
        return inicio, inicio
    ultimo = mapa[min(fim_norm, len(mapa)) - 1]
    fim = ultimo + 1
    if inicio > fim:
        raise ValueError("mapa produziu inicio > fim")
    if inicio < 0 or fim > len(original):
        raise ValueError("offset fora do texto original")
    return inicio, fim
