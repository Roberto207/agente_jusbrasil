"""Rastro por citação (`runs/<run>/rastro.jsonl`): o que cada etapa decidiu e por quê.

Fica fora do JSON do contrato. Alimenta o `erros.md` e a contagem por caminho de decisão.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from verificador.contratos import CitacaoVerificada

NOME = "rastro.jsonl"


def linha_de_rastro(documento_id: str, c: CitacaoVerificada) -> dict[str, object]:
    cand, campos, res = c.candidata, c.campos, c.resolucao
    return {
        "documento_id": documento_id,
        "inicio": cand.inicio,
        "fim": cand.fim,
        "trecho": cand.trecho,
        "forma": cand.forma,
        "padrao": cand.padrao,
        "origem": sorted(cand.origem),
        "campos": {**asdict(campos), "cadeia_recursos": list(campos.cadeia_recursos)},
        "fonte": campos.fonte,
        "correcao_ocr": campos.correcao_ocr,
        "candidatos": list(res.candidatos),
        "caminho": res.caminho,
        "classificacao": res.classificacao,
        "id_canonico": res.id_canonico,
        "confianca": res.confianca,
    }


def escrever_rastro(pasta_run: Path, linhas: Iterable[dict[str, object]]) -> Path:
    ordenadas = sorted(linhas, key=lambda l: (str(l["documento_id"]), int(l["inicio"]), int(l["fim"])))  # type: ignore[arg-type]
    pasta_run.mkdir(parents=True, exist_ok=True)
    caminho = pasta_run / NOME
    caminho.write_text(
        "".join(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n" for l in ordenadas),
        encoding="utf-8",
    )
    return caminho


def carregar_rastro(pasta_run: Path) -> dict[tuple[str, int, int], dict[str, object]]:
    caminho = pasta_run / NOME
    if not caminho.is_file():
        return {}
    saida: dict[tuple[str, int, int], dict[str, object]] = {}
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        if bruta.strip():
            l = json.loads(bruta)
            saida[(l["documento_id"], int(l["inicio"]), int(l["fim"]))] = l
    return saida


def contar_caminhos(rastro: dict[tuple[str, int, int], dict[str, object]]) -> Counter[str]:
    return Counter(str(l["caminho"]) for l in rastro.values())
