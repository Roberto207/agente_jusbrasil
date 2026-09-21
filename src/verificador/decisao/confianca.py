"""Confiança = taxa de acerto do caminho no controle (ADR-008).

`decidir` permanece puro (sempre `confianca=None`). O pipeline preenche o campo
depois, lendo a tabela gerada por `verificador calibrar`. Se a tabela mandar
`enviar=false` (R26) ou não existir, a confiança continua ausente.
"""

from __future__ import annotations

import json
from dataclasses import replace
from functools import lru_cache
from importlib import resources
from pathlib import Path

from verificador.avaliacao.calibrar import NOME_TABELA, _chave
from verificador.contratos import Campos, Resolucao
from verificador.decisao.caminhos import CLASSE_DO_CAMINHO


def _caminho_tabela() -> Path:
    return Path(str(resources.files("verificador.avaliacao"))) / NOME_TABELA


@lru_cache(maxsize=1)
def carregar() -> dict | None:
    caminho = _caminho_tabela()
    if not caminho.is_file():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def hash_tabela() -> str | None:
    import hashlib

    caminho = _caminho_tabela()
    if not caminho.is_file():
        return None
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def consultar(caminho: str, correcao_ocr: bool, fonte: str) -> float | None:
    """Taxa já com fallback; `None` se a confiança não deve ser enviada."""
    tabela = carregar()
    if not tabela or not tabela.get("enviar"):
        return None
    indice = {(_chave(t["caminho"], bool(t["correcao_ocr"]), t["fonte"])): t for t in tabela["taxas"]}
    celula = indice.get(_chave(caminho, correcao_ocr, fonte))
    if celula is not None:
        return float(celula["taxa"])
    classe = CLASSE_DO_CAMINHO.get(caminho)
    medias = tabela.get("taxa_media_por_classe") or {}
    if classe in medias:
        return float(medias[classe])
    return None


def atribuir(resolucao: Resolucao, campos: Campos) -> Resolucao:
    valor = consultar(resolucao.caminho, campos.correcao_ocr, campos.fonte)
    if valor is None:
        return resolucao
    return replace(resolucao, confianca=float(valor))
