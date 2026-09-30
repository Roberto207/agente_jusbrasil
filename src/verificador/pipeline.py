"""O pipeline de um documento: texto → extração → campos → decisão (DESIGN, "Pipeline de execução").

Sem GPU: regras e consulta ao índice (ADR-001). O encoder entra só na extração, atrás de
`usar_encoder`, em CPU (ADR-011). A classificação nunca passa por modelo.
"""

from __future__ import annotations

from collections import defaultdict
from time import perf_counter

from verificador.base.indice import Indice
from verificador.contratos import CitacaoVerificada, Resolucao
from verificador.decisao import decidir
from verificador.decisao.caminhos import CAMPOS_NAO_LIDOS
from verificador.decisao.confianca import atribuir
from verificador.extracao import extrair, ler_campos
from verificador.extracao.campos import CAMPOS_VAZIOS
from verificador.texto import preparar


def processar_documento(
    texto: str, indice: Indice, tempos: dict[str, float] | None = None, encoder=None
) -> list[CitacaoVerificada]:
    """Citações verificadas de um documento, na ordem do texto. `tempos` acumula segundos por etapa."""
    tempos = tempos if tempos is not None else defaultdict(float)

    t0 = perf_counter()
    preparado = preparar(texto)
    tempos["texto"] = tempos.get("texto", 0.0) + perf_counter() - t0

    t0 = perf_counter()
    candidatas = extrair(preparado, encoder)  # encoder: só com `usar_encoder` (ADR-011)
    tempos["extracao"] = tempos.get("extracao", 0.0) + perf_counter() - t0

    verificadas: list[CitacaoVerificada] = []
    for candidata in candidatas:
        t0 = perf_counter()
        campos = ler_campos(candidata)
        tempos["campos"] = tempos.get("campos", 0.0) + perf_counter() - t0

        t0 = perf_counter()
        if campos is None:  # campos não lidos: nunca `real` (ADR-006)
            campos = CAMPOS_VAZIOS
            resolucao = Resolucao("incompleta", None, CAMPOS_NAO_LIDOS, (), None)
        else:
            resolucao = decidir(campos, candidata.forma, indice)
        resolucao = atribuir(resolucao, campos)
        tempos["decisao"] = tempos.get("decisao", 0.0) + perf_counter() - t0
        verificadas.append(CitacaoVerificada(candidata, campos, resolucao))
    return verificadas
