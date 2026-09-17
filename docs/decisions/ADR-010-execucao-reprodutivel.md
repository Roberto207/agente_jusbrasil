# ADR-010: Pacote reproduzível, repositório privado e artefatos públicos

**Status:** Aceito
**Data:** 2026-09-17
**Revisão:** 2026-09-17 — incorpora as regras completas: pesos e dados sintéticos em repositório
público com revisão fixa; Foundational Rules 5d/6b sobre compartilhamento de código.

## Contexto

Finalistas entregam repositório, README, referência dos modelos (link + revisão), ambiente
(`requirements`/`Dockerfile`) e o comando exato que reproduz as saídas submetidas. Pesos de
fine-tuning e dados usados no treino precisam ser públicos. Compartilhar código em particular fora
da equipe é proibido, e código só pode ser publicado no fórum do Kaggle durante a competição. Os
dados oficiais são privados e a base tem 90 MB.

## Decisão

- **Código**: repositório GitHub **privado** durante a competição, acesso só da equipe.
- **Pesos do encoder e dados sintéticos**: Hugging Face **público**, revisão fixa, publicados dentro
  do prazo; o código referencia link + revisão.
- **Dados oficiais**: fora do git (`.gitignore`); caminho da pasta é parâmetro.
- **Execução**: um comando gera `submission.csv`, relatório e manifesto; imagem Docker e
  `requirements.txt` com versões fixas (ADR-014).
- **Rastreio**: cada submissão tem tag git `sub-NNN`; o comando de submissão recusa árvore suja.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Repositório público durante a competição | Viola Foundational 6b |
| Pesos em link privado | Viola a regra de pesos públicos |
| Versionar os dados oficiais | Redistribui material privado; 90 MB |

## Consequências

### Positivas
Pacote pronto para a verificação; nada exposto fora das regras.

### Negativas
Publicar pesos e dados cedo ajuda outras equipes.

### Mitigação
Publicar perto do fim, mas dentro do prazo, com folga para conferir os links.
