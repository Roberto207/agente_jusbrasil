"""Etapa 2 da decisão: candidatos consistentes e os caminhos de decisão (ADR-006, ADR-007).

Cada citação termina em exatamente um caminho, com nome estável. A tabela é exaustiva e os
caminhos são disjuntos; a confiança (ADR-008) e o relatório dependem desses nomes.
"""

from __future__ import annotations

from collections.abc import Sequence

from verificador.contratos import Campos, RegistroIndice
from verificador.tabelas import mesma_familia_classe

SEM_NUMERO = "sem_numero"
NUMERO_AUSENTE = "numero_ausente"
NUMERO_CONTRADITO = "numero_contradito"
NUMERO_UNICO = "numero_unico"
NUMERO_DESEMPATADO = "numero_desempatado"
NUMERO_AMBIGUO = "numero_ambiguo"
LEI_APELIDO_DESCONHECIDO = "lei_apelido_desconhecido"
LEI_AUSENTE = "lei_ausente"
LEI_UNICA = "lei_unica"
LEI_AMBIGUA = "lei_ambigua"
# Citação detectada cujos campos as regras não leram (e não há LLM): nunca vira `real` (ADR-006).
CAMPOS_NAO_LIDOS = "campos_nao_lidos"

CLASSE_DO_CAMINHO: dict[str, str] = {
    SEM_NUMERO: "incompleta",
    NUMERO_AUSENTE: "inventada",
    NUMERO_CONTRADITO: "inventada",
    NUMERO_UNICO: "real",
    NUMERO_DESEMPATADO: "real",
    NUMERO_AMBIGUO: "incompleta",
    LEI_APELIDO_DESCONHECIDO: "inventada",
    LEI_AUSENTE: "inventada",
    LEI_UNICA: "real",
    LEI_AMBIGUA: "incompleta",
    CAMPOS_NAO_LIDOS: "incompleta",
}


# Os 10 caminhos da tabela do DESIGN; `CAMPOS_NAO_LIDOS` é o 11º, emitido só pela integração.
CAMINHOS_DECISAO = tuple(k for k in CLASSE_DO_CAMINHO if k != CAMPOS_NAO_LIDOS)


def consistentes(campos: Campos, candidatos: Sequence[RegistroIndice]) -> list[RegistroIndice]:
    """Candidatos que nenhum atributo *explícito* da citação contradiz (ADR-007).

    Ordem do filtro: tribunal, UF, classe processual principal, cadeia de recursos. Atributo ausente
    na citação (ou no registro) nunca elimina ninguém.

    Com **mais de um** candidato, classe e cadeia precisam bater exatamente — é o desempate.
    Com **exatamente um**, a classe de outra família processual veta (número emprestado: HC no
    lugar de REsp). Estágio do mesmo caso (`ARR` vs `AIRR`) não é empréstimo: a página Data manda
    1 candidato → `real`, e a cadeia também muda nesse caso (`AgARR` lê `ARR`+`AgRg`). Cadeia
    divergente com a **mesma** classe continua vetando.
    """
    unico = len(candidatos) == 1
    saida = []
    for r in candidatos:
        if campos.tribunal and r.tribunal and campos.tribunal != r.tribunal:
            continue
        if campos.uf and r.uf and campos.uf != r.uf:
            continue
        if campos.classe_principal and r.classe_principal:
            if unico:
                if not mesma_familia_classe(campos.classe_principal, r.classe_principal):
                    continue
            elif campos.classe_principal != r.classe_principal:
                continue
        cadeia_diverge = bool(
            campos.cadeia_recursos
            and tuple(campos.cadeia_recursos) != tuple(r.cadeia_recursos)
        )
        if cadeia_diverge:
            # Outro estágio da família muda classe e cadeia juntas (`AgARR` → ARR+AgRg vs AIRR).
            # Cadeia divergente com a *mesma* classe continua empréstimo (AgInt no REsp único).
            outro_estagio = (
                unico
                and campos.classe_principal
                and r.classe_principal
                and campos.classe_principal != r.classe_principal
                and mesma_familia_classe(campos.classe_principal, r.classe_principal)
            )
            if not outro_estagio:
                continue
        saida.append(r)
    return saida
