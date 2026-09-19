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
