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
_NUMERO = re.compile(
    r"(?<![\w])(?=[\dIlOSgl.]*\d)[\dIlOSgl]+(?:[.\-][\dIlOSgl]+)*",
    re.IGNORECASE,
)
_N_NUMERO = re.compile(
    r"(?<![A-Za-zÁ-ú])(?:[nN][º°oO]|[nN]\.)(?=\s*[\dIlOSgl])",
)
_CINCO_UMULA = re.compile(r"5[úu]mula", re.IGNORECASE)
_ESPACO_NO_NUMERO = re.compile(
    r"(?<=\d) +(?=[\d.\-])|(?<=\d\.) +(?=\d)",
)
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


def _vizinho_digito(token: str, i: int) -> bool:
    if i > 0 and token[i - 1].isdigit():
        return True
    if i + 1 < len(token) and token[i + 1].isdigit():
        return True
    # 1º dígito de um grupo: l.239, I.003, g.324.784
    if i + 2 < len(token) and token[i + 1] in ".-" and token[i + 2].isdigit():
        return True
    # letra no meio do número após separador: 1.o21 (exige dígito depois,
    # senão `…-SP` vira `…-5P`)
    if (
        i >= 2
        and token[i - 1] in ".-"
        and token[i - 2].isdigit()
        and i + 1 < len(token)
        and token[i + 1].isdigit()
    ):
        return True
    return False


def _ocr_no_token(token: str) -> str:
    if not any(ch.isdigit() for ch in token):
        return token
    tabela = ocr()
    saida: list[str] = []
    for i, ch in enumerate(token):
        if ch.isalpha() and ch in tabela and _vizinho_digito(token, i):
            saida.append(tabela[ch])
        else:
            saida.append(ch)
    return "".join(saida)


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
