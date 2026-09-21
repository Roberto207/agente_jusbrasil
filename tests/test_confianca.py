"""Confiança calibrada (ADR-008, R26): tabela no controle e lookup no pipeline."""

from __future__ import annotations

import pytest

from verificador.avaliacao.calibrar import Observacao, montar_tabela
from verificador.contratos import Campos, Resolucao
from verificador.decisao.confianca import atribuir, carregar, consultar


def test_caminho_raro_herda_a_taxa_da_classe() -> None:
    obs = [Observacao("numero_unico", False, "regras", 1) for _ in range(10)]
    obs += [Observacao("lei_unica", False, "regras", 1) for _ in range(6)]
    obs += [Observacao("numero_ambiguo", False, "regras", 0)]  # n=1 → fallback da classe
    tabela = montar_tabela(obs)
    por_chave = {(t["caminho"], t["correcao_ocr"], t["fonte"]): t for t in tabela["taxas"]}
    raro = por_chave[("numero_ambiguo", False, "regras")]
    assert raro["usou_fallback"] is True
    assert raro["taxa"] == tabela["taxa_media_por_classe"]["incompleta"] == 0.0
    assert por_chave[("numero_unico", False, "regras")]["usou_fallback"] is False
    assert por_chave[("numero_unico", False, "regras")]["taxa"] == 1.0
    assert tabela["enviar"] is True
    assert tabela["brier_controle"] < tabela["brier_constante"] or tabela["brier_controle"] == 0.0


def test_r26_nao_envia_se_a_tabela_nao_ganha_da_constante() -> None:
    """Um único caminho: a taxa da célula é a constante, Brier empata, não enviar."""
    obs = [Observacao("numero_unico", False, "regras", 1) for _ in range(8)]
    obs += [Observacao("numero_unico", False, "regras", 0) for _ in range(2)]
    tabela = montar_tabela(obs)
    assert tabela["brier_controle"] == tabela["brier_constante"]
    assert tabela["enviar"] is False


def test_atribuir_respeita_enviar(monkeypatch) -> None:
    campos = Campos(None, None, (), "1", None, None, None, None, None, False, "regras")
    res = Resolucao("real", "1", "numero_unico", ("1",), None)

    monkeypatch.setattr("verificador.decisao.confianca.carregar", lambda: None)
    carregar.cache_clear()
    assert atribuir(res, campos).confianca is None

    monkeypatch.setattr(
        "verificador.decisao.confianca.carregar",
        lambda: {
            "enviar": True,
            "taxa_media_por_classe": {"real": 0.9},
            "taxas": [
                {
                    "caminho": "numero_unico",
                    "correcao_ocr": False,
                    "fonte": "regras",
                    "taxa": 0.95,
                }
            ],
        },
    )
    carregar.cache_clear()
    assert atribuir(res, campos).confianca == pytest.approx(0.95)


def test_consultar_sem_tabela_devolve_none() -> None:
    carregar.cache_clear()
    tabela = carregar()
    if tabela is None or not tabela.get("enviar"):
        assert consultar("numero_unico", False, "regras") is None
    else:
        valor = consultar("numero_unico", False, "regras")
        assert valor is None or 0.0 <= valor <= 1.0
