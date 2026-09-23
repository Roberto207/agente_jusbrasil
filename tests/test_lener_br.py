"""Sonda de recall externa (Tier 2, `tarefas_equipe.md`): LeNER-Br é texto jurídico real, escrito
por gente de fora da equipe — não pontuável contra o nosso gabarito (convenção de anotação
diferente), mas responde à pergunta que a amostra e o sintético não conseguem responder sozinhos:
em texto que ninguém do time escreveu, quantas referências a julgados nossos padrões deixam passar?

Não é teste de regressão do pipeline oficial — é diagnóstico. Roda só `preparar()` + `extrair()`
(sem índice/base: a extração de spans não depende da base canônica do desafio).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import iou_offsets
from tests.lener_br_helpers import documento, documentos
from verificador.extracao import extrair
from verificador.texto import preparar

RAIZ = Path(__file__).resolve().parents[1]
PASTA_LENER = RAIZ / "lener-br" / "leNER-Br"


@pytest.fixture(scope="module")
def dataset() -> Path:
    if not (PASTA_LENER / "raw_text").is_dir():
        pytest.skip(
            "LeNER-Br ausente — clone com "
            "`git clone --depth 1 https://github.com/peluz/lener-br.git lener-br` na raiz do repo"
        )
    return PASTA_LENER


def test_recall_de_jurisprudencia_no_leNER_br(dataset: Path) -> None:
    """Sonda: nenhum piso é imposto sobre generalização em si (é diagnóstico, não regressão de
    pipeline) — só garante que o parser/alinhamento do dataset está funcionando (achou entidade
    suficiente pra medir nada zerado por acidente de parsing)."""
    nomes = documentos(dataset)
    assert nomes, "parser não achou nenhum documento — checar o clone do LeNER-Br"

    total_gold = 0
    total_achados = 0
    por_documento: list[tuple[str, int, int]] = []
    for nome in nomes:
        raw, gold = documento(dataset, nome)
        if not gold:
            continue
        candidatas = extrair(preparar(raw))
        achados = 0
        for entidade in gold:
            esperado = (entidade.inicio, entidade.fim)
            if any(iou_offsets(esperado, (c.inicio, c.fim)) >= 0.5 for c in candidatas):
                achados += 1
        total_gold += len(gold)
        total_achados += achados
        por_documento.append((nome, achados, len(gold)))

    assert total_gold >= 50, f"esperava dezenas de entidades JURISPRUDENCIA, achou {total_gold}"
    recall = total_achados / total_gold

    piores = sorted((d for d in por_documento if d[2] > d[1]), key=lambda d: d[1] / d[2])[:5]
    print(
        f"\nLeNER-Br — recall de JURISPRUDENCIA: {total_achados}/{total_gold} = {recall:.4f}"
        f" ({len(nomes)} documentos, {sum(1 for _, g in ((d[0], d[2]) for d in por_documento) if g)} com entidade)"
    )
    if piores:
        print("Documentos com mais perda:", piores)

    # Diagnóstico, não regressão do pipeline oficial: sem piso duro. `total_gold >= 50` acima já
    # garante que o parser/alinhamento não está quebrado (se estivesse, teríamos 0 entidades).
