"""Frente A — índice da base canônica.

Critério de pronto (`tarefas_equipe.md`): os 96 `real` do gabarito resolvem para
o `id_canonico` certo e nenhum registro pega número de precedente (ADR-002).

Nenhum `id_canonico` ou trecho da amostra aparece como literal (R43): tudo é
lido do `goldenset_offsets.csv` e dos `.txt`.
"""

from __future__ import annotations

import sqlite3

import pytest

from verificador.base import construir_indice
from verificador.base.numero_proprio import numero_proprio, so_digitos
from verificador.contratos import Candidata
from verificador.extracao.campos import ler_campos
from verificador.tabelas import classes, ocr, resolver_lei, resolver_uf, ufs


@pytest.fixture(scope="module")
def indice(pasta_dados):
    return construir_indice(pasta_dados / "desafio1_bracis.db")


@pytest.fixture(scope="module")
def reais(gabarito):
    return [linha for linha in gabarito if linha["classificacao"] == "real"]


def _ids_esperados(linha: dict[str, str]) -> set[str]:
    """O gabarito aceita vários ids por citação; basta acertar um."""
    bruto = linha["id_canonico"].replace(";", ",")
    return {parte.strip() for parte in bruto.split(",") if parte.strip()}


def _forma(linha: dict[str, str], trecho: str) -> str:
    if linha["tipo"] == "lei":
        return "lei_artigo"
    return "sumula" if "mula" in trecho.lower() else "com_numero"


def _resolver(indice, linha: dict[str, str], trecho: str) -> set[str]:
    """Roda citação → campos → consulta ao índice, como a frente D fará."""
    candidata = Candidata(
        inicio=int(linha["inicio"]),
        fim=int(linha["fim"]),
        trecho=trecho,
        tipo=linha["tipo"],  # type: ignore[arg-type]
        forma=_forma(linha, trecho),  # type: ignore[arg-type]
        padrao="gabarito",
        origem=frozenset({"regex"}),
    )
    campos = ler_campos(candidata)
    if campos is None:
        return set()
    if campos.numero:
        return {r.id for r in indice.por_numero(campos.numero)}
    if campos.lei_chave and campos.artigo:
        return {r.id for r in indice.por_lei_artigo(campos.lei_chave, campos.artigo)}
    return set()


# -- o índice em si ---------------------------------------------------------


def test_indice_cobre_a_base_inteira(indice, pasta_dados) -> None:
    with sqlite3.connect(pasta_dados / "desafio1_bracis.db") as conn:
        (total,) = conn.execute("SELECT COUNT(*) FROM documentos").fetchone()
    assert len(indice) == total


def test_quase_todo_registro_tem_identificacao(indice) -> None:
    """Zero registro sem número, salvo os que legitimamente não têm.

    Único caso na base: um extrato de ata do STM cujo cabeçalho não traz número
    de processo. Nenhum id cobrado pelo gabarito depende dele.
    """
    sem_id = indice.sem_numero()
    assert len(sem_id) <= 1, [r.id for r in sem_id]


def test_numero_proprio_nao_vem_de_precedente(indice) -> None:
    """ADR-002: um número não pode ser herdado de um precedente citado.

    Quando dezenas de registros compartilham o mesmo número, o parser está
    pegando o processo que todos citam, não o de cada um. Recursos internos
    legítimos do mesmo processo são poucos por número.
    """
    repetidos = indice.numeros_repetidos()
    assert repetidos, "a base tem recursos internos; zero repetição indica parser quebrado"
    numero, maior = max(repetidos.items(), key=lambda item: item[1])
    assert maior <= 6, f"{numero} aparece em {maior} registros — provável número de precedente"


def test_numero_do_registro_esta_no_cabecalho(indice, pasta_dados) -> None:
    """O número escolhido aparece na abertura do próprio registro.

    Vale para as fontes cujo número fica no cabeçalho; o TST identifica o
    processo no rodapé e por isso fica fora desta checagem.
    """
    with sqlite3.connect(pasta_dados / "desafio1_bracis.db") as conn:
        conn.text_factory = lambda b: b.decode("utf-8", errors="replace")
        textos = dict(conn.execute("SELECT id, texto FROM documentos"))

    for registro in indice.registros:
        if registro.natureza != "acordao" or registro.tribunal == "TST":
            continue
        if not registro.numero:
            continue
        cabecalho = so_digitos(textos[int(registro.id)][:400])
        assert registro.numero in cabecalho, f"{registro.id}: número fora do cabeçalho"


# -- critério de pronto da frente A -----------------------------------------


def test_todas_as_reais_do_gabarito_resolvem(indice, reais, textos) -> None:
    """Os 96 `real` encontram seu `id_canonico` pelo número (ou lei + artigo)."""
    falhas: list[str] = []
    for linha in reais:
        texto = textos[linha["documento_id"]]
        trecho = texto[int(linha["inicio"]) : int(linha["fim"])]
        if not _resolver(indice, linha, trecho) & _ids_esperados(linha):
            falhas.append(trecho[:60])
    assert not falhas, f"{len(falhas)} de {len(reais)} não resolveram: {falhas[:5]}"


def test_inventadas_de_jurisprudencia_nao_acham_registro(indice, gabarito, textos) -> None:
    """Citação inventada não pode encontrar candidato pelo número (ADR-002).

    É o teste que prova que o índice não cai na armadilha do número citado
    dentro do texto de outro acórdão.
    """
    vazadas: list[str] = []
    for linha in gabarito:
        if linha["classificacao"] != "inventada" or linha["tipo"] != "jurisprudencia":
            continue
        texto = textos[linha["documento_id"]]
        trecho = texto[int(linha["inicio"]) : int(linha["fim"])]
        if _resolver(indice, linha, trecho):
            vazadas.append(trecho[:60])
    assert not vazadas, f"inventadas com candidato: {vazadas[:5]}"


# -- consultas --------------------------------------------------------------


def test_consultas_devolvem_listas(indice, reais, textos) -> None:
    """`por_numero` e `por_lei_artigo` sempre devolvem lista (pode haver empate)."""
    assert indice.por_numero("numero-que-nao-existe") == []
    assert indice.por_lei_artigo("LEI-INEXISTENTE-0000", "1") == []

    linha = reais[0]
    texto = textos[linha["documento_id"]]
    trecho = texto[int(linha["inicio"]) : int(linha["fim"])]
    assert isinstance(_resolver(indice, linha, trecho), set)


def test_sumulas_entram_com_prefixo(indice) -> None:
    """Súmula é indexada como `S<n>` / `SV<n>`, sem colidir com processos."""
    sumulas = [r for r in indice.registros if r.natureza == "sumula"]
    assert sumulas
    for registro in sumulas:
        assert registro.numero
        assert registro.numero.startswith(("S", "SV"))


def test_dispositivos_tem_lei_e_artigo(indice) -> None:
    """Todo dispositivo resolve para uma `lei_chave` conhecida e um artigo."""
    dispositivos = [r for r in indice.registros if r.natureza == "dispositivo"]
    assert dispositivos
    for registro in dispositivos:
        assert registro.lei_chave, f"{registro.id} sem lei_chave"
        assert registro.artigo, f"{registro.id} sem artigo"


# -- atributos de desempate (ADR-007) ---------------------------------------


def test_cadeia_de_recursos_separa_principal(indice) -> None:
    """Na cadeia `AgInt no AgInt no REsp`, a principal é o recurso original.

    Sem isso, o desempate entre registros do mesmo processo não funciona.
    """
    com_cadeia = [r for r in indice.registros if r.cadeia_recursos]
    assert com_cadeia, "nenhuma cadeia lida — o desempate do ADR-007 ficaria cego"
    for registro in com_cadeia:
        assert registro.classe_principal
        assert registro.classe_principal not in ("",)


def test_relator_normalizado(indice) -> None:
    """Relator sem título, sem acento e minúsculo, dos dois lados da comparação."""
    com_relator = [r for r in indice.registros if r.relator]
    assert len(com_relator) > 900
    for registro in com_relator:
        assert registro.relator == registro.relator.lower()
        assert "ministro" not in registro.relator
        assert "min." not in registro.relator


def test_acordaos_tem_tribunal_e_ano(indice) -> None:
    acordaos = [r for r in indice.registros if r.natureza == "acordao"]
    assert all(r.tribunal for r in acordaos)
    assert sum(1 for r in acordaos if r.ano) == len(acordaos)


# -- tabelas ----------------------------------------------------------------


def test_tabelas_carregam_sem_chave_duplicada() -> None:
    siglas = [sigla for _, sigla in classes()]
    padroes = [padrao for padrao, _ in classes()]
    assert siglas and padroes
    assert len(padroes) == len(set(padroes)), "padrão de classe repetido"
    assert len(ufs()) == 27
    assert ocr()


def test_tabelas_resolvem_os_formatos_da_base() -> None:
    """Formatos que a base e a amostra realmente usam."""
    assert resolver_uf("RIO DE JANEIRO") == "RJ"
    assert resolver_uf("PR") == "PR"
    assert resolver_lei("Constituição Federal de 1988") == "CF-1988"
    assert resolver_lei("Lei nº 4.737, de 15 de julho de 1965") == "LEI-4737-1965"
    assert resolver_lei("Decreto-Lei nº 5.452, de 1º de maio de 1943") == "DL-5452-1943"
    assert resolver_lei("Lei Complementar nº 64/1990") == "LC-64-1990"
    assert resolver_lei("CPC") == "LEI-13105-2015"


def test_numero_proprio_reduz_a_digitos() -> None:
    assert so_digitos("1.741.784") == so_digitos("1741784") == "1741784"
    assert numero_proprio("STJ", "acordao", "RECURSO ESPECIAL Nº 1.741.784 - PR (2018/0116304-1)")
