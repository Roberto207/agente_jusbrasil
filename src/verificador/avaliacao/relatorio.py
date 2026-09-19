"""Relatório por execução: nota do `kaggle_metric` + spans + matriz de confusão + erros.

A nota vem sempre do `avaliar()` oficial (nunca reimplementada, R28). Os números de span e a
matriz de confusão usam o mesmo alinhamento do `kaggle_metric` (`_casar`, `_contida`), então
descrevem exatamente os pares que a métrica considerou.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

CLASSES = ("real", "inventada", "incompleta")
LIMITE_ERROS = 40


def avaliar_conjunto(metrica: Any, solution, submission, documentos: Iterable[str] | None = None) -> dict:
    """`metrica.avaliar` restrita a `documentos` (a submissão inteira serve; o excesso é ignorado)."""
    if documentos is not None:
        solution = solution[solution["documento_id"].isin(set(documentos))]
    return metrica.avaliar(solution, submission)


def analisar(metrica: Any, solution, submission, documentos: Iterable[str] | None = None) -> dict[str, Any]:
    """Spans casados/perdidos/espúrios, matriz de confusão e a lista de erros por tipo."""
    if documentos is not None:
        solution = solution[solution["documento_id"].isin(set(documentos))]
    sub = submission.drop_duplicates(subset=["documento_id"], keep="first").set_index("documento_id")

    matriz: Counter[tuple[str, str]] = Counter()
    totais = Counter()
    erros: list[dict[str, Any]] = []
    for _, linha in solution.iterrows():
        doc = linha["documento_id"]
        golds = metrica._parse_solution_cell(linha["citacoes"], doc)
        preds = metrica._parse_submission_cell(sub.loc[doc, "citacoes"], doc)
        pares, golds_sem_par, preds_sem_par = metrica._casar(golds, preds)
        totais["golds"] += len(golds)
        totais["preds"] += len(preds)
        totais["casados"] += len(pares)

        for gi, pi in pares:
            g, p = golds[gi], preds[pi]
            matriz[(g["classe"], p["classe"])] += 1
            if g["classe"] == p["classe"] == "real":
                if p["id_canonico"] not in g["doc_ids"]:
                    erros.append(_erro("link_errado", doc, g, p))
            elif g["classe"] != p["classe"]:
                tipo = "real_perdida" if g["classe"] == "real" else "classe_errada"
                erros.append(_erro(tipo, doc, g, p))
        for gi in golds_sem_par:
            matriz[(golds[gi]["classe"], "sem_span")] += 1
            erros.append(_erro("span_perdido", doc, golds[gi], None))
        casados = [golds[gi] for gi, _ in pares]
        for pi in preds_sem_par:
            p = preds[pi]
            if any(metrica._contida(p, g) for g in casados):
                totais["componentes_ignorados"] += 1
                continue
            matriz[("espurio", p["classe"])] += 1
            totais["espurios"] += 1
            erros.append(_erro("span_espurio", doc, None, p))

    g, p, c = totais["golds"], totais["preds"], totais["casados"]
    return {
        "documentos": len(solution),
        "citacoes_gabarito": g,
        "citacoes_emitidas": p,
        "casadas": c,
        "recall_spans": c / g if g else 0.0,
        "precisao_spans": c / p if p else 0.0,
        "espurios": totais["espurios"],
        "perdidos": g - c,
        "matriz": {f"{a}|{b}": n for (a, b), n in sorted(matriz.items())},
        "erros": erros,
    }


def _erro(tipo: str, doc: str, g: dict | None, p: dict | None) -> dict[str, Any]:
    return {
        "tipo": tipo,
        "documento_id": doc,
        "inicio": (g or p)["inicio"],  # type: ignore[index]
        "fim": (g or p)["fim"],  # type: ignore[index]
        "gabarito": None if g is None else g["classe"],
        "predito": None if p is None else p["classe"],
        "id_predito": None if p is None else p["id_canonico"],
        "ids_gabarito": None if g is None else sorted(g["doc_ids"]),
    }


def _tabela_matriz(matriz: dict[str, int]) -> list[str]:
    colunas = [*CLASSES, "sem_span"]
    linhas = ["| gabarito \\ predito | " + " | ".join(colunas) + " |", "|---|" + "---|" * len(colunas)]
    for gold in (*CLASSES, "espurio"):
        celulas = [str(matriz.get(f"{gold}|{col}", 0)) for col in colunas]
        rotulo = "espúrio (sem par)" if gold == "espurio" else gold
        linhas.append(f"| {rotulo} | " + " | ".join(celulas) + " |")
    return linhas


def formatar_relatorio(
    run_id: str,
    conjuntos: dict[str, dict[str, Any]],
    caminhos: Counter[str] | None = None,
) -> str:
    """`conjuntos[nome] = {"resultado": <avaliar>, "analise": <analisar>}`."""
    linhas = [f"# Relatório — `{run_id}`", ""]
    for nome, bloco in conjuntos.items():
        resultado, analise = bloco["resultado"], bloco["analise"]
        linhas += [
            f"## Conjunto `{nome}` ({analise['documentos']} documentos)",
            "",
            f"**score_final:** {float(resultado['score_final']):.6f}",
            "",
        ]
        for nivel, r in sorted(resultado["niveis"].items()):
            f1 = {c: round(float(v), 6) for c, v in r["f1_por_classe"].items()}
            linhas += [
                f"### Nível {nivel}",
                f"- macro_f1: {float(r['macro_f1']):.6f}",
                f"- f1_por_classe: `{f1}`",
                f"- tau: {float(r['tau']):.6f}",
                f"- s: {float(r['s']):.6f}",
                f"- b: {float(r['b']):.6f}",
                f"- score: {float(r['score']):.6f}",
                "",
            ]
        linhas += [
            "### Spans",
            f"- citações no gabarito: {analise['citacoes_gabarito']} · emitidas: {analise['citacoes_emitidas']}"
            f" · casadas (IoU ≥ 0,5): {analise['casadas']}",
            f"- recall de spans: {analise['recall_spans']:.4f} · precisão de spans: {analise['precisao_spans']:.4f}",
            f"- perdidos: {analise['perdidos']} · espúrios: {analise['espurios']}",
            "",
            "### Matriz de confusão",
            *_tabela_matriz(analise["matriz"]),
            "",
        ]
    if caminhos:
        linhas += ["## Caminhos de decisão (rastro)", *(f"- `{c}`: {n}" for c, n in sorted(caminhos.items())), ""]
    return "\n".join(linhas)


def relatorio_json(conjuntos: dict[str, dict[str, Any]]) -> str:
    """Versão de máquina, lida pelo comparador (evita reinterpretar o markdown)."""
    saida = {
        nome: {
            "score_final": float(b["resultado"]["score_final"]),
            "niveis": {str(n): {k: (v if k == "f1_por_classe" else float(v)) for k, v in r.items()}
                       for n, r in b["resultado"]["niveis"].items()},
            "analise": {k: v for k, v in b["analise"].items() if k != "erros"},
        }
        for nome, b in conjuntos.items()
    }
    return json.dumps(saida, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


_TITULOS = {
    "span_perdido": "Span perdido (citação do gabarito sem par)",
    "span_espurio": "Span espúrio (emitido sem citação no gabarito)",
    "real_perdida": "Real perdida por dúvida ou contradição (ADR-006)",
    "classe_errada": "Classe errada",
    "link_errado": "Link errado (real com id fora do gabarito)",
}


def formatar_erros(
    run_id: str,
    conjuntos: dict[str, dict[str, Any]],
    rastro: dict[tuple[str, int, int], dict[str, Any]] | None = None,
    trechos: dict[tuple[str, int, int], str] | None = None,
) -> str:
    """`erros.md`: erros agrupados por tipo, com caminho e origem quando há rastro."""
    rastro, trechos = rastro or {}, trechos or {}
    linhas = [f"# Erros — `{run_id}`", ""]
    for nome, bloco in conjuntos.items():
        por_tipo: dict[str, list[dict[str, Any]]] = {}
        for e in bloco["analise"]["erros"]:
            por_tipo.setdefault(e["tipo"], []).append(e)
        linhas += [f"## Conjunto `{nome}`", ""]
        if not por_tipo:
            linhas += ["Nenhum erro.", ""]
            continue
        for tipo in _TITULOS:
            itens = por_tipo.get(tipo)
            if not itens:
                continue
            linhas += [f"### {_TITULOS[tipo]} — {len(itens)}", "", "| documento | span | gabarito → predito | caminho | trecho |", "|---|---|---|---|---|"]
            for e in itens[:LIMITE_ERROS]:
                chave = (e["documento_id"], e["inicio"], e["fim"])
                r = rastro.get(chave, {})
                trecho = str(trechos.get(chave) or r.get("trecho") or "").replace("\n", " ").replace("|", "\\|")
                linhas.append(
                    f"| {e['documento_id']} | {e['inicio']}-{e['fim']} | {e['gabarito'] or '—'} → {e['predito'] or '—'}"
                    f" | {r.get('caminho', '—')} | {trecho[:70]} |"
                )
            if len(itens) > LIMITE_ERROS:
                linhas.append(f"\n… e mais {len(itens) - LIMITE_ERROS}.")
            linhas.append("")
    return "\n".join(linhas)
