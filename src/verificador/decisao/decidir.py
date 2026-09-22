"""`decidir(campos, forma, indice) -> Resolucao`: a classe e o id de uma citação (DESIGN [4])."""

from __future__ import annotations

from verificador.base.indice import Indice
from verificador.contratos import Campos, RegistroIndice, Resolucao
from verificador.decisao import caminhos as c
from verificador.decisao.candidatos import buscar_candidatos, normalizar_sumula


def _ids(registros: list[RegistroIndice]) -> tuple[str, ...]:
    return tuple(sorted(r.id for r in registros))


def _cumpre_r14(campos: Campos, forma: str, registro: RegistroIndice) -> bool:
    """R14: `real` só se número (ou lei e artigo) da citação é igual ao do registro resolvido."""
    if forma == "lei_artigo":
        return registro.lei_chave == campos.lei_chave and registro.artigo == campos.artigo
    numero = normalizar_sumula(campos.numero) if forma == "sumula" and campos.numero else campos.numero
    return registro.numero == numero


def decidir(campos: Campos, forma: str, indice: Indice) -> Resolucao:
    """Classifica uma citação. Determinística e independente da ordem do índice e do nome do documento.

    Na dúvida nunca `real` (ADR-006): só um único candidato consistente vira `real`.
    """
    if forma == "sem_numero":  # R6: tribunal/classe + ano + relator sem número
        return Resolucao("incompleta", None, c.SEM_NUMERO, (), None)

    lei = forma == "lei_artigo"
    if lei and not campos.lei_chave:
        return Resolucao("inventada", None, c.LEI_APELIDO_DESCONHECIDO, (), None)

    candidatos = buscar_candidatos(campos, forma, indice)
    if not candidatos:  # R8
        return Resolucao("inventada", None, c.LEI_AUSENTE if lei else c.NUMERO_AUSENTE, (), None)

    validos = c.consistentes(campos, candidatos)
    if not validos:  # R40: número existe, mas tribunal/UF/família de classe contradizem todos
        return Resolucao("inventada", None, c.NUMERO_CONTRADITO, _ids(candidatos), None)

    if len(validos) > 1:  # R7
        return Resolucao(
            "incompleta", None, c.LEI_AMBIGUA if lei else c.NUMERO_AMBIGUO, _ids(validos), None
        )

    escolhido = validos[0]  # R9
    if not _cumpre_r14(campos, forma, escolhido):
        raise RuntimeError(f"R14 violado: registro {escolhido.id} não corresponde à citação lida")
    if lei:
        caminho = c.LEI_UNICA
    else:
        caminho = c.NUMERO_DESEMPATADO if len(candidatos) > 1 else c.NUMERO_UNICO
    return Resolucao("real", escolhido.id, caminho, (escolhido.id,), None)  # R12
