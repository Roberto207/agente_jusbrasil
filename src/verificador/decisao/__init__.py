"""Frente D — decisão: classe e id de cada citação, a partir dos campos lidos e do índice."""

from verificador.decisao.caminhos import CAMINHOS_DECISAO, CLASSE_DO_CAMINHO, consistentes
from verificador.decisao.decidir import decidir
from verificador.decisao.llm import ler_campos_llm, numero_do_llm_valido

__all__ = [
    "decidir",
    "consistentes",
    "CLASSE_DO_CAMINHO",
    "CAMINHOS_DECISAO",
    "ler_campos_llm",
    "numero_do_llm_valido",
]
