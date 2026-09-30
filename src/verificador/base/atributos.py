"""Atributos de um registro da base, além do número próprio (Tarefa 3).

O número sozinho não basta para decidir: o mesmo número de processo aparece em
vários registros (recursos internos do mesmo processo). O desempate usa
`classe_principal`, `cadeia_recursos`, `uf` e `tribunal` — é o que a frente D
compara contra os campos lidos da citação (ADR-007).

Reusa as tabelas da frente B (`verificador.tabelas`): classes processuais, UFs e
apelidos de lei. Nada é duplicado aqui.
"""

from __future__ import annotations

import re
import unicodedata

from verificador.base.numero_proprio import JANELA_CABECALHO
from verificador.tabelas import classes_no_texto, resolver_uf, tst_sigla

# UF colada ao número: `Nº 1.741.784 - PR`, `7000075-58.2022.7.00.0000/PR`.
_UF_SIGLA = re.compile(r"[-/]\s*([A-Z]{2})\b")

# UF por extenso do STF, entre o número e `RELATOR`: `76.532 RIO DE JANEIRO RELATOR`.
_UF_EXTENSO = re.compile(r"\d\s+([A-Z][A-Z\s]{3,40}?)\s+(?:RELATOR|RELATORA|PRESIDENTE)")

# UF por extenso do TSE, depois da comarca: `- CLASSE 32ª GANDU - BAHIA Relator:`.
_UF_TSE = re.compile(r"-\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{3,30}?)\s*\.?\s*Relator", re.I)

_RELATOR = re.compile(
    r"RELATOR(?:A)?\s*:?\s*(?:MINISTR[OA]\s*)?(?:DR\.?\s*)?([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'\s.]{4,60}?)"
    r"(?=\s{2,}|\s*(?:RECORRENTE|RECORRIDO|AGRAVANTE|AGRAVADO|EMBARGANTE|EMBARGADO|"
    r"REQUERENTE|REQUERIDO|IMPETRANTE|PACIENTE|ADVOGAD|REDATOR|REVISOR|R\.P/|$))",
    re.I,
)

# Fim do bloco "classe + cadeia": o `Nº` do número, ou o número em si. Tudo que
# vem depois já é corpo do acórdão.
_ATE_O_NUMERO = re.compile(r"N\s*[ºo°.º�]{0,3}\s*\d|\b\d{1,3}\.\d{3}\b|\d{1,7}-\d{2}\.\d{4}")

_ANO_CNJ = re.compile(r"\d{1,7}-\d{2}\.(\d{4})\.")
_ANO_DATA = re.compile(r"\b\d{2}/\d{2}/((?:19|20)\d{2})\b")
_ANO_SEQ = re.compile(r"\((\d{4})/\d+-\d\)")
_ANO_SOLTO = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")

# Prefixos de recurso interno usados pelo TST no próprio número:
# `TST-ED-E-ED-RR-3400-05...` → cadeia (EDcl, E, EDcl) + principal RR.
_TST_CADEIA = re.compile(r"TST\s*-\s*((?:[A-Za-z]{1,6}\s*-\s*)+)\d", re.I)


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_relator(nome: str) -> str | None:
    """Relator em forma comparável: sem título, sem acento, minúsculo.

    `MINISTRO JOEL ILAN PACIORNIK` → `joel ilan paciornik`.

    A frente B tem uma função de mesmo nome para o lado da *citação*; esta cobre
    o lado do *registro*, cujos títulos são outros (`MINISTRA`, `MIN.`, `DR.`).
    """
    texto = _sem_acento(nome)
    texto = re.sub(r"\b(?:MINISTR[OA]|MIN|DR|DRA|DES|JUIZ[AO]?)\b\.?", " ", texto, flags=re.I)
    texto = re.sub(r"[^A-Za-z\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip().lower()
    return texto or None


def extrair_relator(texto: str, coluna: str | None = None) -> str | None:
    """Relator do registro, normalizado.

    A base já traz a coluna `relator` preenchida em 993 dos 996 acórdãos, então
    ela é a fonte primária — ler do texto só faz sentido quando ela está vazia.
    Isso evita depender do cabeçalho do TST, que não nomeia o relator no começo
    (ele assina no fim do documento).
    """
    if coluna and coluna.strip():
        normalizado = normalizar_relator(coluna)
        if normalizado:
            return normalizado
    m = _RELATOR.search(texto[:JANELA_CABECALHO])
    return normalizar_relator(m.group(1)) if m else None


def extrair_uf(tribunal: str | None, texto: str) -> str | None:
    """UF do registro.

    Cada tribunal escreve de um jeito: o STJ usa sigla colada ao número, o STF
    usa o nome por extenso antes de `RELATOR`, o TSE põe a comarca e o estado
    depois da classe. Por isso a busca é ordenada por tribunal.
    """
    cabecalho = texto[:JANELA_CABECALHO]

    if tribunal == "STF":
        m = _UF_EXTENSO.search(_sem_acento(cabecalho))
        if m:
            uf = resolver_uf(m.group(1).strip())
            if uf:
                return uf

    if tribunal == "TSE":
        m = _UF_TSE.search(cabecalho)
        if m:
            uf = resolver_uf(m.group(1).strip())
            if uf:
                return uf

    m = _UF_SIGLA.search(cabecalho)
    if m:
        uf = resolver_uf(m.group(1))
        if uf:
            return uf

    # Último recurso: qualquer nome de estado por extenso no cabeçalho.
    m = _UF_EXTENSO.search(_sem_acento(cabecalho))
    return resolver_uf(m.group(1).strip()) if m else None


def extrair_ano(texto: str) -> int | None:
    """Ano do registro.

    Preferência: ano embutido no número CNJ (o mais confiável), depois a data de
    julgamento, depois o ano do número sequencial do STJ, depois qualquer ano
    plausível no cabeçalho.
    """
    cabecalho = texto[:JANELA_CABECALHO]
    for padrao in (_ANO_CNJ, _ANO_DATA, _ANO_SEQ):
        m = padrao.search(cabecalho)
        if m:
            return int(m.group(1))
    m = _ANO_SOLTO.search(cabecalho)
    return int(m.group(1)) if m else None


def extrair_classes(tribunal: str | None, texto: str) -> tuple[str | None, tuple[str, ...]]:
    """`(classe_principal, cadeia_recursos)` do registro.

    Numa cadeia de recursos internos (`AgInt no AgInt no REsp`), a **principal**
    é a última — o recurso original — e a cadeia guarda as anteriores, na ordem
    do texto. É o que permite distinguir o REsp puro do agravo sobre ele
    (ADR-007).
    """
    cabecalho = texto[:JANELA_CABECALHO]

    # No TST a cadeia está dentro do próprio número (`TST-ED-E-ED-RR-3400-…`),
    # não em prosa, então é lida do texto inteiro como o número é.
    if tribunal == "TST":
        m = _TST_CADEIA.search(texto)
        if m:
            tokens = [t.strip() for t in m.group(1).split("-") if t.strip()]
            siglas = [sigla for t in tokens for sigla in tst_sigla(t)]
            if siglas:
                return siglas[-1], tuple(siglas[:-1])

    # A cadeia de recursos vem toda **antes do número** (`EDcl no AgRg no
    # RECURSO EM MANDADO DE SEGURANÇA Nº 49.890`). Ler além disso capturaria
    # siglas do corpo e trocaria a classe principal.
    m = _ATE_O_NUMERO.search(cabecalho)
    trecho = cabecalho[: m.start()] if m else cabecalho

    siglas = classes_no_texto(trecho)
    if not siglas:
        return None, ()
    return siglas[-1], tuple(siglas[:-1])
