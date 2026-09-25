"""Portas do encoder (ADR-011): ele só acrescenta, e só o que tem forma de citação. Sem torch."""

from __future__ import annotations

from verificador.extracao import extrair
from verificador.texto import preparar


class _EncoderFalso:
    """Devolve os spans dos trechos pedidos, como se o modelo os tivesse marcado."""

    def __init__(self, *marcados: tuple[str, str]) -> None:
        self.marcados = marcados

    def spans(self, texto: str) -> list[tuple[int, int, str]]:
        return [(texto.index(t), texto.index(t) + len(t), r) for t, r in self.marcados]


CORPO = "Decido. Conforme a MS-2735/DF e o art. 5º da CLT, com fls. 23 e a Súmula 83 do STJ, nego."


def _por_origem(texto: str, encoder) -> dict[str, set[str]]:
    saida: dict[str, set[str]] = {}
    for c in extrair(preparar(texto), encoder):
        saida.setdefault(next(iter(c.origem)), set()).add(c.trecho)
    return saida


def test_sem_encoder_so_regex() -> None:
    assert set(_por_origem(CORPO, None)) == {"regex"}


def test_encoder_acrescenta_o_que_o_regex_nao_acha() -> None:
    texto = "Decido. Conforme o Pedido de Uniformização PUIL 1.234/SP, nego."
    enc = _EncoderFalso(("PUIL 1.234/SP", "JUR"))
    # PUIL não é classe conhecida: sem classe, a porta 2 barra.
    assert _por_origem(texto, enc).get("encoder") is None
    texto2 = "Decido. Conforme o Recurso Especial repetitivo 1.234.567, nego."
    enc2 = _EncoderFalso(("Recurso Especial repetitivo 1.234.567", "JUR"))
    assert _por_origem(texto2, enc2)["encoder"] == {"Recurso Especial repetitivo 1.234.567"}


def test_regex_manda_onde_ja_achou() -> None:
    enc = _EncoderFalso(("Súmula 83 do STJ, nego", "JUR"), ("art. 5º", "LEI"))
    por_origem = _por_origem(CORPO, enc)
    assert "encoder" not in por_origem
    assert "Súmula 83 do STJ" in por_origem["regex"]


def test_sem_digito_ou_sem_ancora_e_descartado() -> None:
    enc = _EncoderFalso(("fls. 23", "JUR"), ("Conforme a", "JUR"))
    assert "encoder" not in _por_origem(CORPO, enc)


def test_cabecalho_fica_de_fora() -> None:
    texto = "Processo nº 0001234-56.2024.1.00.0000\n\nRELATÓRIO\n\nDecido. Nada a citar."
    enc = _EncoderFalso(("Processo nº 0001234-56.2024.1.00.0000", "JUR"))
    prep = preparar(texto)
    assert all(c.inicio >= prep.corpo_inicio for c in extrair(prep, enc))


def test_artigo_sem_lei_e_enunciado_administrativo_sao_barrados() -> None:
    texto = "Decido. Vale o ARTIGO 3º, CAPUT e o Enunciado Administrativo 2 do STJ, nego."
    enc = _EncoderFalso(("ARTIGO 3º, CAPUT", "LEI"), ("Enunciado Administrativo 2 do STJ", "JUR"))
    assert "encoder" not in _por_origem(texto, enc)


def test_artigo_com_lei_nomeada_passa() -> None:
    texto = "Decido. Vale o art. 7º da Lei Orgânica do Município, nego."
    enc = _EncoderFalso(("art. 7º da Lei Orgânica do Município", "LEI"))
    assert _por_origem(texto, enc)["encoder"] == {"art. 7º da Lei Orgânica do Município"}
