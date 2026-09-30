"""Frentes A × B — o que a leitura do texto e o índice precisam concordar.

Dois testes de conjunto:

* **ida e volta**: para cada registro da base monta-se a citação natural dele, extrai-se,
  lê-se os campos e consulta-se o índice. Pega divergência de nome de sigla e de formato
  entre as duas frentes que a amostra (26 documentos) não exercita.
* **amostra sob o ADR-007**: a decisão provisória abaixo mostra o que a frente D vai
  encontrar ao ligar A e B.

Nada da amostra entra como literal (R43): as citações saem do índice e do gabarito em
tempo de execução.
"""

from __future__ import annotations

import collections

from verificador.extracao import extrair, ler_campos
from verificador.texto import preparar
from tests.helpers import iou_offsets

PISO_TST = 0.95
PISO_DEMAIS = 0.88


def _consistentes(campos, candidatos):
    """Filtro do ADR-007 (provisório, até a frente D): atributo ausente nunca elimina."""
    saida = []
    for r in candidatos:
        if campos.tribunal and r.tribunal and campos.tribunal != r.tribunal:
            continue
        if campos.uf and r.uf and campos.uf != r.uf:
            continue
        if (
            campos.classe_principal
            and r.classe_principal
            and campos.classe_principal != r.classe_principal
        ):
            continue
        if campos.cadeia_recursos and campos.cadeia_recursos != r.cadeia_recursos:
            continue
        saida.append(r)
    return saida


def _milhar(digitos: str) -> str:
    grupos: list[str] = []
    while digitos:
        grupos.insert(0, digitos[-3:])
        digitos = digitos[:-3]
    return ".".join(grupos)


def _cnj(digitos: str) -> str:
    return (
        f"{digitos[:-13]}-{digitos[-13:-11]}.{digitos[-11:-7]}."
        f"{digitos[-7]}.{digitos[-6:-4]}.{digitos[-4:]}"
    )


def _citacao(r) -> str:
    """Citação no formato em que a própria base escreve o número do registro."""
    cadeia = list(r.cadeia_recursos)
    if r.tribunal == "TST":
        return "-".join(["TST", *cadeia, r.classe_principal]) + "-" + _cnj(r.numero)
    numero = _cnj(r.numero) if len(r.numero) >= 14 else _milhar(r.numero)
    classes = " no ".join([*cadeia, r.classe_principal])
    uf = f"/{r.uf}" if r.uf and r.tribunal == "STJ" else ""
    return f"{classes} nº {numero}{uf}"


def test_ida_e_volta_de_cada_registro_da_base(indice) -> None:
    acertos: collections.Counter[str] = collections.Counter()
    totais: collections.Counter[str] = collections.Counter()
    for r in indice.registros:
        if r.natureza != "acordao" or not r.numero or not r.classe_principal:
            continue
        totais[r.tribunal] += 1
        texto = f"Conforme decidido no {_citacao(r)}, a tese prevalece."
        candidatas = [c for c in extrair(preparar(texto)) if c.forma == "com_numero"]
        if not candidatas:
            continue
        campos = ler_campos(candidatas[0])
        if campos is None or not campos.numero:
            continue
        consistentes = _consistentes(campos, indice.por_numero(campos.numero))
        if r.id in {c.id for c in consistentes}:
            acertos[r.tribunal] += 1

    assert set(totais) == {"STF", "STJ", "STM", "TSE", "TST"}
    abaixo = {
        tribunal: f"{acertos[tribunal]}/{total}"
        for tribunal, total in totais.items()
        if acertos[tribunal] / total < (PISO_TST if tribunal == "TST" else PISO_DEMAIS)
    }
    assert not abaixo, f"registros que a citação natural não recupera: {abaixo}"


def test_amostra_sob_o_adr_007(indice, textos, gabarito) -> None:
    por_documento = collections.defaultdict(list)
    for linha in gabarito:
        por_documento[linha["documento_id"]].append(linha)

    reais_certos = inventadas_reais = incompletas_ok = 0
    for documento, texto in textos.items():
        candidatas = extrair(preparar(texto))
        for linha in por_documento[documento]:
            esperado = (int(linha["inicio"]), int(linha["fim"]))
            melhor = max(candidatas, key=lambda c: iou_offsets(esperado, (c.inicio, c.fim)))
            campos = ler_campos(melhor)
            assert campos is not None
            if melhor.forma == "sem_numero":
                previsto, id_ = "incompleta", None
            else:
                if melhor.forma == "lei_artigo":
                    candidatos = (
                        indice.por_lei_artigo(campos.lei_chave, campos.artigo)
                        if campos.lei_chave
                        else []
                    )
                else:
                    candidatos = indice.por_numero(campos.numero) if campos.numero else []
                consistentes = _consistentes(campos, candidatos)
                if not consistentes:
                    previsto, id_ = "inventada", None
                elif len(consistentes) == 1:
                    previsto, id_ = "real", consistentes[0].id
                else:
                    previsto, id_ = "incompleta", None

            if linha["classificacao"] == "real" and previsto == "real" and id_ == linha["id_canonico"]:
                reais_certos += 1
            if linha["classificacao"] == "inventada" and previsto == "real":
                inventadas_reais += 1
            if linha["classificacao"] == "incompleta" and previsto == "incompleta":
                incompletas_ok += 1

    assert inventadas_reais == 0  # τ = 0
    assert incompletas_ok == 32
    # 2 dos 96 são perdas conhecidas e não corrigíveis sem decorar a amostra: um número com dois
    # registros idênticos (R7 → incompleta) e uma citação cujo gabarito aponta outra classe.
    assert reais_certos >= 94
