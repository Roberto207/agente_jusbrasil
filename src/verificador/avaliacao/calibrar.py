"""Gera a tabela `taxa_acerto` no conjunto de controle (ADR-008, R26).

A tabela é regenerada por código, nunca editada à mão. Toda taxa é suavizada em direção a um
prior fixo e pessimista (`ALFA` observações "virtuais" a `PRIOR`) — não só o caminho com menos de
`MINIMO` ocorrências (esse continua marcado em `usou_fallback`, mas é só um aviso; a fórmula já é
uma só). O prior tem de ser uma constante, não a média da própria classe: quando o controle não
tem NENHUM erro (caso de hoje — 301/301), a média de qualquer classe também dá 1,0, e suavizar 1,0
em direção a 1,0 não muda nada. Sem essa âncora externa, um caminho de n grande que nunca errou
sai com taxa 1,0 exata — Brier 0 é fácil de conseguir localmente e caro se o conjunto cego tiver um
erro que o controle não teve (achado de revisão de 22/09, ver `resultado_submissoes.md` §7).

R26 (`o Brier no controle precisa ser menor que o de uma confiança constante`) é conferido **por
caminho**, não agregado: cada célula só usa a própria taxa suavizada se ela bater a constante
sobre os próprios dados da célula (`brier_propria < brier_pooled`); empate ou pior, a célula herda a
constante. Isso torna `brier_controle <= brier_constante` verdade **por construção** — a versão
agregada com tolerância fixa (achado de revisão de 22/09) escondia isso: com o controle sem
nenhum erro, dividir em caminhos SEMPRE perde pra constante em Brier agregado (célula pequena
puxa mais pro prior que o pool inteiro puxa — não é ruído de amostra, é a fórmula), então uma
tolerância cobria o sintoma em vez de resolver a causa. Com a comparação célula a célula, R26
segue cumprido ao pé da letra, sem número mágico. `enviar` só é falso com controle vazio — o que
é seguro porque `b = 0,10·(1−Brier)` nunca é negativo (resultado_submissoes.md §7): mandar
confiança nunca piora a nota real, só muda o tamanho do ganho.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verificador.avaliacao.rastro import carregar_rastro
from verificador.avaliacao.solution import montar_solution
from verificador.decisao.caminhos import CLASSE_DO_CAMINHO

MINIMO = 5
ALFA = 7  # observações "virtuais" na suavização; faixa 5-10 já discutida em resultado_submissoes.md §7
PRIOR = 0.97  # âncora pessimista fixa (não deriva dos dados); mesmo valor já proposto em §7
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


def _suavizar(ys: Sequence[int], alfa: float, prior: float) -> float:
    """Laplace/Bayes empírico: `alfa` observações "virtuais" no valor `prior` (fixo, não deriva
    dos próprios dados — ver docstring do módulo)."""
    return (sum(ys) + alfa * prior) / (len(ys) + alfa) if ys else prior


def montar_tabela(
    observacoes: Sequence[Observacao], minimo: int = MINIMO, alfa: int = ALFA, prior: float = PRIOR
) -> dict[str, Any]:
    """Agrupa as observações; cada caminho usa a própria taxa suavizada ou herda a constante,
    conforme quem bate o outro nos dados daquele caminho (R26 por caminho — ver docstring do módulo)."""
    por_celula: dict[tuple[str, bool, str], list[int]] = defaultdict(list)
    por_classe: dict[str, list[int]] = defaultdict(list)
    for obs in observacoes:
        por_celula[(obs.caminho, obs.correcao_ocr, obs.fonte)].append(obs.y)
        por_classe[_classe(obs.caminho)].append(obs.y)

    media_classe = {classe: _suavizar(ys, alfa, prior) for classe, ys in sorted(por_classe.items())}
    geral = [y for ys in por_classe.values() for y in ys]
    taxa_constante = _suavizar(geral, alfa, prior)

    taxas: list[dict[str, Any]] = []
    p_por_obs: list[float] = []
    y_por_obs: list[int] = []
    for (caminho, ocr, fonte), ys in sorted(por_celula.items()):
        n, acertos = len(ys), sum(ys)
        usou_fallback = n < minimo
        taxa_propria = _suavizar(ys, alfa, prior)
        brier_propria = _brier(ys, [taxa_propria] * n)
        brier_pooled = _brier(ys, [taxa_constante] * n)
        usou_constante = brier_propria >= brier_pooled  # empate ou pior: a célula não bateu a constante
        taxa = taxa_constante if usou_constante else taxa_propria
        taxas.append(
            {
                "caminho": caminho,
                "correcao_ocr": ocr,
                "fonte": fonte,
                "n": n,
                "acertos": acertos,
                "taxa": round(taxa, 6),
                "usou_fallback": usou_fallback,
                "usou_constante": usou_constante,
            }
        )
        p_por_obs.extend([taxa] * n)
        y_por_obs.extend(ys)

    brier = _brier(y_por_obs, p_por_obs)
    brier_constante = _brier(y_por_obs, [taxa_constante] * len(y_por_obs))
    # Verdade por construção (cada célula já escolheu o lado de menor Brier nos próprios dados) —
    # o assert documenta a garantia em vez de confiar só no comentário acima.
    assert not y_por_obs or brier <= brier_constante + 1e-9
    enviar = bool(y_por_obs)

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


