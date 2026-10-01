"""JSONs por documento → CSV de submissão, sem depender da pasta de dados da organização.

Cópia da lógica do `json_to_submission.py` oficial (distribuído com a amostra do desafio): uma linha por
documento, `citacoes = "inicio,fim,classe,id_canonico,confianca|..."`, `-` para ausente. O formato tem que
continuar **byte a byte** igual ao do oficial (`tests/test_executar.py` confere quando a amostra existe).
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path


def codificar(doc: dict) -> str:
    partes = []
    for c in doc.get("citacoes", []):
        classe = c["classificacao"]
        resol = c.get("resolucao") or {}
        id_canonico = str(resol.get("id_canonico", "") or "").strip() or "-"
        conf = c.get("confianca", None)
        conf_s = "-" if conf is None else f"{float(conf):.4f}"
        partes.append(f"{int(c['inicio'])},{int(c['fim'])},{classe},{id_canonico},{conf_s}")
    return "|".join(partes) if partes else "-"  # "-" = sem citações (célula vazia é rejeitada)


def escrever_submission(pasta_jsons: Path, destino: Path) -> int:
    """Grava o CSV em `destino` e devolve o número de documentos.

    Escreve num arquivo temporário ao lado e só então troca: uma falha no meio não deixa CSV parcial.
    """
    arquivos = sorted(pasta_jsons.glob("*.json"))
    if not arquivos:
        raise FileNotFoundError(f"nenhum .json encontrado em {pasta_jsons}")
    linhas = []
    for arq in arquivos:
        doc = json.loads(arq.read_text(encoding="utf-8"))
        linhas.append((doc.get("documento_id") or arq.stem, codificar(doc)))
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".parcial")
    with temporario.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["documento_id", "citacoes"])
        w.writerows(linhas)
    os.replace(temporario, destino)
    return len(linhas)
