"""Frente C — saída: JSON por documento e validação do contrato."""

from verificador.saida.escrever import citacao_para_json, escrever_json
from verificador.saida.validar import ErroDeSaida, validar_citacoes

__all__ = ["escrever_json", "citacao_para_json", "validar_citacoes", "ErroDeSaida"]
