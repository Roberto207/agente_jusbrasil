"""JSON por documento no contrato da organização (`specs/scope.md`, "schema 1.2")."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from verificador.contratos import CitacaoVerificada
from verificador.saida.validar import ErroDeSaida, validar_citacoes


def citacao_para_json(c: CitacaoVerificada) -> dict[str, object]:
    cand, res = c.candidata, c.resolucao
    item: dict[str, object] = {
        "inicio": int(cand.inicio),
        "fim": int(cand.fim),
        "trecho": cand.trecho,
        "tipo": cand.tipo,
        "classificacao": res.classificacao,
        "resolucao": {"id_canonico": str(res.id_canonico)} if res.classificacao == "real" else {},
    }
    if res.confianca is not None:
        item["confianca"] = float(res.confianca)
    return item


def escrever_json(
    documento_id: str,
    citacoes: Sequence[CitacaoVerificada],
    pasta: Path,
    texto: str | None = None,
) -> Path:
    """Grava `<documento_id>.json` em `pasta`, na ordem do texto.

    Recusa (`ErroDeSaida`) a saída que o Kaggle rejeitaria. Com `texto`, confere também o R38.
    """
    ordenadas = sorted(citacoes, key=lambda c: (c.candidata.inicio, c.candidata.fim))
    problemas = validar_citacoes(documento_id, ordenadas, texto)
    if problemas:
        raise ErroDeSaida("\n".join(problemas))

    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{documento_id}.json"
    dados = {
        "documento_id": documento_id,
        "citacoes": [citacao_para_json(c) for c in ordenadas],
    }
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return caminho
