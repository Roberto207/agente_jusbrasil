from __future__ import annotations

from verificador.contratos import Candidata
from verificador.extracao import ler_campos


def _cand(trecho: str, forma: str, tipo: str = "jurisprudencia") -> Candidata:
    return Candidata(
        inicio=0,
        fim=len(trecho),
        trecho=trecho,
        tipo=tipo,  # type: ignore[arg-type]
        forma=forma,  # type: ignore[arg-type]
        padrao=forma,
        origem=frozenset({"regex"}),
    )


def test_r36_artigo_igual_com_e_sem_inciso() -> None:
    com = ler_campos(_cand("art. 12, III, da Constituição Federal", "lei_artigo", "lei"))
    sem = ler_campos(_cand("art. 12 da Constituição Federal", "lei_artigo", "lei"))
    assert com is not None and sem is not None
    assert com.artigo == sem.artigo == "12"
    assert com.lei_chave == sem.lei_chave == "CF-1988"


def test_lei_com_paragrafo_ignora_complemento() -> None:
    campos = ler_campos(_cand("art. 20, § 1º-A, da CLT", "lei_artigo", "lei"))
    assert campos is not None
    assert campos.artigo == "20"
    assert campos.lei_chave == "DL-5452-1943"


def test_com_numero_le_cadeia_e_uf() -> None:
    campos = ler_campos(_cand("AgInt no AREsp nº 1.111.222/GO", "com_numero"))
    assert campos is not None
    assert campos.classe_principal == "AREsp"
    assert campos.cadeia_recursos == ("AgInt",)
    assert campos.numero == "1111222"
    assert campos.uf == "GO"


def test_sumula_vinculante_usa_prefixo_sv() -> None:
    campos = ler_campos(_cand("Súmula Vinculante 10", "sumula"))
    assert campos is not None
    assert campos.numero == "SV10"
    campos2 = ler_campos(_cand("Súmula 83 do STJ", "sumula"))
    assert campos2 is not None
    assert campos2.numero == "S83"
    assert campos2.tribunal == "STJ"


def test_sem_numero_exige_ano_e_relator() -> None:
    campos = ler_campos(
        _cand("julgado do STF proferido em 2024 pela relatoria de Relator Exemplo", "sem_numero")
    )
    assert campos is not None
    assert campos.tribunal == "STF"
    assert campos.ano == 2024
    assert campos.relator == "relator exemplo"
    assert ler_campos(_cand("julgado do STF sem mais dados", "sem_numero")) is None


def test_ocr_marca_correcao_no_numero() -> None:
    campos = ler_campos(_cand("AgInt no RESP 21737l8 - SP", "com_numero"))
    assert campos is not None
    assert campos.numero == "2173718"
    assert campos.correcao_ocr is True
