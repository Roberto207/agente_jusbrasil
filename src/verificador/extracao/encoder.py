"""Encoder NER como rede de segurança ao lado do regex (ADR-011, decisão de 24/09).

O encoder só **acrescenta** candidatas onde o regex não achou nada. Cada span previsto passa por
portas, nesta ordem; se falhar em uma, é descartado:

0. começa no corpo, não no cabeçalho (números de autos e protocolo são distratores, R34);
1. nenhuma candidata do regex se sobrepõe a ele — onde o regex achou algo, o regex manda;
2. tem dígito **e** uma âncora: súmula/enunciado/verbete/OJ (nunca "enunciado administrativo", que
   não é súmula), classe processual, ou artigo **com a lei identificada** (`da Lei …`, `do CPC`) —
   artigo solto (`ARTIGO 3º, CAPUT`) é referência vaga, não citação;
3. `ler_campos` consegue ler os campos na forma escolhida (senão a decisão não teria o que consultar).

A consequência é estrutural: com o encoder ligado, nada do que o regex já acha muda. O risco é só
falso positivo novo, medido nos distratores (critério 3 do go/no-go).

A inferência é a mesma função do treino (`treino.treinar.prever`): o que roda aqui é o que foi
medido no Kaggle. `torch` e `transformers` só são importados quando o encoder é carregado.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from verificador.contratos import Candidata, TextoPreparado
from verificador.extracao.campos import _classes_no_texto, ler_campos
from verificador.texto.normalizacao import normalizar

_ANCORA_SUMULA = re.compile(
    r"s[úu]mula|enunciado|verbete|orienta[çc][ãa]o\s+jurisprudencial|(?<![A-Za-z])OJ(?![A-Za-z])", re.IGNORECASE
)
_ANCORA_ARTIGO = re.compile(r"^art(?:igo)?s?\.?\s*\d", re.IGNORECASE)
_LEI_NOMEADA = re.compile(r"\bd[oa]s?\s+[A-Za-zÀ-ÿ]", re.IGNORECASE)
_ADMINISTRATIVO = re.compile(r"administrativ", re.IGNORECASE)


def _forma(trecho: str, rotulo: str) -> str | None:
    """Porta 2: a forma que o trecho tem, ou None se ele não tem dígito e âncora."""
    if not any(ch.isdigit() for ch in trecho):
        return None
    if rotulo == "LEI":
        return "lei_artigo" if _ANCORA_ARTIGO.search(trecho) and _LEI_NOMEADA.search(trecho) else None
    if _ANCORA_SUMULA.search(trecho):
        return None if _ADMINISTRATIVO.search(trecho) else "sumula"
    return "com_numero" if _classes_no_texto(normalizar(trecho)[0]) else None


def _aparar(texto: str, inicio: int, fim: int) -> tuple[int, int]:
    """Tira espaço e pontuação solta das bordas (o span vem de tokens, e `, ` pode sobrar)."""
    while inicio < fim and (texto[inicio].isspace() or texto[inicio] in ",;:("):
        inicio += 1
    while fim > inicio and (texto[fim - 1].isspace() or texto[fim - 1] in ",;:)"):
        fim -= 1
    return inicio, fim


def candidatas_do_encoder(
    t: TextoPreparado, spans: Sequence[tuple[int, int, str]], regex: Sequence[Candidata]
) -> list[Candidata]:
    """Aplica as portas 0–3 aos spans previstos (offsets no texto original)."""
    saida: list[Candidata] = []
    for bruto_ini, bruto_fim, rotulo in spans:
        inicio, fim = _aparar(t.original, bruto_ini, bruto_fim)
        if inicio >= fim or inicio < t.corpo_inicio:
            continue
        if any(c.inicio < fim and c.fim > inicio for c in regex):
            continue
        trecho = t.original[inicio:fim]
        forma = _forma(trecho, rotulo)
        if forma is None:
            continue
        cand = Candidata(
            inicio=inicio,
            fim=fim,
            trecho=trecho,
            tipo="lei" if forma == "lei_artigo" else "jurisprudencia",
            forma=forma,  # type: ignore[arg-type]
            padrao="encoder",
            origem=frozenset({"encoder"}),
        )
        if ler_campos(cand) is not None:
            saida.append(cand)
    return saida


class Encoder:
    """Modelo ajustado carregado em CPU (R49: inferência determinística, sem GPU)."""

    def __init__(self, link: str, revisao: str | None = None, *, threads: int = 4) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        from verificador.treino.treinar import Config

        torch.manual_seed(0)
        torch.set_num_threads(threads)
        torch.use_deterministic_algorithms(True)
        self._torch = torch
        self._dispositivo = torch.device("cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(link, revision=revisao)
        self.modelo = AutoModelForTokenClassification.from_pretrained(link, revision=revisao).eval()
        self._cfg = Config(modelo=link, revisao=revisao or "")

    def spans(self, texto: str) -> list[tuple[int, int, str]]:
        from verificador.treino.treinar import prever

        return prever(self.modelo, self.tokenizer, texto, self._cfg, self._dispositivo)
