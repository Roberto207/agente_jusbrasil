"""Ponto de encaixe do LLM leitor de campos difíceis (ADR-013) e a conferência R48.

Nesta versão o LLM não existe: `ler_campos_llm` devolve `None` para tudo e a fila cai no caminho
`campos_nao_lidos`. A conferência já está pronta e testada para o LLM entrar sem mexer na decisão.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from verificador.contratos import Campos, Candidata
from verificador.tabelas import ocr

_SEPARADORES = ".-/ \t\n"


def ler_campos_llm(fila: Sequence[Candidata], llm: object | None = None) -> list[Campos | None]:
    return [None] * len(fila)


def _sequencias_de_digitos(trecho_normalizado: str) -> list[str]:
    """Sequências de dígitos que o trecho contém, aplicando só as trocas da tabela de confusões de OCR.

    Um trecho só conta se tiver ao menos um dígito de verdade: palavras como `nos` (com `o` e `s`,
    letras da tabela) nunca viram número.
    """
    tabela = ocr()
    sequencias: list[str] = []
    atual: list[str] = []
    tem_digito = False

    def fechar() -> None:
        nonlocal atual, tem_digito
        if atual and tem_digito:
            sequencias.append("".join(atual))
        atual, tem_digito = [], False

    for ch in trecho_normalizado:
        if ch.isdigit():
            atual.append(ch)
            tem_digito = True
        elif ch in tabela:
            atual.append(tabela[ch])
        elif ch in _SEPARADORES:
            continue  # pontuação e espaço dentro do número não interrompem a sequência
        else:
            fechar()
    fechar()
    return sequencias


def numero_do_llm_valido(numero: str, trecho_normalizado: str) -> bool:
    """R48: o número devolvido pelo LLM só vale se seus dígitos saem do trecho normalizado."""
    digitos = re.sub(r"\D", "", numero)
    return bool(digitos) and any(digitos in s for s in _sequencias_de_digitos(trecho_normalizado))
