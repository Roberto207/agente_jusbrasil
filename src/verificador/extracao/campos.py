"""Leitura de campos por regras. None → fila de difíceis."""

from __future__ import annotations

import re
import unicodedata

from dataclasses import replace

from verificador.contratos import Campos, Candidata
from verificador.extracao.padroes import MARCADOR_RELATOR, TRIBUNAL_EXTENSO, TST_NUMERO
from verificador.tabelas import classes_no_texto, ocr, resolver_lei, resolver_uf, tst_sigla
from verificador.texto.normalizacao import normalizar

# Campos que as regras não leram. Cada leitor preenche só o que achou (`replace`); `ler_campos`
# acerta `correcao_ocr` no fim, e `pipeline` usa a constante quando nada foi lido.
CAMPOS_VAZIOS = Campos(
    tribunal=None,
    classe_principal=None,
    cadeia_recursos=(),
    numero=None,
    uf=None,
    ano=None,
    relator=None,
    lei_chave=None,
    artigo=None,
    correcao_ocr=False,
    fonte="regras",
)

_DIGITO = re.compile(r"\d+")
_ANO = re.compile(r"\b(19|20)\d{2}\b")
_TRIBUNAL = re.compile(r"\b(STF|STJ|STM|TSE|TST)\b", re.IGNORECASE)
_UF_APOS_NUMERO = re.compile(
    r"\s*(?:/|-|\()\s*([A-Z]{2})\b",
    re.IGNORECASE,
)
# ADR-015: mesmo princípio do padrão de extração — marcador (que repete, porque `Rel. Min.` são dois)
# mais preenchimento curto, em vez de enumerar `relatoria de|rel. min.|sob relatoria de`. Sem isso,
# `relatada pelo Ministro X` é extraída mas não tem o relator lido, e cai em `campos_nao_lidos`.
# O preenchimento é preguiçoso e a captura começa em maiúscula de verdade (`(?-i:…)`, porque o
# IGNORECASE valeria para a classe toda): guloso, ele comia o início do nome — `Dias Toffoli` virava
# `s toffoli`.
# Marcador e preenchimento preguiçosos, e a captura começa em maiúscula de verdade (`(?-i:…)`, porque
# o IGNORECASE valeria para a classe toda). Gulosos, comiam o nome: `Dias Toffoli` virava `s toffoli`,
# e um relator chamado `Relator Exemplo` perdia o primeiro nome, porque `Relator` também é marcador.
# O título que sobrar na captura (`Min.`, `Ministro`) é removido por `normalizar_relator`.
_RELATOR = re.compile(
    rf"(?:{MARCADOR_RELATOR}[^;\d\n]{{0,7}}?){{1,3}}?((?-i:[A-ZÁÉÍÓÚÂÊÔÃÕÇ]).+)$",
    re.IGNORECASE | re.DOTALL,
)
_ARTIGO = re.compile(
    r"art(?:igo)?\.?\s*(\d+(?:\.\d+)?)º?",
    re.IGNORECASE,
)
_LEI_IDENT = re.compile(
    r"\bd[oa]s?\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_SUMULA_VINC = re.compile(r"vinculante", re.IGNORECASE)


def _sem_acento(texto: str) -> str:
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def normalizar_relator(nome: str) -> str:
    texto = _sem_acento(nome)
    # A mesma lista de títulos de `base/atributos.py`: os dois lados da comparação precisam normalizar
    # igual, senão a citação `Ministro X` nunca encontra o registro `MINISTRA X`.
    texto = re.sub(r"\b(?:MINISTR[OA]|MIN|DR|DRA|DES|JUIZ[AO]?)\b\.?", " ", texto, flags=re.IGNORECASE)
    texto = re.sub(r"[^A-Za-z\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip().lower()


def _digitos(texto: str) -> str:
    return "".join(_DIGITO.findall(texto))


def _tem_ocr_no_numero(texto: str) -> bool:
    tabela = ocr()
    for i, ch in enumerate(texto):
        if ch.isalpha() and ch in tabela:
            esq = i > 0 and texto[i - 1].isdigit()
            dir_ = i + 1 < len(texto) and texto[i + 1].isdigit()
            if esq or dir_:
                return True
    return False


def _numero_com_ocr(trecho: str, bruto: str) -> str | None:
    tabela = ocr()
    saida: list[str] = []
    for ch in bruto:
        if ch.isalpha() and ch in tabela:
            saida.append(tabela[ch])
        elif ch.isdigit():
            saida.append(ch)
    # A flag de correção de OCR não sai daqui: `ler_campos` a calcula sobre o trecho original.
    return "".join(saida) or _digitos(bruto) or _digitos(trecho) or None


_TRIBUNAL_POR_EXTENSO = tuple((sigla, re.compile(p, re.IGNORECASE)) for sigla, p in TRIBUNAL_EXTENSO.items())
_OJ = re.compile(r"^\s*(?:orienta[çc][ãa]o\s+jurisprudencial|oj)\b", re.IGNORECASE)


def _tribunal(texto: str) -> str | None:
    """Sigla do tribunal, escrita como sigla ou por extenso (`do colendo Superior Tribunal de Justiça`)."""
    m = _TRIBUNAL.search(texto)
    if m:
        return m.group(1).upper()
    return next((sigla for sigla, p in _TRIBUNAL_POR_EXTENSO if p.search(texto)), None)


def _uf_apos_numero(trecho: str, fim_numero: int) -> str | None:
    """UF escrita logo depois do número (`/RJ`, `- PR`, `(SP)`).

    Procurar em qualquer ponto do trecho lia o `-RR` de `TST-RR-…` como Roraima.
    """
    m = _UF_APOS_NUMERO.match(trecho, fim_numero)
    return resolver_uf(m.group(1)) if m else None


def _campos_com_numero(trecho: str) -> Campos | None:
    tema = re.search(r"tem[aã]\s+(\d+(?:\.\d+)?)\s+da\s+repercuss", trecho, re.I)
    if tema:
        # Tema de repercussão geral: o gabarito o trata como citação (e a base não tem temas).
        numero = _numero_com_ocr(trecho, tema.group(1))
        return replace(CAMPOS_VAZIOS, numero=numero)

    tst = TST_NUMERO.search(trecho)
    if tst:
        tokens = [t for t in tst.group("cadeia_tst").split("-") if t and t.upper() != "TST"]
        siglas = [sigla for t in tokens for sigla in tst_sigla(t)]
        numero = _numero_com_ocr(trecho, tst.group("numero_tst"))
        if not numero or not siglas:
            return None
        return replace(
            CAMPOS_VAZIOS,
            tribunal="TST",
            classe_principal=siglas[-1],
            cadeia_recursos=tuple(siglas[:-1]),
            numero=numero,  # uf fica vazia: o número CNJ do TST codifica a região, não a UF
        )

    m_num = re.search(
        r"(?<![A-Za-zÀ-ÿ])n[oº°.]?\s*(\d+(?:[.\-]\d+)*)|(\d+(?:[.\-]\d+)*)",  # `no` de "Interno" não é "nº"
        trecho,
        re.I,
    )
    # A classe e a cadeia vêm antes do número. Depois dele mora a UF, e `/RO` ou `/RR` seriam lidos
    # como Recurso Ordinário e Recurso de Revista (mesma armadilha do ADR-002, em outro campo).
    siglas = classes_no_texto(trecho[: m_num.start()] if m_num else trecho)
    if not siglas:
        return None
    bruto = (m_num.group(1) or m_num.group(2) or "") if m_num else ""
    numero = _numero_com_ocr(trecho, bruto)
    if not numero:
        return None
    principal = siglas[-1]
    cadeia = tuple(siglas[:-1])
    return replace(
        CAMPOS_VAZIOS,
        tribunal=_tribunal(trecho),
        classe_principal=principal,
        cadeia_recursos=cadeia,
        numero=numero,
        uf=_uf_apos_numero(trecho, m_num.end()) if m_num else None,
    )


def _campos_sumula(trecho: str) -> Campos | None:
    m = re.search(r"(\d+)", trecho)
    if not m:
        return None
    # No plural (`Súmulas 219 e 329`) vale o primeiro número. Orientação Jurisprudencial não é
    # súmula: `OJ<n>` não existe no índice e não casa por engano com a Súmula de mesmo número.
    if _OJ.search(trecho):
        numero, tribunal = f"OJ{m.group(1)}", "TST"
    else:
        vinc = bool(_SUMULA_VINC.search(trecho))
        numero, tribunal = (f"SV{m.group(1)}" if vinc else f"S{m.group(1)}"), _tribunal(trecho)
    return replace(CAMPOS_VAZIOS, tribunal=tribunal, numero=numero)


def _campos_lei(trecho: str) -> Campos | None:
    art = _ARTIGO.search(trecho)
    if not art:
        return None
    artigo = art.group(1).lstrip("0") or "0"
    if "." in artigo:
        artigo = artigo.replace(".", "")
    lei_m = _LEI_IDENT.search(trecho)
    identificador = lei_m.group(1).strip() if lei_m else ""
    lei_chave = resolver_lei(identificador) if identificador else None
    return replace(CAMPOS_VAZIOS, lei_chave=lei_chave, artigo=artigo)


def _campos_sem_numero(trecho: str) -> Campos | None:
    ano_m = _ANO.search(trecho)
    rel_m = _RELATOR.search(trecho)
    if not ano_m or not rel_m:
        return None
    relator = normalizar_relator(rel_m.group(1))
    if not relator:
        return None
    siglas = classes_no_texto(trecho)
    tribunal = _tribunal(trecho)
    if not tribunal and not siglas:
        return None
    return replace(
        CAMPOS_VAZIOS,
        tribunal=tribunal,
        classe_principal=siglas[-1] if siglas else None,
        cadeia_recursos=tuple(siglas[:-1]) if len(siglas) > 1 else (),
        ano=int(ano_m.group(0)),
        relator=relator,
    )


def _campos_referencia_vaga() -> Campos:
    """Sempre vazio: por definição, uma referência vaga não tem identificador nenhum para ler
    (ADR-005). Explícito (em vez de cair no `return None` genérico) para não entrar por engano
    na fila de difíceis/LLM quando `usar_llm=True` estiver ligado (Fase 4)."""
    return CAMPOS_VAZIOS


def ler_campos(c: Candidata) -> Campos | None:
    norm, _ = normalizar(c.trecho)
    if c.forma == "com_numero":
        campos = _campos_com_numero(norm)
        if campos is not None:
            return replace(campos, correcao_ocr=_tem_ocr_no_numero(c.trecho))
        return None
    if c.forma == "sumula":
        return _campos_sumula(norm)
    if c.forma == "lei_artigo":
        return _campos_lei(norm)
    if c.forma == "sem_numero":
        return _campos_sem_numero(norm)
    if c.forma == "referencia_vaga":
        return _campos_referencia_vaga()
    return None
