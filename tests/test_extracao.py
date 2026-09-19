from __future__ import annotations

from verificador.contratos import Candidata
from verificador.extracao import extrair, ler_campos
from verificador.extracao.sobreposicao import iou, resolver
from verificador.texto import preparar
from tests.helpers import iou_offsets, trecho_gabarito


def test_recall_de_spans_iou(textos, gabarito) -> None:
    perdidas: list[str] = []
    for doc_id, texto in textos.items():
        prep = preparar(texto)
        candidatas = extrair(prep)
        golds = [row for row in gabarito if row["documento_id"] == doc_id]
        usados: set[int] = set()
        for row in golds:
            esperado = (int(row["inicio"]), int(row["fim"]))
            melhor = 0.0
            melhor_i = None
            for i, cand in enumerate(candidatas):
                if i in usados:
                    continue
                v = iou_offsets(esperado, (cand.inicio, cand.fim))
                if v > melhor:
                    melhor = v
                    melhor_i = i
            if melhor < 0.5:
                perdidas.append(
                    f"{doc_id} {row['citacao_id']} {trecho_gabarito(row['trecho'])!r} melhor={melhor:.2f}"
                )
            elif melhor_i is not None:
                usados.add(melhor_i)
    assert not perdidas, "spans sem par (IoU < 0,5):\n" + "\n".join(perdidas)


def test_r4_sobreposição_parcial_nao_fica_abaixo_de_meio(textos, gabarito) -> None:
    for doc_id, texto in textos.items():
        prep = preparar(texto)
        candidatas = extrair(prep)
        golds = [
            (int(row["inicio"]), int(row["fim"]))
            for row in gabarito
            if row["documento_id"] == doc_id
        ]
        for cand in candidatas:
            for g in golds:
                inter = max(0, min(cand.fim, g[1]) - max(cand.inicio, g[0]))
                if inter == 0:
                    continue
                assert iou_offsets((cand.inicio, cand.fim), g) >= 0.5


def test_r3_sem_par_com_iou_alto(textos) -> None:
    for texto in textos.values():
        candidatas = extrair(preparar(texto))
        for i, a in enumerate(candidatas):
            for b in candidatas[i + 1 :]:
                assert iou(a, b) < 0.5


def test_r33_referencia_vaga_conhecida_nao_vira_candidata(textos) -> None:
    marcas = (
        "jurisprudência pacífica",
        "entendimento sumulado",
        "artigo correspondente",
        "orientação jurisprudencial da Corte Superior",
    )
    for texto in textos.values():
        prep = preparar(texto)
        candidatas = extrair(prep)
        for marca in marcas:
            pos = texto.lower().find(marca)
            if pos < 0:
                continue
            fim = pos + len(marca)
            for cand in candidatas:
                if cand.inicio <= pos and cand.fim >= fim:
                    raise AssertionError(f"referência vaga capturada: {cand.trecho!r}")


def test_amostra_tem_recall_e_campos_completos(textos, gabarito) -> None:
    emitidas = 0
    golds = 0
    for doc_id, texto in textos.items():
        candidatas = extrair(preparar(texto))
        emitidas += len(candidatas)
        golds += sum(1 for row in gabarito if row["documento_id"] == doc_id)
        assert all(ler_campos(c) is not None for c in candidatas)
        assert all(c.trecho == texto[c.inicio : c.fim] for c in candidatas)
    assert emitidas == golds == 192


def test_r34_nada_do_cabecalho(textos) -> None:
    for texto in textos.values():
        prep = preparar(texto)
        for cand in extrair(prep):
            assert cand.inicio >= prep.corpo_inicio
            assert cand.trecho == texto[cand.inicio : cand.fim]


def test_padrao_com_numero_positivo_e_negativo() -> None:
    texto = (
        "No mérito aplica-se o AgInt no AREsp nº 9.888.777/GO. "
        "Não se extrai o protocolo 2019.1234567 nem as fls. 10/20."
    )
    cands = extrair(preparar(texto))
    assert any(c.forma == "com_numero" and "9.888.777" in c.trecho for c in cands)
    assert all("2019.1234567" not in c.trecho for c in cands)
    assert all("fls" not in c.trecho.lower() for c in cands)


def test_padrao_sumula_positivo_e_negativo() -> None:
    texto = "A Súmula 83 do STJ e a Súmula Vinculante 10 resolvem. O entendimento sumulado não basta."
    cands = extrair(preparar(texto))
    assert {c.trecho for c in cands if c.forma == "sumula"} >= {
        "Súmula 83 do STJ",
        "Súmula Vinculante 10",
    }


def test_padrao_lei_positivo_e_negativo() -> None:
    texto = "Vale o art. 12, III, da Constituição Federal, não o artigo correspondente do CPC."
    cands = extrair(preparar(texto))
    leis = [c for c in cands if c.forma == "lei_artigo"]
    assert any("art. 12" in c.trecho for c in leis)
    assert all("artigo correspondente" not in c.trecho for c in leis)


def test_padrao_sem_numero_positivo_e_negativo() -> None:
    texto = (
        "Como o julgado do STF proferido em 2024 pela relatoria de Relator Exemplo. "
        "A jurisprudência pacífica desta Corte não é citação."
    )
    cands = extrair(preparar(texto))
    assert any(c.forma == "sem_numero" for c in cands)
    assert all("pacífica" not in c.trecho for c in cands)


def test_resolver_descarta_contida() -> None:
    longa = Candidata(10, 40, "x" * 30, "jurisprudencia", "com_numero", "a", frozenset({"regex"}))
    curta = Candidata(12, 20, "x" * 8, "jurisprudencia", "com_numero", "a", frozenset({"regex"}))
    saida = resolver([longa, curta])
    assert saida == [longa]
