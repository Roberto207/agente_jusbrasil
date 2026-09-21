"""Gera a tabela `taxa_acerto` no conjunto de controle (ADR-008, R26).

A tabela é regenerada por código, nunca editada à mão. Caminho com menos de
`MINIMO` ocorrências herda a taxa média da classe. Se o Brier no controle não
for menor que o de uma confiança constante, `enviar` fica falso e o pipeline
não emite `confianca`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verificador.avaliacao import divisao
from verificador.avaliacao.rastro import carregar_rastro
from verificador.avaliacao.solution import montar_solution
from verificador.decisao.caminhos import CLASSE_DO_CAMINHO

MINIMO = 5
NOME_TABELA = "taxa_acerto.json"


@dataclass(frozen=True)
class Observacao:
    caminho: str
    correcao_ocr: bool
    fonte: str
    y: int  # 1 se classe (e link, se real) batem com o gabarito


def _chave(caminho: str, correcao_ocr: bool, fonte: str) -> str:
    return f"{caminho}|{int(correcao_ocr)}|{fonte}"


def _classe(caminho: str) -> str:
    return CLASSE_DO_CAMINHO.get(caminho, "incompleta")


def montar_tabela(observacoes: Sequence[Observacao], minimo: int = MINIMO) -> dict[str, Any]:
    """Agrupa as observações e decide se a confiança deve ser enviada (R26)."""
    por_celula: dict[tuple[str, bool, str], list[int]] = defaultdict(list)
    por_classe: dict[str, list[int]] = defaultdict(list)
    for obs in observacoes:
        por_celula[(obs.caminho, obs.correcao_ocr, obs.fonte)].append(obs.y)
        por_classe[_classe(obs.caminho)].append(obs.y)

    media_classe = {
        classe: (sum(ys) / len(ys) if ys else 0.0) for classe, ys in sorted(por_classe.items())
    }
    geral = [y for ys in por_classe.values() for y in ys]
    taxa_constante = (sum(geral) / len(geral)) if geral else 0.0

    taxas: list[dict[str, Any]] = []
    p_por_obs: list[float] = []
    y_por_obs: list[int] = []
    for (caminho, ocr, fonte), ys in sorted(por_celula.items()):
        n, acertos = len(ys), sum(ys)
        usou_fallback = n < minimo
        taxa = media_classe[_classe(caminho)] if usou_fallback else acertos / n
        taxas.append(
            {
                "caminho": caminho,
                "correcao_ocr": ocr,
                "fonte": fonte,
                "n": n,
                "acertos": acertos,
                "taxa": round(taxa, 6),
                "usou_fallback": usou_fallback,
            }
        )
        p_por_obs.extend([taxa] * n)
        y_por_obs.extend(ys)

    brier = _brier(y_por_obs, p_por_obs)
    brier_constante = _brier(y_por_obs, [taxa_constante] * len(y_por_obs))
    enviar = bool(y_por_obs) and (brier < brier_constante or brier == 0.0)

    return {
        "minimo_ocorrencias": minimo,
        "enviar": enviar,
        "n_controle": len(y_por_obs),
        "taxa_constante": round(taxa_constante, 6),
        "brier_controle": round(brier, 6),
        "brier_constante": round(brier_constante, 6),
        "taxa_media_por_classe": {k: round(v, 6) for k, v in media_classe.items()},
        "taxas": taxas,
    }


def _brier(ys: Sequence[int], ps: Sequence[float]) -> float:
    if not ys:
        return 1.0
    return sum((p - y) ** 2 for y, p in zip(ys, ps)) / len(ys)


def observacoes_do_run(
    pasta_run: Path,
    gabarito: Path,
    documentos: Iterable[str] | None,
    metrica: Any,
) -> list[Observacao]:
    """Casa o rastro com o gabarito pelo mesmo alinhamento da métrica oficial."""
    rastro = carregar_rastro(pasta_run)
    if not rastro:
        raise SystemExit(f"rastro ausente em {pasta_run} — rode `verificador rodar` antes")
    solution = montar_solution(gabarito, documentos)
    saida: list[Observacao] = []
    for _, linha in solution.iterrows():
        doc = str(linha["documento_id"])
        golds = metrica._parse_solution_cell(linha["citacoes"], doc)
        preds_meta = [
            rastro[chave]
            for chave in sorted(rastro)
            if chave[0] == doc
        ]
        preds = [
            {
                "inicio": int(l["inicio"]),
                "fim": int(l["fim"]),
                "classe": l["classificacao"],
                "id_canonico": l["id_canonico"] or "",
                "confianca": None,
            }
            for l in preds_meta
        ]
        pares, _golds_sem, _preds_sem = metrica._casar(golds, preds)
        for gi, pi in pares:
            g, p, meta = golds[gi], preds[pi], preds_meta[pi]
            if g["classe"] == p["classe"] == "real":
                y = 1 if p["id_canonico"] in g["doc_ids"] else 0
            else:
                y = 1 if g["classe"] == p["classe"] else 0
            saida.append(
                Observacao(
                    caminho=str(meta["caminho"]),
                    correcao_ocr=bool(meta["correcao_ocr"]),
                    fonte=str(meta["fonte"]),
                    y=y,
                )
            )
    return saida


def gravar_tabela(tabela: dict[str, Any], destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(tabela, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destino


def destino_padrao() -> Path:
    from importlib import resources

    return Path(str(resources.files("verificador.avaliacao"))) / NOME_TABELA


def _docs_do_conjunto(nome: str, gabarito: Path) -> set[str] | None:
    if nome == "controle":
        return set(divisao.documentos("controle"))
    if nome == "sintetico_controle":
        dados = json.loads((gabarito.parent / "divisao.json").read_text(encoding="utf-8"))
        return set(dados["controle"])
    if nome in ("amostra", "sintetico"):
        return None
    raise SystemExit(f"conjunto de calibração desconhecido: {nome}")
