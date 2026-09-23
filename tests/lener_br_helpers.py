"""Parser do formato CoNLL/IOB do LeNER-Br: reconstrói spans de caractere das entidades a partir
das tags, alinhando contra o texto bruto (`raw_text/`) do mesmo documento.

Não faz parte do pacote `verificador` — é só ferramenta de leitura do dataset externo para a sonda
de recall (`tests/test_lener_br.py`), sem nenhuma dependência do resto do projeto.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SPLITS = ("train", "dev", "test")


@dataclass(frozen=True)
class EntidadeLeNER:
    inicio: int
    fim: int
    tipo: str


def _tokens_do_conll(caminho: Path) -> list[tuple[str, str]]:
    """[(token, tag)], ignorando linhas em branco (fronteira de sentença)."""
    saida: list[tuple[str, str]] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        token, _, tag = linha.rpartition(" ")
        if token:
            saida.append((token, tag))
    return saida


def alinhar_tokens(raw: str, tokens: list[tuple[str, str]]) -> list[tuple[int, int, str, str]]:
    """[(inicio, fim, token, tag)] — alinha cada token contra `raw`, avançando um cursor.

    Estratégia gulosa: pula espaço em branco, tenta casar o token exatamente na posição do
    cursor; se não bater (pontuação colada de um jeito diferente do raw_text), procura o token
    numa janela curta à frente. Token não encontrado é pulado — não trava o alinhamento inteiro
    por um único desvio pontual.
    """
    saida: list[tuple[int, int, str, str]] = []
    cursor = 0
    n = len(raw)
    for token, tag in tokens:
        while cursor < n and raw[cursor].isspace():
            cursor += 1
        if raw[cursor : cursor + len(token)] == token:
            saida.append((cursor, cursor + len(token), token, tag))
            cursor += len(token)
            continue
        achado = raw.find(token, cursor, cursor + 200)
        if achado != -1:
            saida.append((achado, achado + len(token), token, tag))
            cursor = achado + len(token)
    return saida


def entidades(tipo: str, alinhados: list[tuple[int, int, str, str]]) -> list[EntidadeLeNER]:
    """Funde tokens `B-`/`I-` consecutivos do `tipo` pedido em spans únicos."""
    saida: list[EntidadeLeNER] = []
    inicio = fim = None
    for tok_inicio, tok_fim, _tok, tag in alinhados:
        do_tipo = tag in (f"B-{tipo}", f"I-{tipo}")
        comeca = tag == f"B-{tipo}"
        if do_tipo and not comeca and inicio is not None:
            fim = tok_fim
            continue
        if inicio is not None:
            saida.append(EntidadeLeNER(inicio, fim, tipo))  # type: ignore[arg-type]
            inicio = fim = None
        if comeca:
            inicio, fim = tok_inicio, tok_fim
    if inicio is not None:
        saida.append(EntidadeLeNER(inicio, fim, tipo))  # type: ignore[arg-type]
    return saida


def documentos(pasta: Path) -> list[str]:
    """Nomes (sem extensão) de todo documento com `.conll` em qualquer split.

    Cada split tem também um arquivo consolidado (`train.conll`, `dev.conll`, `test.conll`) que
    concatena todos os documentos daquele split — excluído aqui pelo nome (stem == nome do split).
    """
    return sorted(
        {
            p.stem
            for split in SPLITS
            for p in (pasta / split).glob("*.conll")
            if p.stem != split
        }
    )


def documento(pasta: Path, nome: str, tipo: str = "JURISPRUDENCIA") -> tuple[str, list[EntidadeLeNER]]:
    """Texto bruto + spans do `tipo` pedido, para um documento do LeNER-Br."""
    raw = (pasta / "raw_text" / f"{nome}.txt").read_text(encoding="utf-8")
    conll = next(p for split in SPLITS if (p := pasta / split / f"{nome}.conll").is_file())
    alinhados = alinhar_tokens(raw, _tokens_do_conll(conll))
    return raw, entidades(tipo, alinhados)
