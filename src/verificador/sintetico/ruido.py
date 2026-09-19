"""Ruído de OCR aplicado à *citação* (não ao texto em volta), para os pares limpo × ruidoso (R35).

Só faz o que o DEFINE lista: letra no lugar de dígito dentro de número, espaço/ponto/quebra de
linha dentro de número, variação de `nº` e de travessão. A resposta certa não muda: o gabarito
do par ruidoso é o mesmo do limpo.
"""

from __future__ import annotations

import random
import re

from verificador.tabelas import ocr

_ENTRE_DIGITOS = re.compile(r"(?<=\d[-.])(?=\d)")
_NO = re.compile(r"\bn[º°.]|\bNo\b")


def _letras_parecidas() -> dict[str, tuple[str, ...]]:
    """dígito → letras que o OCR troca por ele (o inverso de `tabelas.ocr()`)."""
    inverso: dict[str, list[str]] = {}
    for letra, digito in sorted(ocr().items()):
        inverso.setdefault(digito, []).append(letra)
    return {d: tuple(ls) for d, ls in inverso.items()}


def letra_no_lugar_de_digito(s: str, rng: random.Random) -> str:
    troca = _letras_parecidas()
    posicoes = [i for i, ch in enumerate(s) if ch in troca and _dentro_de_numero(s, i)]
    if not posicoes:
        return s
    i = rng.choice(posicoes)
    return s[:i] + rng.choice(troca[s[i]]) + s[i + 1 :]


def _dentro_de_numero(s: str, i: int) -> bool:
    vizinhos = s[max(0, i - 1)] + s[min(len(s) - 1, i + 1)]
    return any(c.isdigit() or c in ".-/" for c in vizinhos)


def _inserir_entre_digitos(s: str, rng: random.Random, sep: str) -> str:
    pontos = [m.start() for m in _ENTRE_DIGITOS.finditer(s)]
    if not pontos:
        return s
    i = rng.choice(pontos)
    return s[:i] + sep + s[i:]


def espaco_no_numero(s: str, rng: random.Random) -> str:
    return _inserir_entre_digitos(s, rng, " ")


def quebra_de_linha_no_numero(s: str, rng: random.Random) -> str:
    return _inserir_entre_digitos(s, rng, "\n")


def variacao_no(s: str, rng: random.Random) -> str:
    m = _NO.search(s)
    if not m:
        return s
    return s[: m.start()] + rng.choice(["No", "n°", "N°", "n."]) + s[m.end() :]


def travessao(s: str, rng: random.Random) -> str:
    return re.sub(r"(?<=\d)-(?=\d)|(?<=\s)-(?=\s)", "–", s, count=1)


def cinco_umula(s: str, rng: random.Random) -> str:
    return re.sub(r"[Ss]úmula", lambda m: "5" + m.group(0)[1:], s, count=1)


TRANSFORMACOES = (
    letra_no_lugar_de_digito,
    espaco_no_numero,
    quebra_de_linha_no_numero,
    variacao_no,
    travessao,
    cinco_umula,
)


def ruidoso(citacao: str, rng: random.Random, quantidade: int = 2) -> str:
    """Aplica até `quantidade` transformações aplicáveis, em ordem aleatória."""
    ordem = list(TRANSFORMACOES)
    rng.shuffle(ordem)
    aplicadas = 0
    for f in ordem:
        novo = f(citacao, rng)
        if novo != citacao:
            citacao, aplicadas = novo, aplicadas + 1
        if aplicadas >= quantidade:
            break
    return citacao
