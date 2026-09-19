"""Gerador sintético por código (ADR-012, camada 1): documentos com gabarito exato.

Cada documento limpo tem um gêmeo ruidoso (mesmas citações, com ruído de OCR): o par testa o
R35. Tudo sai de `random.Random(semente)`; mesma semente, mesmos bytes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from verificador.base.indice import Indice, construir_indice
from verificador.sintetico import moldes
from verificador.sintetico.citacoes import Fabricada, Fabrica
from verificador.sintetico.ruido import ruidoso


@dataclass(frozen=True)
class CitacaoSintetica:
    inicio: int
    fim: int
    trecho: str
    tipo: str
    classificacao: str
    id_canonico: str | None
    construcao: str


@dataclass(frozen=True)
class DocumentoSintetico:
    documento_id: str
    nivel: int
    texto: str
    citacoes: tuple[CitacaoSintetica, ...]


def _cabecalho(rng: random.Random) -> str:
    cnj = "".join(rng.choice("0123456789") for _ in range(7)) + "-" + "".join(
        rng.choice("0123456789") for _ in range(2)
    ) + f".{rng.randint(2010, 2024)}.{rng.randint(1, 9)}.{rng.randint(0, 27):02d}.{rng.randint(0, 9999):04d}"
    partes = rng.sample(moldes.PARTES, 2)
    return (
        f"{rng.choice(moldes.ORGAOS)}\n\n"
        f"{rng.choice(['Processo nº', 'Autos nº'])} {cnj}\n"
        f"{partes[0]}: {rng.choice(moldes.NOMES)}\n{partes[1]}: {rng.choice(moldes.NOMES)}\n\n"
        f"{rng.choice(moldes.TITULOS)}"
    )


def _quebrar(texto: str, rng: random.Random) -> str:
    """Emula a quebra de linha do original trocando, às vezes, um espaço por `\\n`."""
    espacos = [i for i, ch in enumerate(texto) if ch == " "]
    if espacos and rng.random() < 0.5:
        i = rng.choice(espacos)
        return texto[:i] + "\n" + texto[i + 1 :]
    return texto


def _plano(fabrica: Fabrica, rng: random.Random) -> tuple[str, list[list[str | Fabricada]]]:
    """Cabeçalho e parágrafos; cada parágrafo é uma lista de trechos de texto e citações."""
    cabecalho = _cabecalho(rng)
    n_par = rng.randint(5, 9)
    com_citacao = set(rng.sample(range(n_par), rng.randint(3, min(8, n_par))))
    paragrafos: list[list[str | Fabricada]] = []
    for p in range(n_par):
        frases: list[list[str | Fabricada]] = [[rng.choice(moldes.FRASES_SEM_CITACAO)]]
        if p in com_citacao:
            pre, pos = rng.choice(moldes.FRASES_COM_CITACAO).split("{c}")
            frases.append([_quebrar(pre, rng), fabrica.sortear(rng), _quebrar(pos, rng)])
        if rng.random() < 0.5:
            frases.append([rng.choice(moldes.FRASES_SEM_CITACAO)])
        rng.shuffle(frases)
        par: list[str | Fabricada] = []
        for k, frase in enumerate(frases):
            par.append(" " if k else "")
            par.extend(frase)
        paragrafos.append(par)
    return cabecalho, paragrafos


def _renderizar(
    documento_id: str, nivel: int, cabecalho: str, paragrafos, transformar
) -> DocumentoSintetico:
    partes: list[str] = []
    citacoes: list[CitacaoSintetica] = []
    pos = 0

    def emitir(s: str) -> None:
        nonlocal pos
        partes.append(s)
        pos += len(s)

    emitir(cabecalho + "\n\n")
    for paragrafo in paragrafos:
        for trecho in paragrafo:
            if isinstance(trecho, str):
                emitir(trecho)
                continue
            texto = transformar(trecho.texto)
            inicio = pos
            emitir(texto)
            citacoes.append(
                CitacaoSintetica(inicio, pos, texto, trecho.tipo, trecho.classificacao, trecho.id_canonico, trecho.construcao)
            )
        emitir("\n\n")
    return DocumentoSintetico(documento_id, nivel, "".join(partes), tuple(citacoes))


def gerar(indice: Indice, pares: int, semente: int = 0) -> list[DocumentoSintetico]:
    """`pares` documentos limpos (nível 1) e seus gêmeos ruidosos (nível 2), intercalados."""
    fabrica = Fabrica(indice)
    documentos: list[DocumentoSintetico] = []
    for i in range(pares):
        cabecalho, paragrafos = _plano(fabrica, random.Random(f"{semente}:{i}:texto"))
        rng_ruido = random.Random(f"{semente}:{i}:ruido")
        documentos.append(_renderizar(f"syn_n1_{i:04d}", 1, cabecalho, paragrafos, lambda s: s))
        documentos.append(
            _renderizar(f"syn_n2_{i:04d}", 2, cabecalho, paragrafos, lambda s: ruidoso(s, rng_ruido))
        )
    return documentos


def gerar_dataset(dados: Path, saida: Path, pares: int = 100, semente: int = 0) -> Path:
    from verificador.cli import caminho_db
    from verificador.sintetico.formato import escrever_dataset

    indice = construir_indice(caminho_db(dados))
    return escrever_dataset(gerar(indice, pares, semente), saida, semente=semente)
