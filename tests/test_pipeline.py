"""Pipeline ponta a ponta (A + B + D + C): amostra oficial e dataset sintético."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tests.helpers import iou_offsets
from verificador import cli
from verificador.avaliacao.rastro import carregar_rastro
from verificador.base import construir_indice
from verificador.decisao import CLASSE_DO_CAMINHO
from verificador.decisao.candidatos import normalizar_sumula
from verificador.decisao.caminhos import CAMPOS_NAO_LIDOS, NUMERO_AUSENTE


@pytest.fixture(scope="module")
def indice(pasta_dados):
    return construir_indice(pasta_dados / "desafio1_bracis.db")


@pytest.fixture(scope="module")
def run_amostra(pasta_dados, tmp_path_factory):
    saida = tmp_path_factory.mktemp("amostra")
    cli.cmd_rodar(entrada=pasta_dados / "txt", run_id="amostra", saida=saida, dados=pasta_dados)
    cli.cmd_avaliar(run_id="amostra", saida=saida, dados=pasta_dados)
    return saida / "amostra"


@pytest.fixture(scope="module")
def run_sintetico(pasta_dados, tmp_path_factory):
    raiz = tmp_path_factory.mktemp("sintetico")
    cli.cmd_gerar_sintetico(dados=pasta_dados, saida=raiz / "dados", pares=40, semente=0)
    cli.cmd_rodar(entrada=raiz / "dados" / "txt", run_id="sint", saida=raiz / "runs", dados=pasta_dados)
    cli.cmd_avaliar(
        run_id="sint", saida=raiz / "runs", gabarito=raiz / "dados" / "goldenset_offsets.csv", dados=pasta_dados
    )
    return raiz


def _relatorio(run: Path) -> dict:
    return json.loads((run / "relatorio.json").read_text(encoding="utf-8"))


def _correspondencia_por_iou(jsons: Path, doc: str, gold: dict, limiar: float = 0.5) -> dict | None:
    """Citação prevista cujo span mais se aproxima do span do gabarito, por IoU.

    None quando nenhuma prevista alcança o limiar: é perda de recall, fora de escopo do invariante
    R50 (coberta por test_amostra_nunca_chama_inventada_de_real_e_acha_todos_os_spans /
    test_sintetico_recall_de_spans_tem_piso).
    """
    esperado = (int(gold["inicio"]), int(gold["fim"]))
    citacoes = json.loads((jsons / f"{doc}.json").read_text(encoding="utf-8"))["citacoes"]
    if not citacoes:
        return None
    melhor = max(citacoes, key=lambda c: iou_offsets(esperado, (c["inicio"], c["fim"])))
    return melhor if iou_offsets(esperado, (melhor["inicio"], melhor["fim"])) >= limiar else None


# -- amostra oficial ------------------------------------------------------------------------


def test_amostra_nunca_chama_inventada_de_real_e_acha_todos_os_spans(run_amostra) -> None:
    for nome, conjunto in _relatorio(run_amostra).items():
        assert all(n["tau"] == 0.0 for n in conjunto["niveis"].values()), nome  # τ = 0
        assert conjunto["analise"]["recall_spans"] == 1.0 and conjunto["analise"]["espurios"] == 0, nome
    assert _relatorio(run_amostra)["amostra"]["score_final"] >= 0.95
    from verificador.decisao.confianca import carregar
    tabela = carregar()
    if tabela and tabela.get("enviar"):
        assert _relatorio(run_amostra)["amostra"]["score_final"] >= 1.05
        assert all(n["b"] > 0 for n in _relatorio(run_amostra)["amostra"]["niveis"].values())


def test_amostra_nao_deixa_erro_de_decisao(run_amostra) -> None:
    """Estágio do mesmo caso (candidato único, família TST de revista) resolve; R40 segue
    pegando número emprestado de outra família. Nenhum `gen_n2_*` deve restar no dump.
    """
    erros = (run_amostra / "erros.md").read_text(encoding="utf-8").split("## Conjunto `ajuste`")[0]
    assert "| gen_n2_" not in erros
    assert "numero_contradito" not in erros
    assert "numero_ambiguo" not in erros
    rel = _relatorio(run_amostra)["amostra"]
    assert rel["analise"]["recall_spans"] == 1.0
    from verificador.decisao.confianca import carregar
    if carregar() and carregar().get("enviar"):
        assert rel["score_final"] >= 1.099


def test_toda_real_cumpre_r14_e_o_rastro_bate_com_o_json(run_amostra, indice) -> None:
    rastro = carregar_rastro(run_amostra)
    por_id = {r.id: r for r in indice.registros}
    emitidas = 0
    for arquivo in sorted((run_amostra / "jsons").glob("*.json")):
        for c in json.loads(arquivo.read_text(encoding="utf-8"))["citacoes"]:
            emitidas += 1
            linha = rastro[(arquivo.stem, c["inicio"], c["fim"])]
            assert linha["classificacao"] == c["classificacao"]
            assert CLASSE_DO_CAMINHO[linha["caminho"]] == c["classificacao"]
            assert ("id_canonico" in c["resolucao"]) == (c["classificacao"] == "real")  # R12/R13
            if c["classificacao"] != "real":
                continue
            registro, campos = por_id[c["resolucao"]["id_canonico"]], linha["campos"]
            if linha["forma"] == "lei_artigo":
                assert (registro.lei_chave, registro.artigo) == (campos["lei_chave"], campos["artigo"])
            else:
                numero = normalizar_sumula(campos["numero"]) if linha["forma"] == "sumula" else campos["numero"]
                assert registro.numero == numero  # R14
    assert emitidas == len(rastro)


def test_amostra_toda_real_nunca_cai_em_numero_ausente(run_amostra, gabarito) -> None:
    """R50: a organização garante que todo ruído sobre uma citação real é recuperável por
    normalização — um dígito nunca é trocado por outro dígito. Logo nenhuma citação `real` do
    gabarito pode terminar em `numero_ausente`; se acontecer é sempre bug nosso.
    """
    rastro = carregar_rastro(run_amostra)
    jsons = run_amostra / "jsons"
    violadoras = []
    for linha in gabarito:
        if linha["classificacao"] != "real":
            continue
        pred = _correspondencia_por_iou(jsons, linha["documento_id"], linha)
        if pred is None:
            continue  # recall é outra métrica
        caminho = rastro[(linha["documento_id"], pred["inicio"], pred["fim"])]["caminho"]
        if caminho == NUMERO_AUSENTE:
            violadoras.append((linha["documento_id"], linha["inicio"], linha["fim"]))
    assert not violadoras, f"real do gabarito virou numero_ausente: {violadoras}"


def test_duas_execucoes_dao_o_mesmo_csv_e_o_mesmo_rastro(pasta_dados, tmp_path) -> None:
    """R49."""
    arquivos = []
    for nome in ("a", "b"):
        cli.cmd_rodar(entrada=pasta_dados / "txt", run_id=nome, saida=tmp_path, dados=pasta_dados)
        arquivos.append((tmp_path / nome / "submission.csv", tmp_path / nome / "rastro.jsonl"))
    for a, b in zip(*arquivos):
        assert a.read_bytes() == b.read_bytes()


def test_manifesto_registra_a_execucao(run_amostra) -> None:
    manifesto = json.loads((run_amostra / "manifesto.json").read_text(encoding="utf-8"))
    assert manifesto["execucao"]["citacoes"] == 192
    assert set(manifesto["hashes"]) >= {"tabelas", "base", "json_to_submission", "taxa_acerto"}
    assert manifesto["hashes"]["tabelas"] and manifesto["hashes"]["base"] and manifesto["hashes"]["json_to_submission"]


def test_calibrar_no_controle_passa_r26(run_amostra, run_sintetico, pasta_dados) -> None:
    """Controle da amostra + sintético-controle (composição real de produção,
    resultado_submissoes.md §4). R26 por caminho (ver `montar_tabela`) garante
    `brier_controle <= brier_constante` por construção — sem número mágico aqui: cada célula só
    fica com a própria taxa se bater a constante nos seus próprios dados; senão herda a constante."""
    from verificador.avaliacao.calibrar import _docs_do_conjunto, montar_tabela, observacoes_do_run
    from verificador.cli import importar_modulo

    metrica = importar_modulo("kaggle_metric_oficial", pasta_dados / "kaggle_metric.py")
    gabarito_amostra = pasta_dados / "goldenset_offsets.csv"
    gabarito_sint = run_sintetico / "dados" / "goldenset_offsets.csv"

    obs = observacoes_do_run(run_amostra, gabarito_amostra, _docs_do_conjunto("controle", gabarito_amostra), metrica)
    obs += observacoes_do_run(
        run_sintetico / "runs" / "sint", gabarito_sint, _docs_do_conjunto("sintetico_controle", gabarito_sint), metrica
    )
    tabela = montar_tabela(obs)
    assert tabela["n_controle"] >= 80
    assert tabela["enviar"] is True
    assert tabela["brier_controle"] <= tabela["brier_constante"]


def test_encoder_e_llm_ligados_falham_alto(pasta_dados, tmp_path, monkeypatch) -> None:
    """LLM ainda não existe; encoder sem modelo configurado não pode rodar em silêncio só com regex."""
    monkeypatch.setenv("VERIFICADOR_ENCODER_LINK", "")  # o toml aponta para o HF; aqui, sem modelo
    for chave, erro in (("usar_llm", "não está implementado"), ("usar_encoder", "exige encoder_link")):
        with pytest.raises(SystemExit, match=erro):
            cli.cmd_rodar(entrada=pasta_dados / "txt", run_id="x", saida=tmp_path, dados=pasta_dados, **{chave: True})


# -- sintético ------------------------------------------------------------------------------


def test_sintetico_toda_citacao_extraida_recebe_a_classe_certa(run_sintetico) -> None:
    """A fronteira A × B × D: o que a extração acha, a decisão classifica sem erro e sem τ."""
    relatorio = _relatorio(run_sintetico / "runs" / "sint")
    for nome in ("sintetico", "sintetico_treino", "sintetico_controle"):
        analise = relatorio[nome]["analise"]
        matriz = analise["matriz"]
        for chave, n in matriz.items():
            gold, pred = chave.split("|")
            assert gold == pred or pred == "sem_span", f"{nome}: {chave} = {n}"
        assert analise["espurios"] == 0 and analise["precisao_spans"] == 1.0
        assert all(n["tau"] == 0.0 for n in relatorio[nome]["niveis"].values())


def test_sintetico_recall_de_spans_tem_piso(run_sintetico) -> None:
    """Hoje ~0,90 após 3.1-b (súmulas com n. e siglas); o piso evita regressão."""
    assert _relatorio(run_sintetico / "runs" / "sint")["sintetico"]["analise"]["recall_spans"] >= 0.86


def test_r35_par_limpo_e_ruidoso_concorda(run_sintetico) -> None:
    """Mesma classe e mesmo id nas duas versões; a diferença só pode ser span que o OCR fez perder."""
    dados, jsons = run_sintetico / "dados", run_sintetico / "runs" / "sint" / "jsons"
    gold: dict[str, list[dict]] = {}
    with (dados / "goldenset_offsets.csv").open(encoding="utf-8", newline="") as fh:
        for linha in csv.DictReader(fh):
            gold.setdefault(linha["documento_id"], []).append(linha)

    def previsto(doc: str, g: dict) -> tuple:
        for c in json.loads((jsons / f"{doc}.json").read_text(encoding="utf-8"))["citacoes"]:
            inter = max(0, min(int(g["fim"]), c["fim"]) - max(int(g["inicio"]), c["inicio"]))
            uniao = (int(g["fim"]) - int(g["inicio"])) + (c["fim"] - c["inicio"]) - inter
            if inter and inter / uniao >= 0.5:
                return (c["classificacao"], c["resolucao"].get("id_canonico"))
        return ("perdida", None)

    iguais = total = 0
    for par in json.loads((dados / "pares.json").read_text(encoding="utf-8")):
        for a, b in zip(gold[par["limpo"]], gold[par["ruidoso"]]):
            ra, rb = previsto(par["limpo"], a), previsto(par["ruidoso"], b)
            total += 1
            iguais += ra == rb
            if ra != rb:
                assert "perdida" in (ra[0], rb[0]), f"classe divergiu no par {par}: {ra} × {rb}"
    assert iguais / total >= 0.9  # hoje ~0,96


def test_sintetico_toda_real_nunca_cai_em_numero_ausente(run_sintetico) -> None:
    """R50, versão sintética: cobre também os pares ruidosos (letra_no_lugar_de_digito, m↔rn etc.)."""
    dados = run_sintetico / "dados"
    jsons = run_sintetico / "runs" / "sint" / "jsons"
    rastro = carregar_rastro(run_sintetico / "runs" / "sint")
    with (dados / "goldenset_offsets.csv").open(encoding="utf-8", newline="") as fh:
        gold_reais = [l for l in csv.DictReader(fh) if l["classificacao"] == "real"]

    violadoras = []
    for linha in gold_reais:
        pred = _correspondencia_por_iou(jsons, linha["documento_id"], linha)
        if pred is None:
            continue
        caminho = rastro[(linha["documento_id"], pred["inicio"], pred["fim"])]["caminho"]
        if caminho == NUMERO_AUSENTE:
            violadoras.append((linha["documento_id"], linha["inicio"], linha["fim"]))
    assert not violadoras, f"real do gabarito virou numero_ausente: {violadoras}"


def test_campos_nao_lidos_e_um_caminho_incompleta() -> None:
    assert CLASSE_DO_CAMINHO[CAMPOS_NAO_LIDOS] == "incompleta"
