"""Rótulos BIO por token e janelas deslizantes, sem depender de tokenizador.

Quem chama passa os `offsets` por token (o `offset_mapping` de um tokenizador rápido). Tokens
especiais têm offset vazio (`(0, 0)`) e ficam fora da perda. As mesmas funções servem ao treino
(`rotular`) e à inferência (`decodificar`, `dono_por_token`), então a ida e a volta são testáveis.
"""

from __future__ import annotations

from collections.abc import Sequence

ROTULOS = ("O", "B-JUR", "I-JUR", "B-LEI", "I-LEI")
ID_ROTULO = {r: i for i, r in enumerate(ROTULOS)}
IGNORAR = -100
TAMANHO_JANELA = 510  # 512 menos [CLS] e [SEP]
SOBREPOSICAO = 128


def _toca(a: int, b: int, inicio: int, fim: int) -> bool:
    return a < fim and b > inicio


def rotular(
    offsets: Sequence[tuple[int, int]],
    spans: Sequence[tuple[int, int, str]],
    ignorar: Sequence[tuple[int, int]] = (),
) -> list[int]:
    """Um id de rótulo por token: `B-` no primeiro token que toca o span, `I-` nos seguintes."""
    saida: list[int] = []
    anterior: int | None = None  # índice do span do token anterior
    for a, b in offsets:
        if b <= a or any(_toca(a, b, i, f) for i, f in ignorar):
            saida.append(IGNORAR)
            anterior = None
            continue
        dono = next((k for k, (i, f, _) in enumerate(spans) if _toca(a, b, i, f)), None)
        if dono is None:
            saida.append(ID_ROTULO["O"])
        else:
            prefixo = "I" if dono == anterior else "B"
            saida.append(ID_ROTULO[f"{prefixo}-{spans[dono][2]}"])
        anterior = dono
    return saida


def decodificar(offsets: Sequence[tuple[int, int]], rotulos: Sequence[int]) -> list[tuple[int, int, str]]:
    """Spans por caractere a partir dos rótulos previstos. `I-` sem `B-` antes abre um span novo."""
    saida: list[tuple[int, int, str]] = []
    atual: list = []  # [inicio, fim, tipo]
    for (a, b), r in zip(offsets, rotulos):
        nome = ROTULOS[r] if 0 <= r < len(ROTULOS) else "O"
        if b <= a or nome == "O":
            if atual:
                saida.append(tuple(atual))  # type: ignore[arg-type]
                atual = []
            continue
        prefixo, tipo = nome.split("-")
        if prefixo == "I" and atual and atual[2] == tipo:
            atual[1] = b
            continue
        if atual:
            saida.append(tuple(atual))  # type: ignore[arg-type]
        atual = [a, b, tipo]
    if atual:
        saida.append(tuple(atual))  # type: ignore[arg-type]
    return saida


def janelas(n_tokens: int, tamanho: int = TAMANHO_JANELA, sobreposicao: int = SOBREPOSICAO) -> list[tuple[int, int]]:
    """Intervalos `[inicio, fim)` de tokens que cobrem o documento inteiro, com sobreposição."""
    if n_tokens <= tamanho:
        return [(0, n_tokens)]
    passo = tamanho - sobreposicao
    inicios = list(range(0, n_tokens - tamanho, passo)) + [n_tokens - tamanho]
    return [(i, i + tamanho) for i in inicios]


def dono_por_token(n_tokens: int, cortes: Sequence[tuple[int, int]]) -> list[int]:
    """Para cada token, a janela em que ele está mais longe da borda (a previsão mais confiável)."""
    donos = []
    for t in range(n_tokens):
        candidatas = [(min(t - i, f - 1 - t), -k) for k, (i, f) in enumerate(cortes) if i <= t < f]
        donos.append(-max(candidatas)[1])
    return donos
