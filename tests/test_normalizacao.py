"""Confere cada regra de `normalizar` (ADR-003) e o mapa de offsets."""

from __future__ import annotations

from verificador.texto.normalizacao import normalizar, voltar_ao_original


def _achar(normalizado: str, trecho: str) -> tuple[int, int]:
    ini = normalizado.index(trecho)
    return ini, ini + len(trecho)


def test_quebra_de_linha_vira_espaco() -> None:
    norm, _ = normalizar("REsp\n1.234.567/SP")
    assert norm == "REsp 1.234.567/SP"


def test_n_grau_no_e_n_ponto_viram_numero() -> None:
    for bruto in ("n° 9.888.777", "No 9.888.777", "n. 9.888.777", "N. 9.888.777"):
        norm, _ = normalizar(bruto)
        assert norm.startswith("nº 9.888.777"), bruto


def test_nao_converte_preposicao_no() -> None:
    norm, _ = normalizar("AgInt no AREsp nº 1.111.222/GO")
    assert "AgInt no AREsp" in norm
    assert norm.count("nº") == 1


def test_travessao_vira_hifen() -> None:
    norm, _ = normalizar("REsp 1.111.222 – GO")
    assert "REsp 1.111.222-GO" == norm


def test_espaco_dentro_de_numero_e_colapsado() -> None:
    norm, _ = normalizar("RE nº 5. 230.808-DF")
    assert "5.230.808" in norm
    assert "5. 230" not in norm


def test_letra_so_vira_digito_dentro_de_numero() -> None:
    norm, _ = normalizar("AgInt no RESP 21737l8 - SP e a Súmula 83")
    assert "2173718" in norm
    assert "Súmula" in norm
    assert "5úmula" not in norm


def test_letra_no_primeiro_digito_do_grupo() -> None:
    """Causa 4: OCR no 1º dígito de um grupo (art. l.239, I.003, g.324)."""
    for bruto, esperado in (
        ("art. l.239", "art. 1.239"),
        ("artigo I.003", "artigo 1.003"),
        ("REsp nº g.324.784", "REsp nº 9.324.784"),
    ):
        norm, _ = normalizar(bruto)
        assert esperado in norm, (bruto, norm)


def test_letra_e_espaco_dentro_do_numero() -> None:
    """Causa 4: letra + espaço no número — OCR antes de colapsar o espaço."""
    norm, _ = normalizar("Rcl n. 7I. 346/SP")
    assert "71.346" in norm
    assert "71. 346" not in norm

    norm, _ = normalizar("art. 1. o21")
    assert "1.021" in norm
    assert "1. 021" not in norm


def test_ocr_nao_corrompe_uf_apos_hifen() -> None:
    norm, _ = normalizar("AgInt no RESP 21737l8 - SP e a Súmula 83")
    assert "2173718" in norm
    assert "-SP" in norm or " SP" in norm
    assert "5P" not in norm


def test_cinco_umula_vira_sumula() -> None:
    norm, _ = normalizar("5úmula 211 do STJ")
    assert norm.startswith("Súmula 211")


def test_nao_aplica_ocr_em_palavra_comum() -> None:
    norm, _ = normalizar("já se reconheceu no mérito")
    assert "se reconheceu" in norm
    assert "5e reconheceu" not in norm


def test_mapa_devolve_o_trecho_original_apos_ocr() -> None:
    original = "Como no AgInt no RESP 21737l8 - SP ficou assentado."
    norm, mapa = normalizar(original)
    ini_n, fim_n = _achar(norm, "2173718")
    ini, fim = voltar_ao_original(original, mapa, ini_n, fim_n)
    assert original[ini:fim] == "21737l8"


def test_mapa_devolve_o_trecho_original_com_quebra() -> None:
    original = "APL nº\n7000449-40.2023.7.00.0000/RS"
    norm, mapa = normalizar(original)
    ini_n, fim_n = _achar(norm, "APL nº 7000449-40.2023.7.00.0000/RS")
    ini, fim = voltar_ao_original(original, mapa, ini_n, fim_n)
    assert original[ini:fim] == original
    assert "\n" in original[ini:fim]


def test_mapa_tem_um_indice_por_caractere_normalizado() -> None:
    original = "RE nº 5. 230.808-DF"
    norm, mapa = normalizar(original)
    assert len(mapa) == len(norm)
    assert all(0 <= pos < len(original) for pos in mapa)
