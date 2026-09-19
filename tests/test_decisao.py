"""Frente D — decisão. Índice falso: nada aqui depende da base real nem da amostra."""

from __future__ import annotations

import random

import pytest

from verificador.base.indice import Indice
from verificador.contratos import Campos, RegistroIndice
from verificador.decisao import CAMINHOS_DECISAO, CLASSE_DO_CAMINHO, decidir, numero_do_llm_valido


def reg(id_, numero=None, *, tribunal="STJ", classe="REsp", cadeia=(), uf="PR", natureza="acordao", lei=None, artigo=None):
    return RegistroIndice(
        id=id_, natureza=natureza, tribunal=tribunal, numero=numero, classe_principal=classe,
        cadeia_recursos=tuple(cadeia), uf=uf, ano=2020, relator=None, lei_chave=lei, artigo=artigo,
    )


def campos(**kw) -> Campos:
    base = dict(
        tribunal=None, classe_principal=None, cadeia_recursos=(), numero=None, uf=None, ano=None,
        relator=None, lei_chave=None, artigo=None, correcao_ocr=False, fonte="regras",
    )
    base.update(kw)
    return Campos(**base)


@pytest.fixture()
def indice() -> Indice:
    return Indice(
        [
            reg("1", "1741784", classe="REsp"),  # processo com um só registro
            reg("2", "500", classe="REsp"),  # REsp original ...
            reg("3", "500", classe="REsp", cadeia=("AgInt",)),  # ... e o agravo interno sobre ele
            reg("4", "777", classe="HC", uf="SP"),
            reg("5", "S83", tribunal="STJ", classe=None, uf=None, natureza="sumula"),
            reg("6", "SV10", tribunal="STF", classe=None, uf=None, natureza="sumula"),
            reg("7", None, tribunal=None, classe=None, uf=None, natureza="dispositivo", lei="LEI-13105-2015", artigo="373"),
            reg("8", None, tribunal=None, classe=None, uf=None, natureza="dispositivo", lei="DL-5452-1943", artigo="818"),
            reg("9", None, tribunal=None, classe=None, uf=None, natureza="dispositivo", lei="DL-5452-1943", artigo="818"),
            reg("10", "1234", classe="AI", uf="MG"),  # número curto, que um "Tema 1234" não pode casar
        ]
    )


CASOS = [
    # (nome do caminho, forma, campos, classe, id)
    ("sem_numero", "sem_numero", campos(tribunal="STF", ano=2024, relator="x"), "incompleta", None),
    ("numero_ausente", "com_numero", campos(numero="999999", classe_principal="REsp"), "inventada", None),
    ("numero_contradito", "com_numero", campos(numero="1741784", classe_principal="HC"), "inventada", None),
    ("numero_unico", "com_numero", campos(numero="1741784", classe_principal="REsp", uf="PR"), "real", "1"),
    ("numero_desempatado", "com_numero", campos(numero="500", classe_principal="REsp", cadeia_recursos=("AgInt",)), "real", "3"),
    ("numero_ambiguo", "com_numero", campos(numero="500", classe_principal="REsp"), "incompleta", None),
    ("lei_apelido_desconhecido", "lei_artigo", campos(artigo="5"), "inventada", None),
    ("lei_ausente", "lei_artigo", campos(lei_chave="LEI-13105-2015", artigo="1134"), "inventada", None),
    ("lei_unica", "lei_artigo", campos(lei_chave="LEI-13105-2015", artigo="373"), "real", "7"),
    ("lei_ambigua", "lei_artigo", campos(lei_chave="DL-5452-1943", artigo="818"), "incompleta", None),
]


@pytest.mark.parametrize("caminho, forma, c, classe, id_", CASOS, ids=[x[0] for x in CASOS])
def test_um_teste_por_caminho(indice, caminho, forma, c, classe, id_) -> None:
    r = decidir(c, forma, indice)
    assert (r.caminho, r.classificacao, r.id_canonico) == (caminho, classe, id_)
    assert r.confianca is None
    assert CLASSE_DO_CAMINHO[caminho] == classe


def test_a_tabela_tem_exatamente_os_dez_caminhos_do_design() -> None:
    assert set(CAMINHOS_DECISAO) == {x[0] for x in CASOS} and len(CAMINHOS_DECISAO) == 10


def test_contradicao_por_uf_e_por_tribunal(indice) -> None:
    assert decidir(campos(numero="777", classe_principal="HC", uf="RJ"), "com_numero", indice).caminho == "numero_contradito"
    assert decidir(campos(numero="S83", tribunal="STF"), "sumula", indice).caminho == "numero_contradito"


def test_atributo_ausente_nunca_elimina(indice) -> None:
    r = decidir(campos(numero="777", classe_principal="HC"), "com_numero", indice)  # sem UF na citação
    assert r.classificacao == "real" and r.id_canonico == "4"


def test_cadeia_presente_precisa_bater(indice) -> None:
    r = decidir(campos(numero="500", classe_principal="REsp", cadeia_recursos=("EDcl",)), "com_numero", indice)
    assert r.caminho == "numero_contradito"


def test_tema_de_repercussao_nao_casa_com_processo_de_numero_curto(indice) -> None:
    """B lê o tema como número sem classe; o registro 1234 (um AI) existe, mas não pode ser resolvido."""
    r = decidir(campos(numero="1234"), "com_numero", indice)
    assert (r.classificacao, r.caminho) == ("inventada", "numero_ausente")


def test_sumula_com_zero_a_esquerda_e_vinculante(indice) -> None:
    assert decidir(campos(numero="S083", tribunal="STJ"), "sumula", indice).id_canonico == "5"
    assert decidir(campos(numero="SV10"), "sumula", indice).id_canonico == "6"
    assert decidir(campos(numero="S999"), "sumula", indice).caminho == "numero_ausente"


def test_r36_inciso_e_paragrafo_nao_mudam_a_resposta(indice) -> None:
    """B tira inciso/§ de `artigo` (R36); a decisão só vê lei e artigo."""
    a = decidir(campos(lei_chave="LEI-13105-2015", artigo="373"), "lei_artigo", indice)
    assert (a.classificacao, a.id_canonico) == ("real", "7")


def test_id_so_em_real_e_r12_r13_r14(indice) -> None:
    for _, forma, c, _, _ in CASOS:
        r = decidir(c, forma, indice)
        assert (r.id_canonico is not None) == (r.classificacao == "real")
        if r.classificacao == "real":
            registro = next(x for x in indice.registros if x.id == r.id_canonico)
            if forma == "lei_artigo":
                assert (registro.lei_chave, registro.artigo) == (c.lei_chave, c.artigo)
            else:
                assert registro.numero == c.numero


def test_resposta_nao_depende_da_ordem_do_indice(indice) -> None:
    esperado = [decidir(c, f, indice) for _, f, c, _, _ in CASOS]
    for semente in range(5):
        registros = list(indice.registros)
        random.Random(semente).shuffle(registros)
        embaralhado = Indice(registros)
        assert [decidir(c, f, embaralhado) for _, f, c, _, _ in CASOS] == esperado


def test_numero_emprestado_nunca_vira_real() -> None:
    """τ = 0: número que existe, citado com classe ou UF diferentes de todos os registros."""
    registros = [reg(str(i), str(1000 + i), classe="REsp", uf="PR") for i in range(50)]
    indice = Indice(registros)
    for r in registros:
        for outra_classe, outra_uf in (("HC", "PR"), ("REsp", "SP"), ("RE", "RJ")):
            res = decidir(campos(numero=r.numero, classe_principal=outra_classe, uf=outra_uf), "com_numero", indice)
            assert res.classificacao == "inventada" and res.caminho == "numero_contradito"


# -- R48 -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "numero, trecho, esperado",
    [
        ("2173718", "AgInt no RESP 21737l8 - SP", True),  # `l` → 1, troca da tabela
        ("2173719", "AgInt no RESP 21737l8 - SP", False),  # dígito que o trecho não tem
        ("1741784", "REsp nº 1.741.784/PR", True),
        ("1741785", "REsp nº 1.741.784/PR", False),
        ("05", "Vistos nos autos", False),  # `nos` não vira número: sem dígito de verdade
        ("", "REsp 123", False),
    ],
)
def test_r48_so_aceita_digitos_que_saem_do_trecho(numero, trecho, esperado) -> None:
    assert numero_do_llm_valido(numero, trecho) is esperado
