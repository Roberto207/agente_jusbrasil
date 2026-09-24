"""Treino do encoder: rótulos BIO, janelas, conversão do LeNER-Br e higiene das divisões."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from verificador.treino import bio, lener
from verificador.treino.dataset import DIVISAO_DE_TREINO, divisao_da_amostra, montar

RAIZ = Path(__file__).resolve().parents[1]
PASTA_LENER = RAIZ / "lener-br" / "leNER-Br"
PASTA_SINTETICO = RAIZ / "sintetico_hf"
PASTA_AMOSTRA = RAIZ / "desafio-jusbrasil-bracis-2026"


def _offsets(texto: str) -> list[tuple[int, int]]:
    """Tokenizador de brinquedo: palavras e pontuação, como o pré-tokenizador do BERT."""
    return [m.span() for m in re.finditer(r"\w+|[^\w\s]", texto)]


# --- bio ------------------------------------------------------------------------------------------

def test_rotular_e_decodificar_ida_e_volta() -> None:
    texto = "Conforme o REsp 1.234/SP e o art. 5º da CF, nego."
    spans = []
    for trecho, rotulo in (("REsp 1.234/SP", "JUR"), ("art. 5º da CF", "LEI")):
        inicio = texto.index(trecho)
        spans.append((inicio, inicio + len(trecho), rotulo))
    off = _offsets(texto)
    assert bio.decodificar(off, bio.rotular(off, spans)) == spans


def test_rotular_marca_b_no_primeiro_token_e_i_nos_seguintes() -> None:
    texto = "ver REsp 12 hoje"
    off = _offsets(texto)
    rot = [bio.ROTULOS[r] for r in bio.rotular(off, [(4, 11, "JUR")])]
    assert rot == ["O", "B-JUR", "I-JUR", "O"]


def test_spans_colados_do_mesmo_tipo_nao_se_fundem() -> None:
    texto = "HC 1 HC 2"
    off = _offsets(texto)
    rot = bio.rotular(off, [(0, 4, "JUR"), (5, 9, "JUR")])
    assert bio.decodificar(off, rot) == [(0, 4, "JUR"), (5, 9, "JUR")]


def test_ignorados_e_tokens_especiais_ficam_fora_da_perda() -> None:
    off = [(0, 0), (0, 3), (4, 7), (0, 0)]
    rot = bio.rotular(off, [], ignorar=[(4, 7)])
    assert rot == [bio.IGNORAR, bio.ID_ROTULO["O"], bio.IGNORAR, bio.IGNORAR]


def test_i_sem_b_abre_span_novo_na_decodificacao() -> None:
    off = [(0, 2), (3, 5)]
    assert bio.decodificar(off, [bio.ID_ROTULO["I-JUR"], bio.ID_ROTULO["I-JUR"]]) == [(0, 5, "JUR")]


@pytest.mark.parametrize("n", [1, 509, 510, 511, 900, 5000])
def test_janelas_cobrem_tudo_e_dono_e_o_mais_central(n: int) -> None:
    cortes = bio.janelas(n)
    assert all(f - i <= bio.TAMANHO_JANELA for i, f in cortes)
    assert cortes[0][0] == 0 and cortes[-1][1] == n
    for (_, fim_a), (ini_b, _) in zip(cortes, cortes[1:]):
        assert fim_a - ini_b >= bio.SOBREPOSICAO  # sobreposição mínima entre vizinhas
    donos = bio.dono_por_token(n, cortes)
    assert all(cortes[d][0] <= t < cortes[d][1] for t, d in enumerate(donos))


# --- lener (sem precisar do dataset) --------------------------------------------------------------

@pytest.mark.parametrize(
    ("trecho", "titulo", "esperado"),
    [
        ("HC 110260 / SP", "Habeas Corpus 110.260 São Paulo", True),
        ("TST-RR-47-48.2014.5.23.0056", "RR - 47-48.2014.5.23.0056", True),
        ("Súmula 7 do STJ", "AgRg no RECURSO ESPECIAL Nº 971.113 - SP", False),
        ("ADI 3767 / PR", "", False),
    ],
)
def test_numero_proprio(trecho: str, titulo: str, esperado: bool) -> None:
    assert lener.numero_proprio(trecho, titulo) is esperado


@pytest.mark.parametrize(
    ("trecho", "esperado"),
    [
        ("art. 896, § 1º-A, da CLT", "citacao"),
        ("ARTIGO 467 DA CLT", "citacao"),
        ("Constituição Federal", "ambigua"),
        ("CPC/1973", "ambigua"),
    ],
)
def test_rotulo_legislacao(trecho: str, esperado: str) -> None:
    assert lener.rotulo_legislacao(trecho, lener.EntidadeLeNER(0, len(trecho), "LEGISLACAO")) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("conforme o REsp 1.234.567/SP do STJ, nego", "citacao"),
        ("Acórdão 1160/2016 do TCU", "fora"),
        ("Súmula 503 do Superior Tribunal de Justiça", "ambigua"),
        ("conforme o STF", "ambigua"),
    ],
)
def test_rotulo_jurisprudencia(texto: str, esperado: str) -> None:
    e = lener.EntidadeLeNER(0, len(texto), "JURISPRUDENCIA")
    if esperado == "citacao":
        e = lener.EntidadeLeNER(texto.index("REsp"), texto.index(" do STJ"), "JURISPRUDENCIA")
    assert lener.rotulo_jurisprudencia(texto, e, titulo_documento="") == esperado


# --- com os dados locais --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pasta_lener() -> Path:
    if not (PASTA_LENER / "raw_text").is_dir():
        pytest.skip("LeNER-Br ausente — `git clone https://github.com/peluz/lener-br.git lener-br`")
    return PASTA_LENER


def test_regua_do_protocolo_tem_as_contagens_registradas(pasta_lener: Path) -> None:
    """A régua do go/no-go é fixa: 352 / 35 / 74 citações no escopo (`tarefas_equipe.md`, Fase 4)."""
    for split, esperado in (("train", 352), ("dev", 35), ("test", 74)):
        total = 0
        for nome in lener.documentos(pasta_lener, splits=(split,)):
            raw, ents = lener.documento(pasta_lener, nome)
            total += sum(lener.no_escopo(raw, e) for e in ents)
        assert total == esperado, split


@pytest.fixture(scope="module")
def dataset(pasta_lener: Path):
    if not (PASTA_SINTETICO / "base" / "txt").is_dir() or not (PASTA_AMOSTRA / "txt").is_dir():
        pytest.skip("precisa de sintetico_hf/ (snapshot do HF na revisão fixa) e da amostra do desafio")
    return montar(PASTA_SINTETICO, PASTA_AMOSTRA, pasta_lener)


def test_nada_de_controle_dev_ou_test_no_treino(dataset) -> None:
    exemplos, _ = dataset
    controle_amostra = {d for d, lado in divisao_da_amostra().items() if lado == "controle"}
    test_lener = set(lener.documentos(PASTA_LENER, splits=("test",)))
    for ex in exemplos:
        assert not (ex.fonte == "lener" and ex.documento in test_lener), "test do LeNER-Br não pode nem ser lido"
        if ex.divisao == DIVISAO_DE_TREINO:
            assert not (ex.fonte == "amostra" and ex.documento in controle_amostra)


def test_pares_do_sintetico_ficam_do_mesmo_lado(dataset) -> None:
    exemplos, _ = dataset
    lado = {(ex.fonte, ex.documento): ex.divisao for ex in exemplos if ex.fonte.startswith("sintetico")}
    for (fonte, doc), divisao in lado.items():
        if "_n1_" in doc:
            assert lado[(fonte, doc.replace("_n1_", "_n2_"))] == divisao


def test_amostra_entra_inteira_com_os_192_trechos(dataset) -> None:
    exemplos, _ = dataset
    assert sum(len(ex.spans) for ex in exemplos if ex.fonte == "amostra") == 192
