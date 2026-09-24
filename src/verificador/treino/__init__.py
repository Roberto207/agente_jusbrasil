"""Treino do encoder NER (ADR-011): montagem do dataset, rótulos BIO e janelas.

Nada aqui roda na execução que produz a submissão. O dataset sai como JSONL de spans por caractere,
sem depender de tokenizador; a tokenização e os rótulos BIO acontecem no notebook de treino, com o
tokenizador do modelo escolhido (`bio.py` tem as funções puras que ele usa).
"""
