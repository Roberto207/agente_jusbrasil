from __future__ import annotations

from verificador.texto import preparar, voltar_ao_original
from tests.helpers import trecho_gabarito


def test_mapa_reconstrói_os_trechos_do_gabarito(textos, gabarito) -> None:
    for row in gabarito:
        texto = textos[row["documento_id"]]
        inicio = int(row["inicio"])
        fim = int(row["fim"])
        esperado = trecho_gabarito(row["trecho"])
        assert texto[inicio:fim] == esperado
        prep = preparar(texto)
        ini_n = next(i for i, pos in enumerate(prep.mapa) if pos >= inicio)
        fim_n = next(
            (i for i, pos in enumerate(prep.mapa) if pos >= fim),
            len(prep.mapa),
        )
        rec_i, rec_f = voltar_ao_original(prep, ini_n, fim_n)
        assert rec_i <= inicio
        assert rec_f >= fim
        assert prep.original[inicio:fim] == esperado


def test_nenhum_numero_de_cabecalho_vira_corpo(textos, gabarito) -> None:
    for doc_id, texto in textos.items():
        prep = preparar(texto)
        assert 0 <= prep.corpo_inicio <= len(texto)
        for row in gabarito:
            if row["documento_id"] != doc_id:
                continue
            assert int(row["inicio"]) >= prep.corpo_inicio


def test_normalizar_e_voltar_nao_gera_intervalo_invalido(textos) -> None:
    for texto in textos.values():
        prep = preparar(texto)
        assert len(prep.mapa) == len(prep.normalizado)
        if not prep.mapa:
            continue
        ini, fim = voltar_ao_original(prep, 0, len(prep.mapa))
        assert 0 <= ini <= fim <= len(prep.original)


def test_bordas_texto_vazio_e_sem_cabecalho() -> None:
    vazio = preparar("")
    assert vazio.original == ""
    assert vazio.corpo_inicio == 0
    assert vazio.normalizado == ""
    assert vazio.mapa == []

    sem_cab = preparar("Como já se reconheceu no REsp nº 1.234.567/SP, a tese prevalece.")
    assert sem_cab.corpo_inicio == 0
    assert "REsp nº 1.234.567/SP" in sem_cab.normalizado

    colado = preparar("fim do texto REsp 1.111.111/RJ")
    assert colado.normalizado.endswith("REsp 1.111.111/RJ")
