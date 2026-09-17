# ADR-002: Índice da base pelo número próprio de cada registro

**Status:** Aceito
**Data:** 2026-09-17

## Contexto

A tabela `documentos` não tem coluna de número de processo. O número está no texto, em formato
diferente por tribunal (STJ `RECURSO ESPECIAL Nº 1.741.784 - PR`; STF `AG.REG. NA RECLAMAÇÃO
76.532 RIO DE JANEIRO`; STM e TSE em número CNJ; súmulas `Súmula n. 83 do STJ`; dispositivos
`Artigo 14 da Lei nº 8.078, de 11 de setembro de 1990`). No TST, o primeiro número do texto às
vezes é de um precedente citado — o confiável é o rodapé `PROCESSO Nº TST-ED-E-ED-RR-...`. A
própria base tem OCR ("TRIEUNAL"). Buscar o número por substring no texto dá falso positivo.

## Decisão

Um passo offline lê os 1.014 registros e grava uma tabela estruturada: número próprio
normalizado (só dígitos), classe processual, UF, tribunal, ano, relator, `id`; para súmulas,
número e tribunal; para dispositivos, lei canônica e artigo. Um parser por tribunal. O índice é
regenerado a partir do `.db`, nunca editado à mão.

## Alternativas Consideradas

| Alternativa | Razão da rejeição |
|---|---|
| Busca FTS5 pelo número no texto inteiro | Casa precedentes citados dentro de outros acórdãos |
| Primeiro número do texto | Falha no TST e em cabeçalhos com data e sessão |

## Consequências

### Positivas
Busca exata e barata; o índice é testável contra os 96 reais do gabarito.

### Negativas
Parser por tribunal é código frágil, sobretudo TST e TSE.

### Mitigação
Relatório de registros sem número extraído; meta de zero antes de integrar.
