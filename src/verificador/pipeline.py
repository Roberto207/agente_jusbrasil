"""O pipeline de um documento: texto → extração → campos → decisão (DESIGN, "Pipeline de execução").

Sem GPU, sem rede e sem modelo: só regras e consulta ao índice (ADR-001). O encoder e o LLM entram
nos pontos marcados, atrás de `usar_encoder`/`usar_llm`, quando existirem.
"""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter

from verificador.base.indice import Indice
from verificador.contratos import Campos, CitacaoVerificada, Resolucao
from verificador.decisao import decidir
from verificador.decisao.caminhos import CAMPOS_NAO_LIDOS
from verificador.extracao import extrair, ler_campos
from verificador.texto import preparar


def _campos_vazios() -> Campos:
    return Campos(None, None, (), None, None, None, None, None, None, False, "regras")


def processar_documento(
    texto: str, indice: Indice, tempos: dict[str, float] | None = None
) -> list[CitacaoVerificada]:
    """Citações verificadas de um documento, na ordem do texto. `tempos` acumula segundos por etapa."""
    tempos = tempos if tempos is not None else defaultdict(float)

    t0 = perf_counter()
    preparado = preparar(texto)
    tempos["texto"] = tempos.get("texto", 0.0) + perf_counter() - t0

    t0 = perf_counter()
    candidatas = extrair(preparado, None)  # encoder: Fase 4, se ganhar da linha de base
    tempos["extracao"] = tempos.get("extracao", 0.0) + perf_counter() - t0

    verificadas: list[CitacaoVerificada] = []
    for candidata in candidatas:
        t0 = perf_counter()
        campos = ler_campos(candidata)
        tempos["campos"] = tempos.get("campos", 0.0) + perf_counter() - t0

        t0 = perf_counter()
        if campos is None:  # fila de difíceis sem LLM: nunca `real` (ADR-006)
            campos = _campos_vazios()
            resolucao = Resolucao("incompleta", None, CAMPOS_NAO_LIDOS, (), None)
        else:
            resolucao = decidir(campos, candidata.forma, indice)
        tempos["decisao"] = tempos.get("decisao", 0.0) + perf_counter() - t0
        verificadas.append(CitacaoVerificada(candidata, campos, resolucao))
    return verificadas
