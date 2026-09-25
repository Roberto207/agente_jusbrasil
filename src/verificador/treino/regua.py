"""Régua do go/no-go: recall do extrator nas citações do escopo do LeNER-Br.

A régua é fixa (`lener.no_escopo`); ao lado, a mesma conta sem o número do próprio processo, que o
LeNER-Br marca como citação e o desafio trata como distrator.

Com `--lei`, mede também a régua de lei (proposta em `docs/relatorio-uso-encoder.md`, fixada em
25/09 antes de o `test` de lei ser aberto): entidade `LEGISLACAO` que começa com "art."/"artigo" e
tem dígito (`lener.rotulo_legislacao == "citacao"`, a mesma convenção do dataset de treino).

O `test` só se mede com as regras congeladas: ele não guia correção (protocolo em
`tarefas_equipe.md`, Fase 4).

Uso:
    python -m verificador.treino.regua --lener lener-br/leNER-Br --splits train dev
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from verificador.extracao import extrair
from verificador.texto import preparar
from verificador.treino import lener

IOU_MINIMO = 0.5


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    uniao = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / uniao if uniao > 0 else 0.0


def medir(pasta: Path, split: str, encoder=None) -> tuple[Counter[str], list[tuple[str, str, bool]]]:
    """Contagens da régua e as perdas `(documento, trecho, é_número_próprio)`.

    Com `encoder`, mede a união (ADR-011) e conta à parte o que só o encoder achou (`so_encoder`).
    """
    c: Counter[str] = Counter()
    perdas: list[tuple[str, str, bool]] = []
    for nome in lener.documentos(pasta, splits=(split,)):
        raw, ents = lener.documento(pasta, nome)
        titulo = lener.titulo(pasta, nome)
        cands = extrair(preparar(raw), encoder)
        spans = [(x.inicio, x.fim) for x in cands]
        do_encoder = [(x.inicio, x.fim) for x in cands if "encoder" in x.origem]
        for e in ents:
            if not lener.no_escopo(raw, e):
                continue
            proprio = lener.numero_proprio(raw[e.inicio : e.fim], titulo)
            iou = any(_iou((e.inicio, e.fim), s) >= IOU_MINIMO for s in spans)
            toca = any(s[0] < e.fim and s[1] > e.inicio for s in spans)
            c["escopo"] += 1
            c["iou"] += iou
            c["so_encoder"] += any(_iou((e.inicio, e.fim), s) >= IOU_MINIMO for s in do_encoder)
            c["sobreposicao"] += toca
            if not proprio:
                c["escopo_sem_proprio"] += 1
                c["iou_sem_proprio"] += iou
                c["sobreposicao_sem_proprio"] += toca
            if not iou:
                perdas.append((nome, raw[e.inicio : e.fim], proprio))
    return c, perdas


def medir_lei(pasta: Path, split: str, encoder=None) -> Counter[str]:
    """Régua de lei: artigos com dígito anotados como `LEGISLACAO`, achados por IoU ≥ 0,5."""
    c: Counter[str] = Counter()
    for nome in lener.documentos(pasta, splits=(split,)):
        raw, ents = lener.documento(pasta, nome, "LEGISLACAO")
        cands = extrair(preparar(raw), encoder)
        spans = [(x.inicio, x.fim) for x in cands]
        do_encoder = [(x.inicio, x.fim) for x in cands if "encoder" in x.origem]
        for e in ents:
            if lener.rotulo_legislacao(raw, e) != "citacao":
                continue
            c["escopo"] += 1
            c["iou"] += any(_iou((e.inicio, e.fim), s) >= IOU_MINIMO for s in spans)
            c["so_encoder"] += any(_iou((e.inicio, e.fim), s) >= IOU_MINIMO for s in do_encoder)
    return c


def _pct(a: int, b: int) -> str:
    return f"{a} ({a / b:.1%})" if b else "0"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--lener", type=Path, default=Path("lener-br/leNER-Br"))
    p.add_argument("--splits", nargs="+", default=["train", "dev"], choices=lener.SPLITS)
    p.add_argument("--perdas", action="store_true", help="lista as citações perdidas")
    p.add_argument("--encoder", help="pasta ou repo do encoder ajustado: mede a união regex + encoder")
    p.add_argument("--revisao", help="revisão do encoder (repo do HF)")
    p.add_argument("--lei", action="store_true", help="mede também a régua de lei")
    args = p.parse_args(argv)
    encoder = None
    if args.encoder:
        from verificador.extracao.encoder import Encoder

        encoder = Encoder(args.encoder, args.revisao)

    print("| Divisão | No escopo | IoU ≥ 0,5 | Qualquer sobreposição | Sem nº próprio | IoU ≥ 0,5 sem nº próprio | Só pelo encoder |")
    print("|---|---|---|---|---|---|---|")
    for split in args.splits:
        c, perdas = medir(args.lener, split, encoder)
        print(
            f"| `{split}` | {c['escopo']} | {_pct(c['iou'], c['escopo'])} | {_pct(c['sobreposicao'], c['escopo'])} "
            f"| {c['escopo_sem_proprio']} | {_pct(c['iou_sem_proprio'], c['escopo_sem_proprio'])} "
            f"| {c['so_encoder'] if encoder else '—'} |"
        )
        if args.perdas:
            for nome, trecho, proprio in perdas:
                print(f"   {'P' if proprio else ' '} {nome}: {' '.join(trecho.split())}")
    if args.lei:
        print("\n| Divisão (lei) | Artigos anotados | IoU ≥ 0,5 | Só pelo encoder |")
        print("|---|---|---|---|")
        for split in args.splits:
            c = medir_lei(args.lener, split, encoder)
            print(f"| `{split}` | {c['escopo']} | {_pct(c['iou'], c['escopo'])} | {c['so_encoder'] if encoder else '—'} |")


if __name__ == "__main__":
    main()
