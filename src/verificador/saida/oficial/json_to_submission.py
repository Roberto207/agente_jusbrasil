# -*- coding: utf-8 -*-
"""
Conversor: JSONs do contrato -> submission.csv do Kaggle.
Uso:  python json_to_submission.py <pasta_com_jsons> [submission.csv]

Lê um .json por documento (formato do Contrato de Entrada e Saída) e gera o CSV
de submissão com 1 linha por documento:
    documento_id, citacoes
    citacoes = "inicio,fim,classe,id_canonico,confianca|..."  ("-" = ausente)

Obs.: `trecho` e `tipo` seguem obrigatórios no JSON (e conferidos pelo validador
local), mas não entram no CSV — a métrica pontua span, classe, link e confiança.
"""
import csv
import json
import sys
from pathlib import Path


def encode(doc: dict) -> str:
    partes = []
    for c in doc.get("citacoes", []):
        classe = c["classificacao"]
        resol = c.get("resolucao") or {}
        id_canonico = str(resol.get("id_canonico", "") or "").strip() or "-"
        conf = c.get("confianca", None)
        conf_s = "-" if conf is None else f"{float(conf):.4f}"
        partes.append(f"{int(c['inicio'])},{int(c['fim'])},{classe},{id_canonico},{conf_s}")
    return "|".join(partes) if partes else "-"   # "-" = sem citações (Kaggle rejeita célula vazia)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("uso: python json_to_submission.py <pasta_com_jsons> [submission.csv]")
    pasta = Path(sys.argv[1])
    destino = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("submission.csv")
    arquivos = sorted(pasta.glob("*.json"))
    if not arquivos:
        sys.exit(f"nenhum .json encontrado em {pasta}")
    linhas = []
    for arq in arquivos:
        doc = json.loads(arq.read_text(encoding="utf-8"))
        documento_id = doc.get("documento_id") or arq.stem
        linhas.append((documento_id, encode(doc)))
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["documento_id", "citacoes"])
        w.writerows(linhas)
    print(f"{destino}: {len(linhas)} documentos.")


if __name__ == "__main__":
    main()
