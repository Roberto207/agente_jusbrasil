from __future__ import annotations

import pytest

from verificador.contratos import Candidata
from verificador.extracao import ler_campos
from verificador.extracao.campos import normalizar_relator


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
    campos2 = ler_campos(_cand("Súmula n. 83 do STJ", "sumula"))
    assert campos2 is not None
    assert campos2.numero == "S83"
    assert campos2.tribunal == "STJ"


def test_relator_lido_sem_depender_da_conjuncao() -> None:
    """ADR-015: `_RELATOR` também ancora no marcador, não em `relatoria de|rel. min.`.

    Se voltar a enumerar, a citação é extraída mas o relator some e o caminho de decisão cai em
    `campos_nao_lidos` — o que muda o rastro que alimenta a tabela de confiança.
    """
    casos = (
        ("decisão colegiada do STM em 2025, relatada pelo Ministro Cilene Ferreira", "cilene ferreira"),
        ("julgado da Corte (TSE, 2015, Min. Jorge Mussi)", "jorge mussi"),
        ("Reclamação do STF, de 2020, Rel. Min. Celso De Mello", "celso de mello"),
        ("julgado do STF proferido em 2024 pela relatoria de Dias Toffoli", "dias toffoli"),
    )
    for trecho, esperado in casos:
        campos = ler_campos(_cand(trecho, "sem_numero"))
        assert campos is not None, trecho
        assert campos.relator == esperado, trecho


def test_titulo_normalizado_igual_nos_dois_lados() -> None:
    """A citação diz `Ministro X` e o registro diz `MINISTRA X`: sem a mesma lista de títulos nos
    dois normalizadores, os dois lados nunca se encontram."""
    from verificador.base.atributos import normalizar_relator as do_registro

    assert normalizar_relator("Ministro Celso De Mello") == do_registro("MINISTRO CELSO DE MELLO")
    assert normalizar_relator("Min. Rosa Weber") == do_registro("MINISTRA ROSA WEBER")


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


def _extrair_campos(texto: str, forma: str = "com_numero"):
    from verificador.extracao import extrair
    from verificador.texto import preparar

    candidatas = [c for c in extrair(preparar(texto)) if c.forma == forma]
    assert candidatas, f"nada extraído de {texto!r}"
    return candidatas[0], ler_campos(candidatas[0])


def test_tst_le_classe_e_cadeia_de_qualquer_recurso_conhecido() -> None:
    casos = {
        "TST-AIRR-74240-33.2006.5.04.0027": ("AIRR", ()),
        "TST-RRAG-10241-50.2016.5.03.0103": ("RRAG", ()),
        "TST-AgRg-AIRR-509-06.2012.5.05.0014": ("AIRR", ("AgRg",)),
        "TST-AgInt-RR-1234-56.2019.5.02.0001": ("RR", ("AgInt",)),
        "TST-EDcl-E-EDcl-RR-3400-05.2011.5.21.0009": ("RR", ("EDcl", "E", "EDcl")),
        "TST-AgARR-25823-78.2015.5.24.0091": ("ARR", ("AgRg",)),
        "ARR-213-85.2010.5.02.0030": ("ARR", ()),
    }
    for citacao, (principal, cadeia) in casos.items():
        candidata, campos = _extrair_campos(f"Cf. {citacao}, que decide.")
        assert campos is not None, citacao
        assert candidata.trecho == citacao, "o span não pode começar no meio da sigla"
        assert (campos.tribunal, campos.classe_principal, campos.cadeia_recursos) == (
            "TST",
            principal,
            cadeia,
        ), citacao


def test_tst_nunca_leva_uf() -> None:
    _, campos = _extrair_campos("Cf. TST-RR-1234-56.2019.5.02.0001, que decide.")
    assert campos is not None and campos.uf is None


def test_uf_so_vale_logo_depois_do_numero() -> None:
    _, campos = _extrair_campos("Cf. AgInt no REsp nº 1.234.567/SP, que decide.")
    assert campos is not None and campos.uf == "SP"
    _, sem_uf = _extrair_campos("Cf. AgRg-REspe nº 0600316-49.2020.6.16.0000, que decide.")
    assert sem_uf is not None and sem_uf.uf is None


def test_sigla_eleitoral_e_edcl_tem_o_mesmo_nome_do_indice() -> None:
    _, campos = _extrair_campos("Cf. ED no AgR no AREspEl 0601514-91.2020.6.05.0000, que decide.")
    assert campos is not None
    assert campos.classe_principal == "AREsp"
    assert campos.cadeia_recursos == ("EDcl", "AgRg")


def test_prefixo_desconhecido_nao_vira_processo_do_tst() -> None:
    from verificador.extracao import extrair
    from verificador.texto import preparar

    texto = "Autos PJe-1234567-89.2020.8.26.0100 e TJSP-0001234-56.2020.8.26.0100."
    assert [c for c in extrair(preparar(texto)) if c.forma == "com_numero"] == []


def test_tema_de_repercussao_geral_e_citacao_sem_classe() -> None:
    """O gabarito trata o tema como citação (a base não tem temas): sem classe nem tribunal."""
    _, campos = _extrair_campos("Nos termos do Tema 2.680 da repercussão geral, decide-se.")
    assert campos is not None
    assert campos.numero == "2680"
    assert campos.classe_principal is None and campos.tribunal is None


def test_tabela_tst_e_a_mesma_dos_dois_lados() -> None:
    from verificador.tabelas import tst_sigla

    assert tst_sigla("EDcl") == tst_sigla("ed") == ("EDcl",)
    assert tst_sigla("AgARR") == ("AgRg", "ARR")
    assert tst_sigla("Inedita") == ("INEDITA",)


def test_numero_com_letra_nao_quebra() -> None:
    from verificador.extracao.campos import _numero_com_ocr

    assert _numero_com_ocr("x", "21737l8") == "2173718"


def test_uf_igual_a_sigla_de_classe_nao_vira_classe() -> None:
    """UF depois do número não pode ser lida como classe (`/RO`, `/MS`, `/AC`…)."""
    for uf in ("RO", "RR", "MS", "AC", "AP"):
        _, campos = _extrair_campos(f"Cf. Agravo Regimental no Rcl n° 60.681/{uf}, que decide.")
        assert campos is not None
        assert (campos.classe_principal, campos.cadeia_recursos, campos.uf) == ("Rcl", ("AgRg",), uf)


def test_sigla_de_classe_antes_do_numero_e_lida() -> None:
    """Causa 3.1-b.2: a amostra sintético cita `EIN nº …` só pela sigla."""
    _, campos = _extrair_campos("Cf. EIN nº 7000123-45.2022.7.00.0000, que decide.")
    assert campos is not None and campos.classe_principal == "EIN"
    _, ms = _extrair_campos("Cf. MS nº 1.234.567/PE, que decide.")
    assert ms is not None and ms.classe_principal == "MS" and ms.uf == "PE"


def test_no_dentro_de_palavra_nao_e_o_n_do_numero() -> None:
    """`Agravo Interno 7000249-04…`: o `no` de "Interno" não pode cortar a classe ao meio."""
    _, campos = _extrair_campos("Cf. Agravo Interno 7000249-04.2021.7.00.0000, que decide.")
    assert campos is not None and campos.classe_principal == "AgInt"


def test_edv_nao_entra_na_cadeia_por_prosa() -> None:
    """`divergência em` no meio da frase não pode virar classe: a cadeia lida seria `['EDv','REsp']`
    e o filtro de consistência rejeitaria o registro certo, transformando uma `real` em `inventada`."""
    campos = ler_campos(_cand("havendo divergência em torno do REsp 1.234.567", "com_numero"))
    assert campos is not None
    assert "EDv" not in campos.cadeia_recursos and campos.classe_principal != "EDv"


def test_edv_legitimo_entra_na_cadeia() -> None:
    campos = ler_campos(_cand("AgInt nos EMBARGOS DE DIVERGÊNCIA EM RESP Nº 1597443 - PR", "com_numero"))
    assert campos is not None
    assert "EDv" in campos.cadeia_recursos




@pytest.mark.parametrize(
    ("trecho", "tribunal"),
    [
        ("Súmula nº 12 do colendo Superior Tribunal de Justiça", "STJ"),
        ("Súmula 45 do Superior Tribunal Militar", "STM"),
        ("enunciado nº 606 da Súmula do Supremo Tribunal Federal", "STF"),
        ("Súmula nº 202, item II, do Tribunal Superior do Trabalho", "TST"),
        ("Súmula 9 do Tribunal Superior Eleitoral", "TSE"),
        ("verbete sumular 33 deste Tribunal Superior", None),
    ],
)
def test_sumula_le_tribunal_por_extenso(trecho: str, tribunal: str | None) -> None:
    campos = ler_campos(_cand(trecho, "sumula"))
    assert campos is not None and campos.tribunal == tribunal


def test_sumulas_no_plural_leem_o_primeiro_numero() -> None:
    campos = ler_campos(_cand("Súmulas nºs 110 e 220 do TST", "sumula"))
    assert campos is not None and campos.numero == "S110" and campos.tribunal == "TST"


def test_orientacao_jurisprudencial_nao_vira_sumula() -> None:
    """`OJ 150` não pode casar com a Súmula 150: o número tem outro prefixo e o tribunal é o TST."""
    for trecho in ("Orientação Jurisprudencial nº 150 da SBDI-1", "OJ 150/SDI-1/TST"):
        campos = ler_campos(_cand(trecho, "sumula"))
        assert campos is not None and campos.numero == "OJ150" and campos.tribunal == "TST"


def test_classes_de_controle_concentrado_e_are() -> None:
    for trecho, classe in (("ADPF 101", "ADPF"), ("ARE 1.234.567", "ARE"), ("AgRg nos EREsp 1.111.222/PR", "EREsp")):
        campos = ler_campos(_cand(trecho, "com_numero"))
        assert campos is not None and campos.classe_principal == classe
