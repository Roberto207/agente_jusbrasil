"""Grava o dataset sintético no mesmo formato da amostra oficial (`txt/` + gabarito em CSV)."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from pathlib import Path

from verificador.sintetico.gerador import DocumentoSintetico

COLUNAS = ("nivel", "documento_id", "citacao_id", "inicio", "fim", "trecho", "tipo", "classificacao", "id_canonico")
FRACAO_CONTROLE = 0.2


def escrever_dataset(
    documentos: Sequence[DocumentoSintetico], pasta: Path, *, semente: int, fracao_controle: float = FRACAO_CONTROLE
) -> Path:
    """`txt/*.txt`, `goldenset_offsets.csv`, `pares.json`, `divisao.json` e `manifesto_sintetico.json`."""
    (pasta / "txt").mkdir(parents=True, exist_ok=True)
    linhas: list[dict[str, object]] = []
    for doc in documentos:
        with (pasta / "txt" / f"{doc.documento_id}.txt").open("w", encoding="utf-8", newline="") as fh:
            fh.write(doc.texto)
        for k, c in enumerate(doc.citacoes, start=1):
            linhas.append(
                {
                    "nivel": doc.nivel, "documento_id": doc.documento_id, "citacao_id": f"s{k}",
                    "inicio": c.inicio, "fim": c.fim, "trecho": c.trecho.replace("\n", "\\n"),
                    "tipo": c.tipo, "classificacao": c.classificacao, "id_canonico": c.id_canonico or "",
                }
            )
    with (pasta / "goldenset_offsets.csv").open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=COLUNAS, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(linhas)

    ids_limpos = [d.documento_id for d in documentos if d.nivel == 1]
    ids_ruidosos = [d.documento_id for d in documentos if d.nivel == 2]
    pares = [{"limpo": a, "ruidoso": b} for a, b in zip(ids_limpos, ids_ruidosos)]
    n_controle = math.ceil(len(pares) * fracao_controle)
    corte = len(pares) - n_controle  # pares inteiros: limpo e ruidoso ficam do mesmo lado
    divisao = {
        "treino": [x for p in pares[:corte] for x in (p["limpo"], p["ruidoso"])],
        "controle": [x for p in pares[corte:] for x in (p["limpo"], p["ruidoso"])],
    }
    for nome, dados in (("pares.json", pares), ("divisao.json", divisao)):
        (pasta / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pasta / "manifesto_sintetico.json").write_text(
        json.dumps({"semente": semente, "pares": len(pares), "versao_gerador": 1}, indent=2) + "\n", encoding="utf-8"
    )
    return pasta
