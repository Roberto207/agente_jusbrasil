"""Fábrica de citações sintéticas: escolhe a citação e deduz o gabarito pelas regras (verdade.py)."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from verificador.base.indice import Indice
from verificador.sintetico import moldes
from verificador.sintetico.verdade import classificar, consistentes
from verificador.tabelas import ufs

TRIBUNAIS = ("STF", "STJ", "STM", "TSE", "TST")


@dataclass(frozen=True)
class Fabricada:
    texto: str
    tipo: str  # jurisprudencia | lei
    forma: str  # com_numero | sumula | lei_artigo | sem_numero
    classificacao: str
    id_canonico: str | None
    construcao: str  # como foi fabricada (para o relatório)


def milhar(digitos: str) -> str:
    grupos: list[str] = []
    while digitos:
        grupos.insert(0, digitos[-3:])
        digitos = digitos[:-3]
    return ".".join(grupos)


def cnj(digitos: str) -> str:
    return (
        f"{digitos[:-13]}-{digitos[-13:-11]}.{digitos[-11:-7]}."
        f"{digitos[-7]}.{digitos[-6:-4]}.{digitos[-4:]}"
    )


def _numero_do_artigo(n: int, rng: random.Random) -> str:
    if n < 10 and rng.random() < 0.5:
        return f"{n}º"
    return milhar(str(n)) if n >= 1000 else str(n)


class Fabrica:
    """Sorteia citações a partir dos registros da base. Tudo determinístico dado o `rng`."""

    PESOS = (
        ("real_acordao", 30), ("real_sumula", 4), ("real_lei", 10),
        ("inventada_numero", 12), ("emprestada", 8), ("ambigua", 4),
        ("sumula_inventada", 3), ("lei_inventada", 6), ("lei_desconhecida", 2),
        ("sem_numero", 15), ("tema", 2),
    )

    def __init__(self, indice: Indice) -> None:
        self.indice = indice
        regs = sorted(indice.registros, key=lambda r: r.id)
        self.acordaos = [r for r in regs if r.natureza == "acordao" and r.numero and r.classe_principal]
        self.sumulas = [r for r in regs if r.natureza == "sumula" and r.numero]
        self.dispositivos = [
            r for r in regs if r.natureza == "dispositivo" and r.lei_chave in moldes.NOMES_DE_LEI and r.artigo
        ]
        self.classes = sorted({r.classe_principal for r in self.acordaos})  # type: ignore[misc]
        self.ufs = sorted(ufs())
        self.relatores = sorted({r.relator.title() for r in self.acordaos if r.relator})
        por_numero: dict[str, list] = defaultdict(list)
        for r in self.acordaos:
            por_numero[r.numero].append(r)  # type: ignore[index]
        self.repetidos = sorted(n for n, rs in por_numero.items() if len(rs) >= 2)
        self._por_numero = por_numero

    # -- utilidades -----------------------------------------------------------------------

    def _nome(self, sigla: str, rng: random.Random) -> str:
        longo = moldes.NOME_LONGO.get(sigla)
        return longo if longo and rng.random() < 0.4 else sigla

    def _numero(self, digitos: str, rng: random.Random) -> str:
        if len(digitos) >= 14:
            return cnj(digitos)
        return milhar(digitos) if rng.random() < 0.7 and len(digitos) > 3 else digitos

    def _render(
        self, rng: random.Random, tribunal: str, numero: str, classe: str,
        cadeia: tuple[str, ...], uf: str | None, forcar_uf: bool = False,
    ) -> tuple[str, dict]:
        """Texto da citação e os atributos que ela declara explicitamente."""
        if tribunal == "TST":
            prefixo = "TST-" if rng.random() < 0.8 else ""
            texto = prefixo + "-".join([*cadeia, classe]) + "-" + cnj(numero)
            return texto, {"tribunal": "TST" if prefixo else None, "uf": None, "classe": classe, "cadeia": cadeia}
        cabeca = " no ".join(self._nome(c, rng) for c in [*cadeia, classe])
        no = rng.choice(["nº", "n.", "n°", ""])
        texto = f"{cabeca} {no} {self._numero(numero, rng)}".replace("  ", " ")
        declarada = None
        if uf and (forcar_uf or rng.random() < 0.7):
            texto += rng.choice([f"/{uf}", f" - {uf}", f" ({uf})"])
            declarada = uf
        return texto, {"tribunal": None, "uf": declarada, "classe": classe, "cadeia": cadeia}

    def _fabricar_acordao(self, construcao: str, texto: str, attrs: dict, numero: str) -> Fabricada:
        candidatos = self.indice.por_numero(numero)
        classe, id_ = classificar(candidatos, consistentes(candidatos, **attrs))
        return Fabricada(texto, "jurisprudencia", "com_numero", classe, id_, construcao)

    # -- tipos de citação -----------------------------------------------------------------

    def real_acordao(self, rng: random.Random) -> Fabricada:
        r = rng.choice(self.acordaos)
        texto, attrs = self._render(rng, r.tribunal, r.numero, r.classe_principal, r.cadeia_recursos, r.uf)  # type: ignore[arg-type]
        return self._fabricar_acordao("real_acordao", texto, attrs, r.numero)  # type: ignore[arg-type]

    def inventada_numero(self, rng: random.Random) -> Fabricada:
        molde = rng.choice(self.acordaos)
        while True:
            n = len(molde.numero)  # type: ignore[arg-type]
            novo = str(rng.randint(1, 9)) + "".join(rng.choice("0123456789") for _ in range(n - 1))
            if not self.indice.por_numero(novo):
                break
        texto, attrs = self._render(rng, molde.tribunal, novo, molde.classe_principal, molde.cadeia_recursos, molde.uf)  # type: ignore[arg-type]
        return self._fabricar_acordao("inventada_numero", texto, attrs, novo)

    def emprestada(self, rng: random.Random) -> Fabricada:
        """Número que existe, com classe (ou UF) que contradiz os registros dele (R40)."""
        r = rng.choice(self.acordaos)
        registros = self._por_numero[r.numero]  # type: ignore[index]
        if r.uf and r.tribunal != "TST" and rng.random() < 0.5:
            outra = rng.choice(sorted(set(self.ufs) - {x.uf for x in registros if x.uf}))
            texto, attrs = self._render(rng, r.tribunal, r.numero, r.classe_principal, r.cadeia_recursos, outra, True)  # type: ignore[arg-type]
        else:
            classe = rng.choice(sorted(set(self.classes) - {x.classe_principal for x in registros}))
            texto, attrs = self._render(rng, r.tribunal, r.numero, classe, (), r.uf)  # type: ignore[arg-type]
        return self._fabricar_acordao("emprestada", texto, attrs, r.numero)  # type: ignore[arg-type]

    def ambigua(self, rng: random.Random) -> Fabricada:
        """Número de recursos internos do mesmo processo, citado só pela classe (R7)."""
        numero = rng.choice(self.repetidos)
        r = rng.choice(self._por_numero[numero])
        texto, attrs = self._render(rng, r.tribunal, numero, r.classe_principal, (), None)  # type: ignore[arg-type]
        return self._fabricar_acordao("ambigua", texto, attrs, numero)

    def real_sumula(self, rng: random.Random) -> Fabricada:
        r = rng.choice(self.sumulas)
        vinculante = r.numero.startswith("SV")  # type: ignore[union-attr]
        n, trib = r.numero.lstrip("SV"), r.tribunal  # type: ignore[union-attr]
        if vinculante:
            texto, declarado = rng.choice([(f"Súmula Vinculante {n} do {trib}", trib), (f"Súmula Vinculante {n}", None)])
        else:
            texto, declarado = rng.choice(
                [(f"Súmula {n} do {trib}", trib), (f"Súmula n. {n} do {trib}", trib), (f"SÚMULA {n} do {trib}", trib)]
            )
        candidatos = self.indice.por_numero(r.numero)  # type: ignore[arg-type]
        classe, id_ = classificar(candidatos, consistentes(candidatos, tribunal=declarado))
        return Fabricada(texto, "jurisprudencia", "sumula", classe, id_, "real_sumula")

    def sumula_inventada(self, rng: random.Random) -> Fabricada:
        if rng.random() < 0.5:  # existente, mas de outro tribunal
            r = rng.choice(self.sumulas)
            n, trib = r.numero.lstrip("SV"), rng.choice(sorted(set(TRIBUNAIS) - {r.tribunal}))  # type: ignore[union-attr,arg-type]
            numero = r.numero
        else:
            while True:
                n = str(rng.randint(1, 999))
                if not self.indice.por_numero(f"S{n}"):
                    break
            trib, numero = rng.choice(TRIBUNAIS), f"S{n}"
        candidatos = self.indice.por_numero(numero)  # type: ignore[arg-type]
        classe, id_ = classificar(candidatos, consistentes(candidatos, tribunal=trib))
        return Fabricada(f"Súmula {n} do {trib}", "jurisprudencia", "sumula", classe, id_, "sumula_inventada")

    def _texto_lei(self, rng: random.Random, artigo: int, chave: str) -> str:
        definido, nome = rng.choice(moldes.NOMES_DE_LEI[chave])
        rotulo = rng.choice(["art.", "artigo", "art"])
        complemento = rng.choice(moldes.COMPLEMENTOS_DE_ARTIGO)
        return f"{rotulo} {_numero_do_artigo(artigo, rng)}{complemento} {definido} {nome}"

    def real_lei(self, rng: random.Random) -> Fabricada:
        r = rng.choice(self.dispositivos)
        candidatos = self.indice.por_lei_artigo(r.lei_chave, r.artigo)  # type: ignore[arg-type]
        classe, id_ = classificar(candidatos, candidatos)
        return Fabricada(self._texto_lei(rng, int(r.artigo), r.lei_chave), "lei", "lei_artigo", classe, id_, "real_lei")  # type: ignore[arg-type]

    def lei_inventada(self, rng: random.Random) -> Fabricada:
        chave = rng.choice(sorted(moldes.NOMES_DE_LEI))
        while True:
            artigo = rng.randint(1, 2100)
            if not self.indice.por_lei_artigo(chave, str(artigo)):
                break
        return Fabricada(self._texto_lei(rng, artigo, chave), "lei", "lei_artigo", "inventada", None, "lei_inventada")

    def lei_desconhecida(self, rng: random.Random) -> Fabricada:
        numero, ano = rng.randint(1000, 99999), rng.randint(1950, 2024)
        texto = f"art. {rng.randint(1, 400)} da Lei nº {milhar(str(numero))}/{ano}"
        return Fabricada(texto, "lei", "lei_artigo", "inventada", None, "lei_desconhecida")

    def sem_numero(self, rng: random.Random) -> Fabricada:
        texto = rng.choice(moldes.MOLDES_SEM_NUMERO).format(
            trib=rng.choice(TRIBUNAIS), ano=rng.randint(2009, 2025),
            rel=rng.choice(self.relatores), classe=rng.choice(["Rcl", "HC", "REsp", "RE"]),
        )
        return Fabricada(texto, "jurisprudencia", "sem_numero", "incompleta", None, "sem_numero")

    def tema(self, rng: random.Random) -> Fabricada:
        n = rng.randint(1, 1300)
        texto = f"Tema {milhar(str(n))} da repercussão geral"
        return Fabricada(texto, "jurisprudencia", "com_numero", "inventada", None, "tema")

    def sortear(self, rng: random.Random) -> Fabricada:
        nomes, pesos = zip(*self.PESOS)
        return getattr(self, rng.choices(nomes, pesos)[0])(rng)
