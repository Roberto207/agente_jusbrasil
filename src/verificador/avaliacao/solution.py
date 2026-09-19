"""Monta o `solution` que o `kaggle_metric.avaliar()` espera a partir do gabarito em CSV."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def montar_solution(gabarito: Path, documentos: Iterable[str] | None = None):
    """Uma linha por documento: `documento_id, nivel, citacoes` (`inicio,fim,classe,doc_ids`).

    `documentos` restringe o resultado (por exemplo, só o conjunto de controle).
    """
    import pandas as pd

    df = pd.read_csv(
        gabarito,
        dtype={
            "documento_id": str,
            "citacao_id": str,
            "classificacao": str,
            "id_canonico": "string",
        },
    )
    if documentos is not None:
        df = df[df["documento_id"].isin(set(documentos))]
    linhas: list[dict[str, object]] = []
    for documento_id, grupo in df.groupby("documento_id", sort=True):
        nivel = int(grupo["nivel"].iloc[0])
        partes: list[str] = []
        ordenado = grupo.sort_values(["inicio", "fim"], kind="mergesort")
        for _, row in ordenado.iterrows():
            classe = str(row["classificacao"]).strip().lower()
            bruto = row["id_canonico"]
            if bruto is None or pd.isna(bruto):
                doc_ids = "-"
            else:
                texto = str(bruto).strip()
                doc_ids = "-" if texto in ("", "<NA>", "nan", "None") else texto
            partes.append(f"{int(row['inicio'])},{int(row['fim'])},{classe},{doc_ids}")
        linhas.append(
            {
                "documento_id": str(documento_id),
                "nivel": nivel,
                "citacoes": "|".join(partes) if partes else "-",
            }
        )
    return pd.DataFrame(linhas)
