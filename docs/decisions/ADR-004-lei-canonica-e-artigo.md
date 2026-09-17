# ADR-004: Citação de lei resolvida por (lei canônica, artigo)

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

A base tem 13 dispositivos, no nível de artigo (`Artigo 373 da Lei nº 13.105, de 16 de março de
2015`). Os pareceres citam a mesma lei de formas diferentes — `CPC`, `Código de Processo Civil`,
`Lei nº 13.105/2015`; `CLT`, `Consolidação das Leis do Trabalho`; `Constituição da República`,
`Constituição Federal` — e com inciso, parágrafo ou alínea (`art. 1º, I, 'g', da Lei
Complementar nº 64/1990`). Na amostra, as 28 citações de lei seguem a regra: lei + artigo na base
→ real; fora → inventada.

## Decisão

Uma tabela versionada de apelidos leva nome, sigla e número de lei a uma chave canônica (tipo +
número + ano: `LEI-13105-2015`, `DL-5452-1943`, `CF-1988`). A resolução usa só (chave, número do
artigo); inciso, parágrafo e alínea ficam no span mas fora da chave. A tabela cobre os principais
códigos federais, não só os 13 da base, para que um artigo inexistente de lei conhecida vire
`inventada` e não "não reconhecido".

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Comparar o texto da citação com o cabeçalho do dispositivo | Não casa `CPC` com `Lei nº 13.105` |
| Chave incluindo inciso | A base não tem inciso; `art. 93, IX` é real no gabarito |

## Consequências

### Positivas
Resolução exata e explicável.

### Negativas
Lei citada só por um apelido fora da tabela não é reconhecida.

### Mitigação
Relatório de "lei não reconhecida" no dump de erros; a tabela cresce por evidência.
