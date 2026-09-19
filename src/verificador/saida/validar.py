"""Validação da saída antes de gravar (R3, R13, R38, R42).

O `kaggle_metric.py` rejeita a submissão **inteira** por causa de um único erro (duas citações
com IoU ≥ 0,5, `real` sem id...). Barrar aqui evita gastar uma submissão do teto diário.
"""

from __future__ import annotations

from collections.abc import Sequence

from verificador.contratos import CitacaoVerificada
from verificador.extracao.sobreposicao import iou

CLASSES = ("real", "inventada", "incompleta")
TIPOS = ("jurisprudencia", "lei")


class ErroDeSaida(ValueError):
    """A saída de um documento não cumpre o contrato."""


def validar_citacoes(
    documento_id: str,
    citacoes: Sequence[CitacaoVerificada],
    texto: str | None = None,
) -> list[str]:
    """Lista de problemas (vazia se a saída está válida). `texto` habilita o R38."""
    problemas: list[str] = []
    for i, c in enumerate(citacoes):
        cand, res = c.candidata, c.resolucao
        rotulo = f"[{documento_id}] citação #{i + 1} ({cand.inicio}, {cand.fim})"

        if not (0 <= cand.inicio < cand.fim):
            problemas.append(f"{rotulo}: span inválido; exige 0 <= inicio < fim")
        if texto is not None:
            if cand.fim > len(texto):
                problemas.append(f"{rotulo}: fim além do texto ({len(texto)})")
            elif cand.trecho != texto[cand.inicio : cand.fim]:  # R38
                problemas.append(f"{rotulo}: trecho difere de texto[inicio:fim] (R38)")

        if res.classificacao not in CLASSES:
            problemas.append(f"{rotulo}: classe {res.classificacao!r} inválida")
        if res.classificacao == "real":
            if not res.id_canonico or not str(res.id_canonico).isdigit():
                problemas.append(f"{rotulo}: `real` exige id_canonico só com dígitos (R12)")
        elif res.id_canonico:
            problemas.append(f"{rotulo}: id_canonico só é permitido em `real` (R13)")

        esperado = "lei" if cand.forma == "lei_artigo" else "jurisprudencia"  # R42
        if cand.tipo not in TIPOS or cand.tipo != esperado:
            problemas.append(f"{rotulo}: tipo {cand.tipo!r} para forma {cand.forma!r}; esperado {esperado!r} (R42)")

        if res.confianca is not None and not (0.0 <= res.confianca <= 1.0):
            problemas.append(f"{rotulo}: confianca {res.confianca} fora de [0, 1]")

    for a in range(len(citacoes)):  # R3
        for b in range(a + 1, len(citacoes)):
            if iou(citacoes[a].candidata, citacoes[b].candidata) >= 0.5:
                problemas.append(
                    f"[{documento_id}] citações #{a + 1} e #{b + 1} têm IoU >= 0,5 (R3): "
                    f"o Kaggle rejeitaria a submissão inteira"
                )
    return problemas
