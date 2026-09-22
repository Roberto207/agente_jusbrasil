"""Correção `m↔rn` contra vocabulário fechado (`tarefas_equipe.md` 3.2, Tier 1).

O ruído `m↔rn` está na página Data do desafio e **não ocorre na amostra**, então estes testes são a
única defesa contra regressão. O risco não é deixar de corrigir — é corrigir demais: `rn→m` cego
transforma `interno` em `intemo`, e `AgInt` é *Agravo **Interno***.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

import pytest

from verificador.extracao import extrair
from verificador.tabelas import chave_ocr, vocabulario_ocr
from verificador.texto import preparar
from verificador.texto.normalizacao import normalizar

# Cada par é (texto com ruído, termo que precisa reaparecer).
REPAROS = [
    ("Súrnula 211 do STJ", "Súmula"),
    ("5úrnula 211 do STJ", "Súmula"),
    ("SÚRNULA 211 DO STJ", "SÚMULA"),
    ("Reclarnação 88.178/RS", "Reclamação"),
    ("Agravo Regirnental", "Regimental"),
    ("Ernbargos de Declaração", "Embargos"),
    ("Agravo de Instrurnento", "Instrumento"),
    ("Rnandado de Segurança", "Mandado"),
    ("Cautelar Inorninada", "Inominada"),
    ("Lei Cornplementar nº 64/1990", "Complementar"),
    ("rninistro Dias Toffoli", "ministro"),
    ("Rel. Rnin. Toffoli", "Min"),
    ("julgado do STRN de 2023", "STM"),
    # sentido inverso: o OCR colou `rn` num `m`
    ("Agravo Intemo", "Interno"),
]

# Palavras que a correção **não pode** tocar. Sobrenomes de relator reais do STF/STJ entram de
# propósito: são o caso em que uma troca cega estragaria a leitura do relator na forma (d).
INTOCAVEIS = [
    "Agravo Interno",
    "interna corporis",
    "Og Fernandes",
    "Alexandre de Moraes",
    "André Mendonça",
    "Cármen Lúcia",
    "Ministro Bernardo",
    "o governo federal",
    "termo inicial",
    "o mérito da causa",
    "prazo moderno",
    "recurso externo",
]


@pytest.mark.parametrize("bruto,esperado", REPAROS)
def test_repara_termo_conhecido(bruto: str, esperado: str) -> None:
    norm, _ = normalizar(bruto)
    assert esperado in norm, f"{bruto!r} não recuperou {esperado!r}: {norm!r}"


@pytest.mark.parametrize("texto", INTOCAVEIS)
def test_nao_toca_no_que_ja_esta_certo(texto: str) -> None:
    norm, _ = normalizar(texto)
    assert norm == texto, f"correção estragou {texto!r} → {norm!r}"


def test_vocabulario_so_tem_palavra_com_m_ou_rn() -> None:
    """Palavra sem `m` nem `rn` no vocabulário é peso morto — nada pode produzi-la."""
    sobrando = [p for p in vocabulario_ocr() if "m" not in p and "rn" not in p]
    assert not sobrando, f"palavras que a correção nunca alcança: {sobrando}"


def test_vocabulario_guarda_interno() -> None:
    """`interno` precisa estar listado: é o termo que a troca cega destruiria (AgInt)."""
    assert chave_ocr("interno") in vocabulario_ocr()


def _tabela(nome: str) -> dict:
    caminho = Path(str(resources.files("verificador.tabelas"))) / nome
    return json.loads(caminho.read_text(encoding="utf-8"))


def _termos_simples(padrao: str) -> list[str]:
    """Palavras de um alias que é texto puro.

    Alias com grupo (`(?:…)`), opcional ou repetição é estrutura de regex, não nome — fica de fora
    para o teste não acusar falso positivo.
    """
    if any(sinal in padrao for sinal in ("(", ")", "?", "*", "+", "|")):
        return []
    limpo = re.sub(r"\[([^\]])[^\]]*\]", r"\1", padrao)
    limpo = re.sub(r"\\s[+*]", " ", limpo)
    limpo = limpo.replace(r"\b", "").replace(r"\.", "")
    return re.findall(r"[A-Za-zÀ-ÿ]{2,}", limpo)


def test_vocabulario_acompanha_as_tabelas_de_extracao() -> None:
    """Toda âncora de extração com `m`/`rn` precisa estar no vocabulário.

    Sem este teste a lista envelhece em silêncio: quem acrescentar uma classe nova em
    `classes.json` não tem como saber que a citação se perde sob ruído `m↔rn`. Foi assim que
    `MS`, `RMS`, `CPM` e `consumidor` ficaram de fora na primeira versão — e só apareceram porque
    o par limpo × ruidoso (R35) quebrou.
    """
    candidatos: set[str] = set()
    for item in _tabela("classes.json")["aliases"]:
        candidatos.add(item["sigla"])
        for padrao in item["padroes"]:
            candidatos.update(_termos_simples(padrao))
    for chave, aliases in _tabela("leis.json").items():
        candidatos.add(chave.split("-")[0])
        for alias in aliases:
            candidatos.update(_termos_simples(alias))

    vocabulario = vocabulario_ocr()
    faltando = sorted(
        termo
        for termo in candidatos
        if ("m" in chave_ocr(termo) or "rn" in chave_ocr(termo))
        and chave_ocr(termo) not in vocabulario
    )
    assert not faltando, (
        f"âncoras com m/rn fora de vocabulario_ocr.json: {faltando}. "
        "Sob ruído m↔rn a citação se perde inteira — acrescente ou justifique."
    )


def test_correcao_preserva_o_mapa_de_offsets() -> None:
    """O trecho extraído continua saindo do texto **original**, com ruído e tudo (R38).

    A troca `rn`→`m` encurta o texto normalizado; se o mapa não acompanhasse, o span voltaria
    deslocado e o `trecho` deixaria de bater com `texto[inicio:fim]`.
    """
    texto = (
        "Trata-se de parecer.\n\n"
        "O caso encontra amparo na Súrnula 211 do STJ e na Reclarnação 88.178/RS, "
        "ambas aplicáveis à espécie."
    )
    preparado = preparar(texto)
    candidatas = extrair(preparado, encoder=None)
    assert candidatas, "nenhuma citação extraída do texto com ruído m↔rn"
    for candidata in candidatas:
        assert candidata.trecho == texto[candidata.inicio : candidata.fim]
        assert 0 <= candidata.inicio < candidata.fim <= len(texto)


def test_ruido_mrn_faz_o_sistema_achar_a_citacao() -> None:
    """Sem a correção, `Súrnula 211` não casaria com nenhum padrão."""
    limpo = "Aplica-se a Súmula 211 do STJ ao caso concreto, sem ressalvas."
    sujo = "Aplica-se a Súrnula 211 do STJ ao caso concreto, sem ressalvas."
    achadas_limpo = extrair(preparar(limpo), encoder=None)
    achadas_sujo = extrair(preparar(sujo), encoder=None)
    assert len(achadas_sujo) == len(achadas_limpo) == 1
    assert achadas_sujo[0].forma == achadas_limpo[0].forma == "sumula"
