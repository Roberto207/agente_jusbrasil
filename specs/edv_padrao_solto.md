# Spec — o padrão solto do alias `EDv`

**Data:** 2026-09-21 · **ADR:** 009 (protocolo anti-overfitting), 015 (âncoras na forma (d))
**Status:** implementada · **Commit de origem:** `7b3ea35` (fix do `gen_n2_010`, da Beatriz)

## Objetivo

Tirar um padrão de classe que capturava prosa corrente, sem perder a correção do `gen_n2_010` que
ele estava sustentando por acidente.

## Contexto

O commit `7b3ea35` acrescentou o alias `EDv` a `classes.json` e resolveu o `gen_n2_010`:
**amostra 1,08603 → 1,09648** e **controle 1,10000** (teto exato). O ganho é real e bem fundamentado —
são 11 registros da base com "Embargos de Divergência", e sem a classe o índice lia
`AgInt nos EMBARGOS DE DIVERGÊNCIA EM RESP` e `AgInt no RECURSO ESPECIAL` como o mesmo `REsp`+`AgInt`,
fabricando um empate onde não havia.

Mas o alias veio com três padrões, e o do meio era problemático.

## Bug: `diverg[eê]ncia em` capturava prosa comum

### Causa raiz

`src/verificador/tabelas/classes.json`, alias `EDv`, padrão `"diverg[eê]ncia em"`. Como a expressão
inclui a preposição, o que vem depois dela é lido como número do processo:

| Entrada | Efeito medido |
|---|---|
| `houve divergência em 2024 sobre o tema` | vira citação falsa `divergência em 2024` |
| `a divergência em 1.234.567 casos analisados` | vira citação falsa |
| `havendo divergência em torno do REsp 1.234.567` | cadeia lida como `['EDv','REsp']` |

O terceiro é o pior: `_classes_no_texto` usa a mesma tabela, então a cadeia de uma citação legítima
fica contaminada, o filtro de consistência rejeita o registro certo e uma `real` vira `inventada`.
Nenhum disparou nos conjuntos atuais (precisão 1,0), mas o conjunto cego é onde morderia.

### A classe do problema

É a mesma família que o ADR-015 combate na forma (d): **vocabulário amplo sem exigência estrutural**.
A diferença é que aqui o estrago é maior, porque a tabela de classes alimenta três consumidores —
extração, leitura de campos e indexação da base.

### O que a investigação revelou (e que não era óbvio)

Remover o padrão solto **quebrou** o `gen_n2_010` de volta. Motivo: o cabeçalho real de 4 registros da
base vem **sem espaço** — `AgInt nosEMBARGOS DE DIVERGÊNCIA EM RESP`. O padrão de classe é embrulhado
em `(?<![A-Za-z])…(?![A-Za-z])` por `_padrao_classe()`, e esse guarda barra `EMBARGOS` quando ele
encosta em `nos`. O padrão solto casava porque `DIVERGÊNCIA` vinha depois de um espaço.

Ou seja: **o padrão errado estava fazendo o trabalho certo pelo motivo errado.**

Varri os cabeçalhos: são só 6 ocorrências de "minúscula colada em MAIÚSCULAS", 4 delas `sEMBARGOS`.
Um normalizador geral de cabeçalho seria mais elegante, mas mexe no parser compartilhado por um ganho
de 4 registros — desproporcional.

### Fix aplicado

```json
{"sigla": "EDv", "padroes": ["nos?\\s*embargos de diverg[eê]ncia",
                             "embargos de diverg[eê]ncia", "\\bedv\\b"]}
```

O primeiro padrão tolera o prefixo colado: `nos` vem depois de espaço, então passa pelo guarda, e
`\s*` aceita tanto `nosEMBARGOS` quanto `nos EMBARGOS`. Vocabulário continua ancorado em
"embargos de divergência" — nada de preposição solta.

## O que NÃO foi feito, de propósito

**Regra de desempate para o `gen_n2_005`**, que fecharia os 0,00352 restantes até 1,100.

A aritmética é tentadora: o nível 1 já tem Brier zero, e o Brier do nível 2 é 0,010753 com 93
citações — `1/93 = 0,010753`. Corrigir aquele único link levaria macro-F1 a 1,0 **e** Brier a 0 de
uma vez, chegando em 1,100 exato.

Mas a base empírica não existe:

- só **2** citações `real` da amostra inteira têm número com mais de um registro na base;
- uma delas (`gen_n2_010`) já foi resolvida pela classe `EDv`;
- sobra **n=1**.

A regra "escolher o registro mais antigo" acerta 2/2 — e "classe mais próxima", "menor id" e várias
outras também acertam 2/2. Com um exemplo efetivo, a regra é infalsificável. É exatamente o que o
**ADR-009** proíbe, e o mesmo erro que suspeitamos das equipes em 1,09999 no leaderboard.

Segue como pergunta à organização (ideia D de `docs/gerais/limites_de_decisao.md`): quando vários
registros dividem o número do processo, o vínculo é ao **caso** ou ao **estágio recursal**?

## Verificação

```bash
pytest                                     # 149
python -m verificador gerar-sintetico --dados desafio-jusbrasil-bracis-2026 --saida sintetico/ --pares 100 --semente 0
python -m verificador rodar/avaliar        # amostra e sintético
```

| Conjunto | Antes do fix | Depois |
|---|---|---|
| Amostra | 1,09648 · 192/192 | **1,09648 · 192/192** |
| Controle | 1,10000 | **1,10000** |
| Sintético | 1,09571 · 988/994 | **1,09571 · 988/994** |

Precisão de spans 1,0, zero espúrios e τ=0 em todos os conjuntos; R49 determinístico nos dois.
O fix é neutro em nota e remove risco — era esse o objetivo.

Testes novos: `test_edv_nao_captura_prosa_comum`, `test_edv_reconhecido_mesmo_colado_no_conector`
(`tests/test_extracao.py`); `test_edv_nao_entra_na_cadeia_por_prosa`,
`test_edv_legitimo_entra_na_cadeia` (`tests/test_campos.py`).
