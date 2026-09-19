"""Índice da base canônica — a entrega da frente A (`DESIGN.md`, etapa [A]).

Transforma os 1.014 registros da base (texto corrido) numa estrutura consultável
por número de processo ou por lei+artigo. É o que permite à frente D decidir se
uma citação é `real`, `inventada` ou `incompleta` sem depender de IA.

O índice guarda o **número próprio** de cada registro (ADR-002), nunca números de
precedentes citados no corpo — a confusão entre os dois faria citações inventadas
parecerem reais.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path

from verificador.base.atributos import (
    extrair_ano,
    extrair_classes,
    extrair_relator,
    extrair_uf,
)
from verificador.base.numero_proprio import artigo_e_lei, numero_proprio
from verificador.contratos import RegistroIndice
from verificador.tabelas import resolver_lei

TABELA = "documentos"

_CONSULTA = f"""
    SELECT id, tribunal, ano, relator, natureza, texto
    FROM {TABELA}
"""


def _abrir_somente_leitura(caminho: Path) -> sqlite3.Connection:
    """Conexão read-only: o índice nunca escreve na base distribuída."""
    uri = caminho.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    # A base tem trechos com bytes inválidos (OCR); trocar por U+FFFD em vez de
    # estourar, como o resto do projeto faz.
    conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
    return conn


def _registro(
    id_: int,
    tribunal: str | None,
    ano_coluna: int | None,
    relator_coluna: str | None,
    natureza: str,
    texto: str,
) -> RegistroIndice:
    """Monta um `RegistroIndice` a partir de uma linha da base.

    Colunas do banco têm prioridade sobre o texto: `tribunal`, `ano` e `relator`
    já vêm preenchidos e são mais confiáveis que qualquer parser (Tarefa 3).
    """
    lei_chave: str | None = None
    artigo: str | None = None
    numero: str | None = None

    if natureza == "dispositivo":
        lido = artigo_e_lei(texto)
        if lido is not None:
            artigo, descricao = lido
            lei_chave = resolver_lei(descricao)
    else:
        numero = numero_proprio(tribunal, natureza, texto)

    if natureza == "acordao":
        classe_principal, cadeia = extrair_classes(tribunal, texto)
        uf = extrair_uf(tribunal, texto)
        ano = ano_coluna if ano_coluna is not None else extrair_ano(texto)
        relator = extrair_relator(texto, relator_coluna)
    else:
        # Súmulas e dispositivos não têm classe processual, UF, ano nem relator.
        classe_principal, cadeia, uf, ano, relator = None, (), None, None, None

    return RegistroIndice(
        id=str(id_),
        natureza=natureza,  # type: ignore[arg-type]
        tribunal=tribunal,
        numero=numero,
        classe_principal=classe_principal,
        cadeia_recursos=cadeia,
        uf=uf,
        ano=ano,
        relator=relator,
        lei_chave=lei_chave,
        artigo=artigo,
    )


class Indice:
    """Registros da base, consultáveis por número ou por lei+artigo.

    As duas consultas devolvem **listas**: o mesmo número de processo aparece em
    vários registros (o recurso original e os agravos internos sobre ele), e a
    mesma lei+artigo pode ter mais de um dispositivo. Quem escolhe entre os
    candidatos é a frente D, com os atributos de desempate (ADR-007).
    """

    def __init__(self, registros: list[RegistroIndice]) -> None:
        self.registros = registros
        self._por_numero: dict[str, list[RegistroIndice]] = defaultdict(list)
        self._por_lei_artigo: dict[tuple[str, str], list[RegistroIndice]] = defaultdict(list)
        for registro in registros:
            if registro.numero:
                self._por_numero[registro.numero].append(registro)
            if registro.lei_chave and registro.artigo:
                self._por_lei_artigo[(registro.lei_chave, registro.artigo)].append(registro)

    def __len__(self) -> int:
        return len(self.registros)

    def por_numero(self, digitos: str) -> list[RegistroIndice]:
        """Registros cujo número próprio é igual ao informado.

        `digitos` já vem reduzido a dígitos (acórdãos) ou no formato de súmula
        (`S83`, `SV10`), como a frente B entrega em `Campos.numero`.
        """
        return list(self._por_numero.get(digitos, ()))

    def por_lei_artigo(self, lei_chave: str, artigo: str) -> list[RegistroIndice]:
        """Dispositivos da mesma lei canônica e mesmo número de artigo."""
        return list(self._por_lei_artigo.get((lei_chave, artigo), ()))

    # -- diagnóstico, usado pelo CLI e pelos testes -------------------------

    def sem_numero(self) -> list[RegistroIndice]:
        """Registros que não são identificáveis por número nem por lei+artigo."""
        return [
            r
            for r in self.registros
            if not r.numero and not (r.lei_chave and r.artigo)
        ]

    def numeros_repetidos(self) -> dict[str, int]:
        """Números presentes em mais de um registro (recursos do mesmo processo)."""
        return {
            numero: len(regs)
            for numero, regs in sorted(self._por_numero.items())
            if len(regs) > 1
        }


def indexar(caminho_db: Path | str) -> list[RegistroIndice]:
    """Lê a base canônica e devolve um `RegistroIndice` por registro.

    Assinatura fixada em `DESIGN.md` ("Contratos entre módulos") — é o que a
    frente D consome. Para consultar, envolver o resultado em `Indice`.
    """
    caminho = Path(caminho_db)
    if not caminho.is_file():
        raise FileNotFoundError(f"base canônica ausente: {caminho}")
    with _abrir_somente_leitura(caminho) as conn:
        linhas = conn.execute(_CONSULTA).fetchall()
    return [_registro(*linha) for linha in linhas]


def construir_indice(caminho_db: Path | str) -> Indice:
    """`indexar()` + estrutura de consulta, em um passo."""
    return Indice(indexar(caminho_db))
