"""Contratos imutáveis entre os módulos do verificador (DESIGN.md)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TipoCitacao = Literal["jurisprudencia", "lei"]
FormaCitacao = Literal["com_numero", "sumula", "lei_artigo", "sem_numero", "referencia_vaga"]
OrigemCandidata = Literal["regex", "encoder"]
FonteCampos = Literal["regras"]
Classificacao = Literal["real", "inventada", "incompleta"]
NaturezaRegistro = Literal["acordao", "sumula", "dispositivo"]


@dataclass(frozen=True)
class TextoPreparado:
    original: str
    corpo_inicio: int
    normalizado: str
    mapa: list[int]


@dataclass(frozen=True)
class Candidata:
    inicio: int
    fim: int
    trecho: str
    tipo: TipoCitacao
    forma: FormaCitacao
    padrao: str
    origem: frozenset[OrigemCandidata]


@dataclass(frozen=True)
class Campos:
    tribunal: str | None
    classe_principal: str | None
    cadeia_recursos: tuple[str, ...]
    numero: str | None
    uf: str | None
    ano: int | None
    relator: str | None
    lei_chave: str | None
    artigo: str | None
    correcao_ocr: bool
    fonte: FonteCampos


@dataclass(frozen=True)
class RegistroIndice:
    id: str
    natureza: NaturezaRegistro
    tribunal: str | None
    numero: str | None
    classe_principal: str | None
    cadeia_recursos: tuple[str, ...]
    uf: str | None
    ano: int | None
    relator: str | None
    lei_chave: str | None
    artigo: str | None


@dataclass(frozen=True)
class Resolucao:
    classificacao: Classificacao
    id_canonico: str | None
    caminho: str
    candidatos: tuple[str, ...]
    confianca: float | None


@dataclass(frozen=True)
class CitacaoVerificada:
    candidata: Candidata
    campos: Campos
    resolucao: Resolucao
