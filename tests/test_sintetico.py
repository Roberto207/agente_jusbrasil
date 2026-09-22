"""Frente C — gerador sintético por código (ADR-012, camada 1)."""

from __future__ import annotations

import csv
import random

import pytest

from tests.test_frente_c import _run_do_gabarito
from verificador import cli
from verificador.base import construir_indice
from verificador.sintetico import gerar
from verificador.sintetico import ruido
from verificador.sintetico.formato import escrever_dataset

CONSTRUCOES = {
    "real_acordao", "real_sumula", "real_lei", "inventada_numero", "emprestada", "ambigua",
    "sumula_inventada", "lei_inventada", "lei_desconhecida", "sem_numero", "tema",
}


@pytest.fixture(scope="module")
def indice(pasta_dados):
    return construir_indice(pasta_dados / "desafio1_bracis.db")


@pytest.fixture(scope="module")
def documentos(indice):
    return gerar(indice, 40, semente=0)


def test_mesma_semente_gera_os_mesmos_bytes(indice, tmp_path) -> None:
    for nome, semente in (("a", 3), ("b", 3), ("c", 4)):
        escrever_dataset(gerar(indice, 8, semente), tmp_path / nome, semente=semente)
    ler = lambda nome: {p.name: p.read_bytes() for p in sorted((tmp_path / nome).rglob("*")) if p.is_file()}
    assert ler("a") == ler("b")
    assert ler("a") != ler("c")


def test_gabarito_bate_com_o_texto_e_os_spans_sao_disjuntos(documentos) -> None:
    ids = [d.documento_id for d in documentos]
    assert len(ids) == len(set(ids))
    for doc in documentos:
        assert doc.citacoes
        ordenadas = sorted(doc.citacoes, key=lambda c: c.inicio)
        for c in ordenadas:
            assert c.trecho == doc.texto[c.inicio : c.fim]
        assert all(a.fim <= b.inicio for a, b in zip(ordenadas, ordenadas[1:]))


def test_par_ruidoso_tem_o_mesmo_gabarito_do_limpo(documentos) -> None:
    limpos = [d for d in documentos if d.nivel == 1]
    ruidosos = [d for d in documentos if d.nivel == 2]
    assert len(limpos) == len(ruidosos) == 40
    mudou = 0
    for a, b in zip(limpos, ruidosos):
        assert [(c.classificacao, c.id_canonico, c.tipo, c.construcao) for c in a.citacoes] == [
            (c.classificacao, c.id_canonico, c.tipo, c.construcao) for c in b.citacoes
        ]
        mudou += sum(x.trecho != y.trecho for x, y in zip(a.citacoes, b.citacoes))
    assert mudou > 0.5 * sum(len(d.citacoes) for d in limpos), "o gêmeo ruidoso precisa ter ruído de verdade"


def test_cobre_todas_as_construcoes_e_as_tres_classes(documentos, indice) -> None:
    citacoes = [c for d in documentos for c in d.citacoes]
    assert {c.construcao for c in citacoes} == CONSTRUCOES
    assert {c.classificacao for c in citacoes} == {"real", "inventada", "incompleta"}
    ids_da_base = {r.id for r in indice.registros}
    assert all(c.id_canonico in ids_da_base for c in citacoes if c.classificacao == "real")
    assert all(c.id_canonico is None for c in citacoes if c.classificacao != "real")
    assert {c.tipo for c in citacoes if c.construcao.endswith("lei") or c.construcao.startswith("lei_")} == {"lei"}


def test_numero_emprestado_nao_vira_real(documentos) -> None:
    """R40: número que existe, mas com classe/UF que contradiz os registros → `inventada`."""
    emprestadas = [c for d in documentos for c in d.citacoes if c.construcao == "emprestada"]
    assert emprestadas and all(c.classificacao == "inventada" for c in emprestadas)


def test_forma_d_e_sempre_incompleta_e_tema_inventada(documentos) -> None:
    citacoes = [c for d in documentos for c in d.citacoes]
    assert all(c.classificacao == "incompleta" for c in citacoes if c.construcao == "sem_numero")
    assert all(c.classificacao == "inventada" for c in citacoes if c.construcao == "tema")


def test_distratores_nao_estao_no_gabarito(documentos) -> None:
    """Referência vaga, `fls. 10/20` e protocolo aparecem no texto mas nunca como citação (R33)."""
    for doc in documentos:
        for marca in ("jurisprudência pacífica", "entendimento sumulado", "fls. 10/20", "2019.1234567"):
            pos = doc.texto.find(marca)
            if pos >= 0:
                assert not any(c.inicio < pos + len(marca) and pos < c.fim for c in doc.citacoes)


def test_transformacoes_de_ruido() -> None:
    rng = random.Random(0)
    assert any(ch.isalpha() and ch in "lIOSg" for ch in ruido.letra_no_lugar_de_digito("REsp 1.741.784/PR", rng)[5:])
    assert " " in ruido.espaco_no_numero("7000380-08.2023", rng)
    assert "\n" in ruido.quebra_de_linha_no_numero("7000380-08.2023", rng)
    assert ruido.variacao_no("REsp nº 1", rng) != "REsp nº 1"
    assert ruido.cinco_umula("Súmula 83", rng) == "5úmula 83"
    # `m↔rn` dentro de palavra (página Data do desafio): é ruído de letra, então age mesmo onde não
    # há número — por isso o caso "sem nada para corromper" agora é uma palavra sem `m` nem `rn`.
    assert "rn" in ruido.m_vira_rn("Súmula 83", rng)
    assert ruido.rn_vira_m("Agravo Interno", rng) == "Agravo Intemo"
    assert ruido.ruidoso("tese s/ base legal", rng) == "tese s/ base legal"


def test_dataset_no_formato_da_amostra_e_aceito_pela_metrica(indice, pasta_dados, tmp_path) -> None:
    pasta = tmp_path / "sint"
    cli.cmd_gerar_sintetico(dados=pasta_dados, saida=pasta, pares=10, semente=1)
    assert {p.name for p in pasta.iterdir()} == {
        "txt", "goldenset_offsets.csv", "pares.json", "divisao.json", "manifesto_sintetico.json"
    }
    with (pasta / "goldenset_offsets.csv").open(encoding="utf-8", newline="") as fh:
        linhas = list(csv.DictReader(fh))
    textos = {p.stem: p.read_text(encoding="utf-8") for p in (pasta / "txt").glob("*.txt")}
    assert len(textos) == 20 and {l["documento_id"] for l in linhas} == set(textos)

    _run_do_gabarito(pasta_dados, textos, linhas, tmp_path, "sint")
    resultado = cli.cmd_avaliar(
        run_id="sint", saida=tmp_path, gabarito=pasta / "goldenset_offsets.csv", dados=pasta_dados
    )
    assert resultado["score_final"] == pytest.approx(1.0)


def test_divisao_do_sintetico_mantem_o_par_do_mesmo_lado(documentos, tmp_path) -> None:
    import json

    escrever_dataset(documentos, tmp_path, semente=0)
    divisao = json.loads((tmp_path / "divisao.json").read_text(encoding="utf-8"))
    assert not set(divisao["treino"]) & set(divisao["controle"])
    assert len(divisao["controle"]) == 2 * 8  # 20% de 40 pares
    for doc in divisao["controle"]:
        assert doc.replace("n1", "n2") in divisao["controle"] or doc.replace("n2", "n1") in divisao["controle"]
