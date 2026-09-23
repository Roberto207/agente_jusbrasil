"""Confiança calibrada (ADR-008, R26): tabela no controle e lookup no pipeline."""

from __future__ import annotations

import pytest

from verificador.avaliacao.calibrar import Observacao, montar_tabela
from verificador.contratos import Campos, Resolucao
from verificador.decisao.confianca import atribuir, carregar, consultar


def test_caminho_raro_herda_a_taxa_da_classe() -> None:
    """`usou_fallback` só documenta n baixo — a suavização (em direção ao prior fixo) roda pra
    todo mundo, então a taxa do caminho raro (n=1, y=0) e a média da classe "incompleta" (que só
    ele alimenta) saem iguais entre si, mas nenhuma das duas é a taxa crua (0,0 ou 1,0)."""
    obs = [Observacao("numero_unico", False, "regras", 1) for _ in range(10)]
    obs += [Observacao("lei_unica", False, "regras", 1) for _ in range(6)]
    obs += [Observacao("numero_ambiguo", False, "regras", 0)]  # n=1 → abaixo de MINIMO
    tabela = montar_tabela(obs)
    por_chave = {(t["caminho"], t["correcao_ocr"], t["fonte"]): t for t in tabela["taxas"]}
    raro = por_chave[("numero_ambiguo", False, "regras")]
    assert raro["usou_fallback"] is True
    assert raro["taxa"] == tabela["taxa_media_por_classe"]["incompleta"]
    assert 0.0 < raro["taxa"] < 1.0  # puxado para o prior fixo, não fica em 0,0 exato
    unico = por_chave[("numero_unico", False, "regras")]
    assert unico["usou_fallback"] is False
    assert unico["taxa"] < 1.0  # nem o caminho de n=10 sem erro escapa da suavização
    assert tabela["enviar"] is True
    assert tabela["brier_controle"] < tabela["brier_constante"] or tabela["brier_controle"] == 0.0


def test_taxa_suaviza_mesmo_sem_erro_e_com_n_grande() -> None:
    """50/50 acertos não vira taxa 1,0 exata quando outro caminho da mesma classe tem erro:
    a suavização (Laplace em direção à média da classe) sempre entra, não só abaixo de MINIMO —
    achado de revisão de 22/09 (taxa 1,0/Brier 0 em todo caminho é overconfiante, ver
    resultado_submissoes.md §7)."""
    obs = [Observacao("numero_unico", False, "regras", 1) for _ in range(50)]
    obs += [Observacao("lei_unica", False, "regras", 1) for _ in range(4)]
    obs += [Observacao("lei_unica", False, "regras", 0) for _ in range(1)]  # mesma classe "real", 1 erro
    tabela = montar_tabela(obs)
    por_chave = {(t["caminho"], t["correcao_ocr"], t["fonte"]): t for t in tabela["taxas"]}
    unico = por_chave[("numero_unico", False, "regras")]
    assert unico["usou_fallback"] is False  # n=50 >= MINIMO
    assert unico["taxa"] < 1.0  # mas a taxa puxa para a média da classe "real" (0,90), não fica exata


def test_celula_sem_diferenciacao_herda_a_constante() -> None:
    """Um único caminho: a taxa própria e a constante vêm dos mesmos dados — empatam, a célula
    herda a constante (`usou_constante`) e a tabela ainda é enviada: existe dado pra calibrar, e
    mandar confiança nunca piora a nota real (`b >= 0`, resultado_submissoes.md §7). R26 (Brier
    por caminho não pode perder pra constante) segue cumprido por construção — ver
    `montar_tabela`, não por uma comparação agregada com tolerância."""
    obs = [Observacao("numero_unico", False, "regras", 1) for _ in range(8)]
    obs += [Observacao("numero_unico", False, "regras", 0) for _ in range(2)]
    tabela = montar_tabela(obs)
    celula = tabela["taxas"][0]
    assert celula["usou_constante"] is True
    assert celula["taxa"] == tabela["taxa_constante"]
    assert tabela["brier_controle"] == tabela["brier_constante"]
    assert tabela["enviar"] is True


def test_caminho_com_erro_de_verdade_mantem_taxa_propria() -> None:
    """`numero_ambiguo` erra de verdade (25%, não é ruído de célula pequena) e bate a constante
    nos próprios dados — mantém taxa diferenciada, mais baixa que a constante (`usou_constante`
    fica `False`): é exatamente o caso que a suavização por caminho existe para capturar."""
    obs = [Observacao("numero_unico", False, "regras", 1) for _ in range(80)]
    obs += [Observacao("numero_ambiguo", False, "regras", 1) for _ in range(15)]
    obs += [Observacao("numero_ambiguo", False, "regras", 0) for _ in range(5)]
    tabela = montar_tabela(obs)
    por_chave = {(t["caminho"], t["correcao_ocr"], t["fonte"]): t for t in tabela["taxas"]}
    ambiguo = por_chave[("numero_ambiguo", False, "regras")]
    assert ambiguo["usou_constante"] is False
    assert ambiguo["taxa"] < tabela["taxa_constante"]
    assert tabela["enviar"] is True


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
