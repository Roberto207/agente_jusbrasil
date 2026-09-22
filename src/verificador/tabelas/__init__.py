"""Tabelas versionadas (provisórias da frente B; a frente A pode refiná-las)."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from importlib import resources
from pathlib import Path


def _pasta() -> Path:
    return Path(str(resources.files("verificador.tabelas")))


def _ler_json(nome: str):
    caminho = _pasta() / nome
    return json.loads(caminho.read_text(encoding="utf-8"))


def hash_tabelas() -> str:
    """Hash das tabelas versionadas (entra no manifesto: mudar uma tabela muda o resultado)."""
    import hashlib

    resumo = hashlib.sha256()
    for caminho in sorted(_pasta().glob("*.json")):
        resumo.update(caminho.name.encode("utf-8"))
        resumo.update(caminho.read_bytes())
    return resumo.hexdigest()


@lru_cache(maxsize=1)
def ocr() -> dict[str, str]:
    return dict(_ler_json("ocr.json")["dentro_de_numero"])


@lru_cache(maxsize=1)
def _tst() -> dict[str, tuple[str, ...]]:
    return {token: tuple(siglas) for token, siglas in _ler_json("tst.json").items()}


def tst_tokens() -> tuple[str, ...]:
    """Tokens (minúsculos) de classe/recurso conhecidos no número do TST, maiores primeiro."""
    return tuple(sorted(_tst(), key=len, reverse=True))


def tst_sigla(token: str) -> tuple[str, ...]:
    """Sigla(s) canônica(s) de um token do número do TST (`TST-EDcl-RR-…`).

    Fonte única para o índice (frente A) e a leitura de campos (frente B): as duas
    pontas da comparação precisam nomear `EDcl`, `AgRg`, `AIRR`… do mesmo jeito.
    Um token só pode valer mais de uma sigla (`AgARR` = `AgRg` + `ARR`). Token
    desconhecido volta em maiúsculas.
    """
    limpo = token.strip()
    return _tst().get(limpo.lower(), (limpo.upper(),))


@lru_cache(maxsize=1)
def vocabulario_ocr() -> frozenset[str]:
    """Termos que a correção `m↔rn` pode produzir (vocabulário fechado).

    A página Data do desafio lista `m↔rn` entre os ruídos do nível 2, mas trocar
    às cegas destrói texto correto (`interno` → `intemo`, e `AgInt` é *Agravo
    **Interno***). Por isso a correção só acontece quando o resultado cai neste
    conjunto — âncora, não vocabulário solto (mesmo princípio do ADR-015).

    Chaves iniciadas por `_` são nota de manutenção, não palavras.
    """
    bruto = _ler_json("vocabulario_ocr.json")
    palavras: set[str] = set()
    for chave, valor in bruto.items():
        if chave.startswith("_"):
            continue
        palavras.update(_so_ascii(palavra) for palavra in valor)
    return frozenset(palavras)


def chave_ocr(palavra: str) -> str:
    """Forma comparável de uma palavra: minúscula, sem acento."""
    return _so_ascii(palavra)


@lru_cache(maxsize=1)
def ufs() -> dict[str, tuple[str, ...]]:
    bruto = _ler_json("ufs.json")
    return {sigla: tuple(nomes) for sigla, nomes in bruto.items()}


@lru_cache(maxsize=1)
def leis() -> list[tuple[str, str]]:
    """Lista (alias_normalizado, lei_chave), maior alias primeiro."""
    bruto = _ler_json("leis.json")
    pares: list[tuple[str, str]] = []
    for chave, aliases in bruto.items():
        for alias in aliases:
            pares.append((_so_ascii(alias), chave))
        pares.append((_so_ascii(chave.replace("-", " ")), chave))
    pares.sort(key=lambda item: len(item[0]), reverse=True)
    return pares


@lru_cache(maxsize=1)
def classes() -> list[tuple[str, str]]:
    """Lista (padrão regex, sigla), maior padrão primeiro."""
    bruto = _ler_json("classes.json")["aliases"]
    pares: list[tuple[str, str]] = []
    for item in bruto:
        sigla = item["sigla"]
        for padrao in item["padroes"]:
            pares.append((padrao, sigla))
    pares.sort(key=lambda item: len(item[0]), reverse=True)
    return pares


def _so_ascii(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto.casefold())
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


# `Lei nº 4.737, de 15 de julho de 1965` — formato usado pelos dispositivos da
# base canônica. O ano é o do fim da frase, não o `de 15`.
_LEI_POR_EXTENSO = re.compile(
    r"(decreto[\s-]*lei|lei complementar|lei)\s+n?[oº°.\s]*(\d+(?:\.\d+)*)\s*,?\s*de\b.*?(\d{4})",
)
# `Lei 13.105/2015`, `LC 64/1990`, `Lei Complementar nº 64/1990`.
# O `nº` entre o rótulo e o número é opcional e aparece em várias grafias.
_LEI_COM_BARRA = re.compile(
    r"(decreto[\s-]*lei|lei complementar|lc|lei)\s+n?[oº°.\s]*(\d+(?:\.\d+)*)\s*/\s*(\d{4})"
)

_PREFIXO_LEI = {
    "lei": "LEI",
    "lei complementar": "LC",
    "lc": "LC",
    "decreto-lei": "DL",
    "decreto lei": "DL",
    "decretolei": "DL",
}


def _chave_por_numero(rotulo: str, numero: str, ano: str) -> str:
    prefixo = _PREFIXO_LEI.get(re.sub(r"\s+", " ", rotulo).strip(), "LEI")
    return f"{prefixo}-{numero.replace('.', '')}-{ano}"


def resolver_lei(identificador: str) -> str | None:
    alvo = _so_ascii(identificador)
    alvo = re.sub(r"\s+", " ", alvo).strip()

    # O número explícito manda mais que o apelido: `Lei nº 13.105, de 2015` é
    # inequívoca, enquanto um apelido pode casar por substring.
    for padrao in (_LEI_POR_EXTENSO, _LEI_COM_BARRA):
        m = padrao.search(alvo)
        if m:
            return _chave_por_numero(m.group(1), m.group(2), m.group(3))

    sem_marcador = re.sub(r"\blei(?: complementar)? n[oº°.]?\s*", "lei ", alvo)
    for alias, chave in leis():
        if alias and alias in sem_marcador:
            return chave
    return None


def resolver_uf(texto: str) -> str | None:
    bruto = texto.strip().upper()
    if bruto in ufs():
        return bruto
    alvo = _so_ascii(texto)
    for sigla, nomes in ufs().items():
        if alvo in nomes:
            return sigla
    return None


def padrao_ufs() -> str:
    return "|".join(sorted(ufs(), key=len, reverse=True))
