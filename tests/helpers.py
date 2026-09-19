from __future__ import annotations


def trecho_gabarito(bruto: str) -> str:
    if "\n" in bruto:
        return bruto
    return bruto.replace("\\n", "\n")


def iou_offsets(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    if inter == 0:
        return 0.0
    uniao = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / uniao if uniao else 0.0


def citacao_verificada(inicio, fim, trecho, classe, id_canonico=None, *, tipo="jurisprudencia", forma=None, confianca=None):
    """`CitacaoVerificada` mínima para testar a saída sem depender de extração ou decisão."""
    from verificador.contratos import Campos, Candidata, CitacaoVerificada, Resolucao

    forma = forma or ("lei_artigo" if tipo == "lei" else "com_numero")
    return CitacaoVerificada(
        candidata=Candidata(inicio, fim, trecho, tipo, forma, "teste", frozenset({"regex"})),  # type: ignore[arg-type]
        campos=Campos(None, None, (), None, None, None, None, None, None, False, "regras"),
        resolucao=Resolucao(classe, id_canonico, "teste", (), confianca),  # type: ignore[arg-type]
    )
