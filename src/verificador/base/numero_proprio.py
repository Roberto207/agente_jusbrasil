"""Extração do número próprio de cada registro da base (ADR-002).

O número de um registro está dentro do seu texto, em formato diferente por
tribunal, e o texto também cita números de *precedentes*. Pegar o número errado
faz uma citação inventada parecer real — é o risco central do ADR-002.

Cada parser aqui olha só a **região onde o tribunal identifica o próprio
processo** (cabeçalho, ou o rodapé no caso do TST), nunca o corpo inteiro.

Formatos observados na base (medições em `mudancas_caio_fase_1_a.md`, Tarefa 1).
"""

from __future__ import annotations

import re
import unicodedata

# Quanto do começo do texto conta como cabeçalho, por fonte. Suficiente para o
# bloco de identificação e curto o bastante para não alcançar o corpo (onde
# moram os precedentes citados).
JANELA_CABECALHO = 400

# Número no padrão CNJ: 7000075-58.2022.7.00.0000. Tolera espaço/quebra depois
# do hífen e dentro do ano — o OCR da base parte números (`1052-77. 201 5.6...`).
_CNJ = r"\d{1,7}\s*-\s*\d{2}\s*\.\s*\d\s*\d\s*\d\s*\d\s*\.\s*\d\s*\.\s*\d{2}\s*\.\s*\d{4}"

# Número curto, com ou sem pontuação: 1.741.784, 2124716 ou 87 (cautelares).
_CURTO = r"\d{1,3}(?:\.\d{3})+|\d{2,9}"

# "Nº" em todas as formas que a base traz, inclusive corrompidas por OCR
# (`N o`, `N°`, `N.`). O `.{0,2}` cobre o caractere de substituição de encoding.
_NUM = r"N\s*[ºo°.º�]{0,3}\s*"


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def so_digitos(numero: str) -> str:
    """Reduz um número a dígitos — a forma canônica de comparação.

    `1.741.784`, `1741784` e `1 741 784` viram todos `1741784`, o que permite
    casar a citação com o registro independentemente da pontuação.
    """
    return re.sub(r"\D", "", numero)


# --------------------------------------------------------------------------
# Parsers por fonte
# --------------------------------------------------------------------------

_STJ = re.compile(rf"{_NUM}({_CURTO})\s*-\s*([A-Z]{{2}})\b")


def numero_stj(texto: str) -> str | None:
    """STJ: primeira ocorrência `Nº <número> - <UF>` no cabeçalho.

    `AgRg no AGRAVO EM RECURSO ESPECIAL Nº 1.327.863 - PR (2018/0169803-4)`
    A UF logo após o número é o que distingue o número do processo de outros
    números do cabeçalho.
    """
    m = _STJ.search(texto[:JANELA_CABECALHO])
    return so_digitos(m.group(1)) if m else None


# STF: número seguido da UF por extenso, antes de RELATOR/RELATORA.
_STF = re.compile(
    r"\b(\d{1,3}(?:\.\d{3})*)\s+([A-Z][A-Z\s]{3,40}?)\s+(?:RELATOR|RELATORA|PRESIDENTE)",
)


def numero_stf(texto: str) -> str | None:
    """STF: `AG.REG. NA RECLAMAÇÃO 76.532 RIO DE JANEIRO RELATOR : ...`

    Não usa `Nº`; o que delimita o número é a UF por extenso seguida de
    `RELATOR`.
    """
    m = _STF.search(_sem_acento(texto[:JANELA_CABECALHO]))
    return so_digitos(m.group(1)) if m else None


_CNJ_RE = re.compile(_CNJ)


def numero_cnj(texto: str) -> str | None:
    """STM e TSE: primeiro número CNJ do cabeçalho.

    `APELAÇÃO CRIMINAL Nº 7000075-58.2022.7.00.0000/PR`
    Tolera o espaço que a base insere no meio (`7000380- 08.2023...`).
    """
    m = _CNJ_RE.search(texto[:JANELA_CABECALHO])
    return so_digitos(m.group(0)) if m else None


# TSE às vezes usa número curto com o CNJ entre parênteses:
# `RECURSO ESPECIAL ELEITORAL Nº 36.038 ( 43342-43.2009.6.00.0000)`
_TSE_CURTO = re.compile(rf"{_NUM}(\d{{1,3}}(?:\.\d{{3}})+)\s*[(\-]")

# Último recurso do TSE: o OCR desmonta a estrutura CNJ a ponto de nenhum padrão
# rígido casar (`487-26.20126.06.0049`, `598- 2012 6 08 0018`, `2622-472010.6.27.0000`).
# Aqui a âncora é o `Nº` do cabeçalho: tudo que vier depois dele em dígitos,
# pontos, hífens e espaços é o número, até o `-` que separa a classe.
_TSE_RUIDOSO = re.compile(rf"{_NUM}(\d[\d\s.\-]{{8,30}}\d)")


def numero_tse(texto: str) -> str | None:
    """TSE: número CNJ do cabeçalho; formas degradadas por OCR como fallback."""
    cabecalho = texto[:JANELA_CABECALHO]
    m = _CNJ_RE.search(cabecalho)
    if m:
        return so_digitos(m.group(0))
    m = _TSE_CURTO.search(cabecalho)
    if m:
        return so_digitos(m.group(1))
    m = _TSE_RUIDOSO.search(cabecalho)
    return so_digitos(m.group(1)) if m else None


# TST — dois padrões, nesta ordem de confiança:
#   1. rodapé `PROCESSO Nº TST-ED-E-ED-RR-3400-05.2011.5.21.0009`
#   2. `estes autos de ... nº TST-AIRR-25823-78.2015.5.24.0091`
# O `DESIGN.md` previa só o primeiro, que cobre 11 de 198 registros (Tarefa 1).
# Classes que nunca são o próprio processo: `ArgInc` é a arguição de
# inconstitucionalidade que centenas de acórdãos do TST citam na ementa como
# precedente (`TST-ArgInc-479-60.2011.5.04.0231`). Sem excluí-la, 37 registros
# herdariam o número dela — exatamente a armadilha do ADR-002.
_TST_CLASSE_PRECEDENTE = r"ArgInc|IncJulg|IRR|IUJ"

_NAO_PRECEDENTE = rf"(?!(?:{_TST_CLASSE_PRECEDENTE})\b)"

_TST_RODAPE = re.compile(
    rf"PROCESSO\s+{_NUM}TST\s*-\s*{_NAO_PRECEDENTE}(?:[A-Za-z]+\s*-\s*)*({_CNJ})", re.I
)
_TST_AUTOS = re.compile(
    rf"autos\s+de\b[^.]{{0,160}}?TST\s*-\s*{_NAO_PRECEDENTE}(?:[A-Za-z]+\s*-\s*)*({_CNJ})", re.I
)
_TST_QUALQUER = re.compile(
    rf"TST\s*-\s*{_NAO_PRECEDENTE}(?:[A-Za-z]+\s*-\s*)+({_CNJ})", re.I
)


def numero_tst(texto: str) -> str | None:
    """TST: rodapé `PROCESSO Nº TST-…`, senão `estes autos de … TST-…`.

    O número do TST **não** está no início do texto: o cabeçalho começa com a
    ementa, que cita a lei de regência (`EMBARGOS REGIDOS PELA LEI Nº
    13.015/2014`) e vários precedentes. Por isso aqui se busca no texto todo,
    mas só por padrões que identificam explicitamente o próprio processo.

    O último padrão é o mais frágil (qualquer `TST-CLASSE-número`), então usa a
    **primeira** ocorrência do texto: o próprio processo é apresentado antes de
    os precedentes serem discutidos.
    """
    for padrao in (_TST_RODAPE, _TST_AUTOS, _TST_QUALQUER):
        m = padrao.search(texto)
        if m:
            return so_digitos(m.group(1))
    return None


# Súmula: `Súmula n. 83 do STJ` / `Súmula Vinculante n. 10 do STF`.
# O número vira `S83` / `SV10` para não colidir com números de processo.
_SUMULA = re.compile(
    rf"S[uú]mula\s+(Vinculante\s+)?(?:{_NUM})?(\d{{1,4}})",
    re.I,
)


def numero_sumula(texto: str) -> str | None:
    """Súmula: devolve `S<n>` ou `SV<n>` (ADR-002)."""
    m = _SUMULA.search(texto[:JANELA_CABECALHO])
    if not m:
        return None
    prefixo = "SV" if m.group(1) else "S"
    return f"{prefixo}{int(m.group(2))}"


# Dispositivo de lei: `Artigo 93 da Constituição Federal de 1988`.
# O ordinal (`Artigo 7º`, `Art. 5º`) é comum nos artigos baixos da Constituição;
# o marcador de ordinal não entra no número.
_DISPOSITIVO = re.compile(
    r"Artigos?\s+(\d{1,4})\s*[ºo°º�]?(?:\s*-\s*[A-Z])?\s+(?:da|do|de)\s+(.+)",
    re.I,
)


def artigo_e_lei(texto: str) -> tuple[str, str] | None:
    """Dispositivo: devolve `(artigo, descrição da lei)` da primeira linha.

    A descrição bruta (`Lei nº 4.737, de 15 de julho de 1965`) é convertida em
    `lei_chave` pela tabela de apelidos (Tarefa 4).
    """
    primeira_linha = texto[:JANELA_CABECALHO].splitlines()[0] if texto else ""
    m = _DISPOSITIVO.match(primeira_linha.strip())
    if not m:
        return None
    return m.group(1), m.group(2).strip()


# Despacho por tribunal, usado pelo indexador.
PARSERS_ACORDAO = {
    "STJ": numero_stj,
    "STF": numero_stf,
    "STM": numero_cnj,
    "TSE": numero_tse,
    "TST": numero_tst,
}


def numero_proprio(tribunal: str | None, natureza: str, texto: str) -> str | None:
    """Número próprio de um registro, conforme a natureza e o tribunal."""
    if natureza == "sumula":
        return numero_sumula(texto)
    if natureza == "dispositivo":
        return None  # dispositivo é identificado por lei + artigo, não por número
    parser = PARSERS_ACORDAO.get(tribunal or "")
    return parser(texto) if parser else None
