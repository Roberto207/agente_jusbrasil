"""Frente A — índice da base canônica (`DESIGN.md`, etapa [A]).

Fronteira pública consumida pelas outras frentes:

    indexar(caminho_db) -> list[RegistroIndice]     # contrato do DESIGN.md
    construir_indice(caminho_db) -> Indice          # + consultas
    Indice.por_numero(digitos) -> list[RegistroIndice]
    Indice.por_lei_artigo(lei_chave, artigo) -> list[RegistroIndice]
"""

from verificador.base.indice import Indice, construir_indice, indexar

__all__ = ["Indice", "construir_indice", "indexar"]
