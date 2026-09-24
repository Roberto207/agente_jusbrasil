"""LeNER-Br: leitura do CoNLL, alinhamento com o texto bruto e conversão para a convenção do desafio.

O LeNER-Br (Luz de Araujo et al., PROPOR 2018) é o único texto jurídico real que usamos. A convenção
de anotação dele difere do gabarito do desafio em três pontos, tratados em `rotulo_jurisprudencia`
e `rotulo_legislacao`:

- marca tribunais fora do escopo (TCU, TJ, TRF…), que o desafio não avalia;
- marca o número do **próprio processo** (cabeçalho, ementa), que no desafio é distrator (R34);
- marca lei sem artigo ("Constituição Federal", "CPC/1973"), e o gabarito só tem `art. … da Lei`.

`no_escopo` é a régua do protocolo de go/no-go (`tarefas_equipe.md`, Fase 4). Ela é fixa: mudar o
filtro quebra a comparação com a linha de base do regex.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SPLITS = ("train", "dev", "test")

_FORA = re.compile(
    r"\bTCU\b|\bTC\b|Tribunal de Contas|\bTRF|\bTJ|\bTRT|\bTRE\b|Tribunal Regional|Tribunal de Justiça|Acórdão",
    re.IGNORECASE,
)
_DENTRO = re.compile(
    r"\bST[FJ]\b|\bTS[TE]\b|\bSTM\b|Supremo|Superior Tribunal|Tribunal Superior|Suprema Corte", re.IGNORECASE
)
_ARTIGO = re.compile(r"^(art\.?|artigos?)\b", re.IGNORECASE)
JANELA_CONTEXTO = 40
TAMANHO_MINIMO = 6
DIGITOS_MINIMOS_NUMERO_PROPRIO = 3


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


def documentos(pasta: Path, splits: tuple[str, ...] = SPLITS) -> list[str]:
    """Nomes (sem extensão) de todo documento com `.conll` nos splits pedidos.

    Cada split tem também um arquivo consolidado (`train.conll`, `dev.conll`, `test.conll`) que
    concatena todos os documentos daquele split — excluído aqui pelo nome (stem == nome do split).
    """
    return sorted({p.stem for split in splits for p in (pasta / split).glob("*.conll") if p.stem != split})


def split_do_documento(pasta: Path, nome: str) -> str:
    return next(split for split in SPLITS if (pasta / split / f"{nome}.conll").is_file())


def documento(pasta: Path, nome: str, tipo: str = "JURISPRUDENCIA") -> tuple[str, list[EntidadeLeNER]]:
    """Texto bruto + spans do `tipo` pedido, para um documento do LeNER-Br."""
    raw = (pasta / "raw_text" / f"{nome}.txt").read_text(encoding="utf-8")
    conll = pasta / split_do_documento(pasta, nome) / f"{nome}.conll"
    alinhados = alinhar_tokens(raw, _tokens_do_conll(conll))
    return raw, entidades(tipo, alinhados)


def titulo(pasta: Path, nome: str) -> str:
    caminho = pasta / "metadata" / f"{nome}_meta.json"
    if not caminho.is_file():
        return ""
    return str(json.loads(caminho.read_text(encoding="utf-8")).get("titulo") or "")


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def no_escopo(raw: str, e: EntidadeLeNER) -> bool:
    """Régua do protocolo: `JURISPRUDENCIA` de STF, STJ, TST, TSE ou STM, com dígito.

    Não cita tribunal fora do escopo no trecho; menciona tribunal do escopo no trecho ou em até 40
    caracteres em volta; tem dígito e ao menos 6 caracteres. Maiúsculas não importam.
    """
    trecho = raw[e.inicio : e.fim]
    if _FORA.search(trecho):
        return False
    contexto = raw[max(0, e.inicio - JANELA_CONTEXTO) : e.fim + JANELA_CONTEXTO]
    return bool(_DENTRO.search(contexto)) and bool(_digitos(trecho)) and len(trecho) >= TAMANHO_MINIMO


def numero_proprio(trecho: str, titulo_documento: str) -> bool:
    """O trecho é o número do próprio processo (o do título nos metadados), não uma citação."""
    d, t = _digitos(trecho), _digitos(titulo_documento)
    return len(d) >= DIGITOS_MINIMOS_NUMERO_PROPRIO and bool(t) and (d in t or t in d)


RotuloLeNER = Literal["citacao", "proprio", "fora", "ambigua"]


def rotulo_jurisprudencia(raw: str, e: EntidadeLeNER, titulo_documento: str) -> RotuloLeNER:
    """`citacao` vira rótulo; `fora` vira O; `proprio` e `ambigua` ficam fora da perda.

    `fora` só quando o trecho cita tribunal fora do escopo **e nenhum** do escopo: "Súmula 503 do
    Superior Tribunal de Justiça" casa "Tribunal de Justiça", mas não deve ensinar que é O.
    """
    trecho = raw[e.inicio : e.fim]
    if no_escopo(raw, e):
        return "proprio" if numero_proprio(trecho, titulo_documento) else "citacao"
    if _FORA.search(trecho) and not _DENTRO.search(trecho):
        return "fora"
    return "ambigua"


def rotulo_legislacao(raw: str, e: EntidadeLeNER) -> Literal["citacao", "ambigua"]:
    """Só `art. … da Lei` com dígito é citação (forma c); lei sem artigo fica fora da perda."""
    trecho = raw[e.inicio : e.fim].strip()
    return "citacao" if _ARTIGO.match(trecho) and _digitos(trecho) else "ambigua"
