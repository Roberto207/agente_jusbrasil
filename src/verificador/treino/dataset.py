"""Monta o dataset do encoder: spans por caractere de quatro fontes, com a divisão de cada documento.

| Fonte | Entra no treino | Fica para medir | Nunca entra |
|---|---|---|---|
| sintético base (camada 1) | `treino` do `divisao.json` | `controle` | — |
| sintético diversificado (camada 2) | `treino` | `controle` | — |
| amostra do desafio | `ajuste` (ADR-009) | `controle` | — |
| LeNER-Br | `train` | `dev` | `test` (régua do go/no-go) |

O `test` do LeNER-Br nem chega ao arquivo: a higiene vem da construção, não da disciplina de quem
treina. O JSONL contém texto da amostra do desafio ("Subject to Competition Rules"), então fica em
`runs/` e **nunca é publicado**; o que se publica são os pesos (R46) e este código.

Uso:
    python -m verificador.treino.dataset --sintetico sintetico_hf \\
        --amostra desafio-jusbrasil-bracis-2026 --lener lener-br/leNER-Br --saida runs/encoder_dataset
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from verificador.avaliacao.divisao import documentos as documentos_da_amostra
from verificador.treino import lener

ROTULO_POR_TIPO = {"jurisprudencia": "JUR", "lei": "LEI"}
DIVISAO_DE_TREINO = "treino"


@dataclass(frozen=True)
class Exemplo:
    fonte: str
    documento: str
    divisao: str  # "treino" | "controle" | "dev"
    texto: str
    spans: tuple[tuple[int, int, str], ...]  # (inicio, fim, "JUR" | "LEI")
    ignorar: tuple[tuple[int, int], ...]  # fora da perda: nem citação, nem O


def ler_gabarito(pasta: Path) -> dict[str, list[tuple[int, int, str]]]:
    """Gabarito no formato oficial, conferindo `texto[inicio:fim] == trecho` em cada linha."""
    textos: dict[str, str] = {}
    saida: dict[str, list[tuple[int, int, str]]] = {}
    with (pasta / "goldenset_offsets.csv").open(encoding="utf-8-sig", newline="") as fh:
        for linha in csv.DictReader(fh):
            doc = linha["documento_id"]
            if doc not in textos:
                textos[doc] = (pasta / "txt" / f"{doc}.txt").read_text(encoding="utf-8")
            inicio, fim = int(linha["inicio"]), int(linha["fim"])
            trecho = linha["trecho"] if "\n" in linha["trecho"] else linha["trecho"].replace("\\n", "\n")
            if textos[doc][inicio:fim] != trecho:
                raise ValueError(f"{pasta.name}/{doc} {linha['citacao_id']}: offset não bate com o trecho")
            saida.setdefault(doc, []).append((inicio, fim, ROTULO_POR_TIPO[linha["tipo"]]))
    return saida


def de_gabarito(fonte: str, pasta: Path, divisao: dict[str, str]) -> list[Exemplo]:
    """Um exemplo por `.txt` da pasta (documento sem citação também entra: é exemplo negativo)."""
    gabarito = ler_gabarito(pasta)
    exemplos = []
    for caminho in sorted((pasta / "txt").glob("*.txt")):
        doc = caminho.stem
        if doc not in divisao:
            raise ValueError(f"{fonte}/{doc} não está na divisão: nenhum documento entra sem lado definido")
        spans = tuple(sorted(gabarito.get(doc, [])))
        exemplos.append(Exemplo(fonte, doc, divisao[doc], caminho.read_text(encoding="utf-8"), spans, ()))
    return exemplos


def divisao_do_sintetico(pasta: Path) -> dict[str, str]:
    dados = json.loads((pasta / "divisao.json").read_text(encoding="utf-8"))
    return {doc: lado for lado in ("treino", "controle") for doc in dados[lado]}


def divisao_da_amostra() -> dict[str, str]:
    lados = {"ajuste": DIVISAO_DE_TREINO, "controle": "controle"}
    return {doc: lado for conjunto, lado in lados.items() for doc in documentos_da_amostra(conjunto)}


def de_lener(pasta: Path) -> tuple[list[Exemplo], Counter[str]]:
    """`train` vira treino e `dev` vira dev; o `test` não é lido."""
    lado = {"train": DIVISAO_DE_TREINO, "dev": "dev"}
    exemplos = []
    contagem: Counter[str] = Counter()
    for nome in lener.documentos(pasta, splits=tuple(lado)):
        raw, juris = lener.documento(pasta, nome, "JURISPRUDENCIA")
        _, leis = lener.documento(pasta, nome, "LEGISLACAO")
        titulo = lener.titulo(pasta, nome)
        spans: list[tuple[int, int, str]] = []
        ignorar: list[tuple[int, int]] = []
        for e in juris:
            r = lener.rotulo_jurisprudencia(raw, e, titulo)
            contagem[f"JURISPRUDENCIA:{r}"] += 1
            if r == "citacao":
                spans.append((e.inicio, e.fim, "JUR"))
            elif r in ("proprio", "ambigua"):
                ignorar.append((e.inicio, e.fim))
        for e in leis:
            r = lener.rotulo_legislacao(raw, e)
            contagem[f"LEGISLACAO:{r}"] += 1
            if r == "citacao":
                spans.append((e.inicio, e.fim, "LEI"))
            else:
                ignorar.append((e.inicio, e.fim))
        split = lener.split_do_documento(pasta, nome)
        exemplos.append(Exemplo("lener", nome, lado[split], raw, tuple(sorted(spans)), tuple(sorted(ignorar))))
    return exemplos, contagem


def montar(sintetico: Path, amostra: Path, pasta_lener: Path) -> tuple[list[Exemplo], dict[str, object]]:
    div_sint = divisao_do_sintetico(sintetico)
    exemplos = (
        de_gabarito("sintetico_base", sintetico / "base", div_sint)
        + de_gabarito("sintetico_diversificado", sintetico, div_sint)
        + de_gabarito("amostra", amostra, divisao_da_amostra())
    )
    ex_lener, rotulos_lener = de_lener(pasta_lener)
    exemplos += ex_lener
    for ex in exemplos:
        _conferir_spans(ex)

    resumo: dict[str, dict[str, int]] = {}
    for ex in exemplos:
        chave = f"{ex.fonte}/{ex.divisao}"
        r = resumo.setdefault(chave, Counter())  # type: ignore[arg-type]
        r["documentos"] += 1
        r["ignorados"] += len(ex.ignorar)
        for *_, rotulo in ex.spans:
            r[rotulo] += 1
    return exemplos, {"por_fonte": {k: dict(v) for k, v in sorted(resumo.items())}, "lener_rotulos": dict(rotulos_lener)}


def _conferir_spans(ex: Exemplo) -> None:
    """Spans não se sobrepõem entre si nem com os ignorados (o BIO não representa sobreposição)."""
    todos = sorted([(i, f) for i, f, _ in ex.spans] + list(ex.ignorar))
    for (_, fim_a), (ini_b, _) in zip(todos, todos[1:]):
        if ini_b < fim_a:
            raise ValueError(f"{ex.fonte}/{ex.documento}: spans sobrepostos em {ini_b}")


def _commit_git(pasta: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(pasta), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def escrever(exemplos: list[Exemplo], resumo: dict[str, object], saida: Path, origem: dict[str, object]) -> Path:
    saida.mkdir(parents=True, exist_ok=True)
    caminho = saida / "dataset.jsonl"
    with caminho.open("w", encoding="utf-8", newline="\n") as fh:
        for ex in exemplos:
            fh.write(json.dumps(asdict(ex), ensure_ascii=False) + "\n")
    manifesto = {
        "origem": origem,
        "sha256_dataset": hashlib.sha256(caminho.read_bytes()).hexdigest(),
        **resumo,
    }
    (saida / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return caminho


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sintetico", type=Path, required=True, help="snapshot do HF (raiz = camada 2, base/ = camada 1)")
    p.add_argument("--revisao-sintetico", default="0209a853e6e59b263b138200963b579105baca24")
    p.add_argument("--amostra", type=Path, required=True, help="pasta com txt/ e goldenset_offsets.csv")
    p.add_argument("--lener", type=Path, required=True, help="pasta leNER-Br do clone de peluz/lener-br")
    p.add_argument("--saida", type=Path, default=Path("runs/encoder_dataset"))
    args = p.parse_args(argv)

    exemplos, resumo = montar(args.sintetico, args.amostra, args.lener)
    origem = {
        "sintetico": {"repo": "Roberto2799/jusbrasil-sintetico-diversificado", "revisao": args.revisao_sintetico},
        "lener": {"repo": "https://github.com/peluz/lener-br", "commit": _commit_git(args.lener)},
        "amostra": "dados da competição (não redistribuir)",
    }
    caminho = escrever(exemplos, resumo, args.saida, origem)
    print(f"{len(exemplos)} documentos → {caminho}")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
