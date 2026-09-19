"""Compara duas execuções: diferença de nota e as citações que mudaram."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _delta(a: float, b: float) -> str:
    return f"{a:.4f} → {b:.4f} ({b - a:+.4f})"


def citacoes_da_submissao(caminho: Path) -> dict[str, list[dict[str, Any]]]:
    """`documento_id → [{inicio, fim, classe, id, confianca}]` lido do `submission.csv`."""
    saida: dict[str, list[dict[str, Any]]] = {}
    with caminho.open(encoding="utf-8", newline="") as fh:
        for linha in csv.DictReader(fh):
            itens = []
            celula = (linha["citacoes"] or "").strip()
            if celula not in ("", "-"):
                for bloco in celula.split("|"):
                    ini, fim, classe, id_, conf = [c.strip() for c in bloco.split(",")]
                    itens.append({"inicio": int(ini), "fim": int(fim), "classe": classe, "id": id_, "confianca": conf})
            saida[linha["documento_id"]] = itens
    return saida


def _iou(a: dict[str, Any], b: dict[str, Any]) -> float:
    inter = max(0, min(a["fim"], b["fim"]) - max(a["inicio"], b["inicio"]))
    uniao = (a["fim"] - a["inicio"]) + (b["fim"] - b["inicio"]) - inter
    return inter / uniao if uniao and inter else 0.0


def diferencas(a: dict[str, list[dict[str, Any]]], b: dict[str, list[dict[str, Any]]]) -> dict[str, list[tuple]]:
    """Citações que sumiram, apareceram ou trocaram de classe/id entre as execuções."""
    saida: dict[str, list[tuple]] = {"sumiram": [], "apareceram": [], "mudaram": []}
    for doc in sorted(set(a) | set(b)):
        A, B = a.get(doc, []), b.get(doc, [])
        usados: set[int] = set()
        for x in A:
            melhor = max(
                (i for i in range(len(B)) if i not in usados and _iou(x, B[i]) >= 0.5),
                key=lambda i: _iou(x, B[i]),
                default=None,
            )
            if melhor is None:
                saida["sumiram"].append((doc, x))
                continue
            usados.add(melhor)
            y = B[melhor]
            if (x["classe"], x["id"]) != (y["classe"], y["id"]):
                saida["mudaram"].append((doc, x, y))
        saida["apareceram"] += [(doc, B[i]) for i in range(len(B)) if i not in usados]
    return saida


def comparar_runs(pasta_a: Path, pasta_b: Path, nome_a: str, nome_b: str) -> str:
    ra = json.loads((pasta_a / "relatorio.json").read_text(encoding="utf-8"))
    rb = json.loads((pasta_b / "relatorio.json").read_text(encoding="utf-8"))
    linhas = [f"# Comparação `{nome_a}` → `{nome_b}`", ""]
    for conjunto in sorted(set(ra) & set(rb)):
        linhas += [f"## Conjunto `{conjunto}`", "", f"- score_final: {_delta(ra[conjunto]['score_final'], rb[conjunto]['score_final'])}"]
        for nivel in sorted(set(ra[conjunto]["niveis"]) & set(rb[conjunto]["niveis"])):
            x, y = ra[conjunto]["niveis"][nivel], rb[conjunto]["niveis"][nivel]
            linhas += [
                f"- nível {nivel}: score {_delta(x['score'], y['score'])} · macro_f1 {_delta(x['macro_f1'], y['macro_f1'])}"
                f" · τ {_delta(x['tau'], y['tau'])}"
            ]
            for classe in sorted(set(x["f1_por_classe"]) & set(y["f1_por_classe"])):
                linhas.append(f"  - f1 `{classe}`: {_delta(x['f1_por_classe'][classe], y['f1_por_classe'][classe])}")
        ax, bx = ra[conjunto]["analise"], rb[conjunto]["analise"]
        linhas += [
            f"- recall de spans: {_delta(ax['recall_spans'], bx['recall_spans'])}"
            f" · espúrios: {ax['espurios']} → {bx['espurios']}",
            "",
        ]
    dif = diferencas(citacoes_da_submissao(pasta_a / "submission.csv"), citacoes_da_submissao(pasta_b / "submission.csv"))
    linhas += [
        "## Citações que mudaram",
        f"- sumiram: {len(dif['sumiram'])} · apareceram: {len(dif['apareceram'])} · trocaram de classe/id: {len(dif['mudaram'])}",
        "",
    ]
    for doc, x, y in dif["mudaram"][:40]:
        linhas.append(f"- {doc} {x['inicio']}-{x['fim']}: {x['classe']}({x['id']}) → {y['classe']}({y['id']})")
    return "\n".join(linhas) + "\n"
