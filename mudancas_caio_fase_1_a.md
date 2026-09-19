# Mudanças — Fase 1, Frente A (Índice da base)

**Autor:** Caio · **Branch:** `frente-a-indice` · **Início:** 2026-09-18
**Plano de origem:** `tarefas_equipe.md`, seção "Fase 1 — Frente A"
**Entrega prometida:** `indexar(caminho_db) -> list[RegistroIndice]`, `por_numero()`, `por_lei_artigo()`

Este documento registra, tarefa por tarefa, **o que foi feito e por quê**. Serve como documentação de
apoio para a revisão do PR e para quem for mexer no índice depois.

---

## Preparação (antes da Tarefa 1)

| O que | Detalhe |
|---|---|
| Branch criado | `frente-a-indice`, a partir de `main` (regra 2 de convivência) |
| Pasta de dados montada | `desafio-jusbrasil-bracis-2026/` com `desafio1_bracis.db`, `goldenset_offsets.csv`, `json_to_submission.py`, `kaggle_metric.py`, `sample_submission.csv` e `txt/` (26 arquivos) |

Os dados oficiais estavam soltos na pasta-pai do repositório. Foram copiados para o caminho que o
código espera. A pasta está no `.gitignore` — **não entra no git**, como manda o `DESIGN.md`.

---

## Tarefa 1 — Explorar a base ✅

**O que o plano pedia:** abrir o `.db`, contar registros por `natureza` e `tribunal`, ler 3–5
cabeçalhos de cada tipo e anotar as variações de formato encontradas.

**O que foi feito:** exploração por consultas SQL e leitura de cabeçalhos reais. Nenhum código de
produção nesta tarefa — a entrega é **conhecimento registrado**, que define o desenho dos parsers da
Tarefa 2.

### 1.1 Composição da base

Total: **1.014 registros**.

| natureza | tipo | quantidade |
|---|---|---|
| `acordao` | jurisprudencia | 996 |
| `dispositivo` | lei | 13 |
| `sumula` | jurisprudencia | 5 |

Acórdãos por tribunal: **STM 200 · STF 200 · TSE 199 · STJ 199 · TST 198**. A base é equilibrada —
nenhum tribunal pode ser deixado de lado.

Outros números: `ano` vai de 2009 a 2026, com **18 nulos** (são exatamente os 13 dispositivos + 5
súmulas; todo acórdão tem ano). `relator` tem 21 nulos. `texto_len` varia de 264 a 149.907
caracteres (média ~66 mil).

### 1.2 Quanto o gabarito realmente cobra

Consulta cruzando `goldenset_offsets.csv` com a base:

- 192 citações: **96 `real`**, 64 `inventada`, 32 `incompleta` (bate com o plano).
- As 96 reais apontam para **95 ids distintos** — e **todos os 95 existem na base**.

Distribuição dos ids cobrados:

| Fonte | Ids cobrados |
|---|---|
| STJ acórdão | 44 |
| dispositivo de lei | 13 |
| STM acórdão | 11 |
| TSE acórdão | 10 |
| TST acórdão | 10 |
| STJ súmula | 3 |
| STF acórdão | 2 |
| STF súmula / TST súmula | 1 / 1 |

**Consequência de prioridade:** STJ (44) e dispositivos de lei (13) valem mais da metade dos ids
cobrados. STF acórdão vale 2. Se o tempo apertar, é por aí que se começa.

### 1.3 Formato do número próprio por fonte — o que foi observado

Cabeçalhos reais lidos direto da base:

**STJ** — número após o primeiro `Nº`, com UF por sigla:
```
RECURSO ESPECIAL Nº 1.741.784 - PR (2018/0116304-1) RELATOR : MINISTRO JOEL ILAN PACIORNIK
AgRg no AGRAVO EM RECURSO ESPECIAL Nº 1.327.863 - PR (2018/0169803-4) ...
AgInt no AgInt no RECURSO ESPECIAL Nº 1.640.323 - RS (2016/0309036-2) ...
```
⚠️ **Variação encontrada:** nem todo número tem pontuação — `Nº 2124716 - MG`, `Nº 891369 - RS`,
`Nº 104595 - PR`. Um padrão que exija `\d.\d{3}` perde ~76 dos 199 registros.

**STF** — sem `Nº`, número seguido da UF **por extenso**:
```
22/04/2026 PRIMEIRA TURMA AG.REG. NA RECLAMAÇÃO 76.532 RIO DE JANEIRO RELATOR : MIN. CRISTIANO ZANIN
07/10/2024 PRIMEIRA TURMA AG.REG. NA RECLAMAÇÃO 67.634 DISTRITO FEDERAL ...
```
A UF vem como `RIO DE JANEIRO`, `SÃO PAULO`, `BAHIA` — a citação no parecer virá como `/RJ`. É a
justificativa direta da tabela de UFs (Tarefa 4).

**STM** — número CNJ, cabeçalho com dois formatos de abertura:
```
Poder Judiciário STM EXTRATO DE ATA ... EMBARGOS INFRINGENTES E DE NULIDADE Nº 7000380- 08.2023.7.00.0000/DF
Secretaria do Tribunal Pleno AGRAVO INTERNO Nº 7000451-78.2021.7.00.0000 ...
```
⚠️ **Variação:** `7000380- 08.2023...` tem **espaço no meio do número**.

**TSE** — número CNJ ou número curto entre parênteses:
```
TRIBUNAL SUPERIOR ELEITORAL ACÓRDÃO AGRAVO REGIMENTAL NO RECURSO ESPECIAL ELEITORAL Nº 310-76.2016.6.16.0006 CLASSE 32ª ...
TRIBUNAL SUPERIOR ELEITORAL ACÓRDÃO RECURSO ESPECIAL ELEITORAL Nº 36.038 ( 43342-43.2009.6.00.0000) -CLASSE 32ª ...
```
⚠️ **Variações:** número quebrado por espaço (`839-42. 2010.6.19.0000`), número **sem pontuação**
(`3112-8520146070000`), e `N o` no lugar de `Nº`.

**TST — o caso mais complicado da base.** Medição da cobertura de cada padrão:

| Padrão | Cobertura |
|---|---|
| rodapé `PROCESSO Nº TST-…` | **11** de 198 |
| + `estes autos de … nº TST-<classe>-<número>` | +88 |
| + qualquer `TST-<classe>-<número>` no texto | +68 |
| sem nenhum dos três | **31** |

O `DESIGN.md` diz "rodapé `PROCESSO Nº TST-...`". **Isso cobre só 11 de 198 registros.** O padrão
realmente dominante é `Vistos, relatados e discutidos estes autos de … nº TST-AIRR-25823-78.2015.5.24.0091`.

Exemplo concreto (`doc_0729`, id `1974934139`, cobrado pelo gabarito): o número próprio está na
posição 4.309 do texto, e **dois outros números de processo aparecem antes dele** (posições 1.506 e
2.914, ambos precedentes citados). Pegar "o primeiro número do texto" erraria este registro.

Dos 10 acórdãos do TST cobrados pelo gabarito, 9 têm o rodapé e 1 (`doc_0729`) só tem a forma
"estes autos de". **Os dois padrões são necessários.**

**Súmulas** — formato limpo e regular:
```
Súmula n. 83 do STJ
Súmula n. 211 do STJ
Súmula Vinculante n. 10 do STF
Súmula n. 331 do TST
```

**Dispositivos de lei** — formato regular, `Artigo N da|do <lei>`:
```
Artigo 93 da Constituição Federal de 1988
Artigo 276 da Lei nº 4.737, de 15 de julho de 1965
Artigo 290 do Decreto-Lei nº 1.001, de 21 de outubro de 1969
Artigo 14 da Lei nº 8.078, de 11 de setembro de 1990
```

### 1.4 Achados que mudam o planejamento

1. **A própria base tem ruído de OCR.** Encontrados `TRIEUNAL SUPERIOR ELEITORAL` (doc_0401),
   `TRE3UNAL` e `N o` (doc_0424), `J SUPERIOR TRIBUNAL MILITAR` (doc_0952). O ruído não está só nos
   documentos de Nível 2 — está na base de referência. Os parsers precisam tolerar isso.

2. **A regra do TST no `DESIGN.md` está incompleta** (11/198). Precisa de um segundo padrão. Isso
   será registrado como nota no PR.

3. **Números sem pontuação são comuns** no STJ e no TSE. Reduzir tudo a dígitos na comparação (como
   o `DESIGN.md` já prevê) resolve — desde que o *parser* também aceite a forma sem pontos.

4. **Não confundir com número de lei.** Cabeçalhos do TST trazem `EMBARGOS REGIDOS PELA LEI Nº
   13.015/2014` logo no começo. Um padrão que procure "primeiro número após `Nº`" pegaria o número
   da lei. (Isso explica os 86 registros com "número próprio" `13.015` medidos na exploração inicial.)

5. **31 acórdãos do TST não têm número recuperável** por nenhum dos padrões. Nenhum deles é cobrado
   pelo gabarito — serão listados e justificados no teste "zero registro sem número próprio", como o
   plano permite ("exceto os que legitimamente não têm — listar e justificar").

---

## Tarefa 2 — Parser de número próprio por fonte ✅

**Arquivo criado:** `src/verificador/base/numero_proprio.py`

**O que o plano pedia:** um parser por fonte (STJ, STF, STM/TSE, TST, súmula, dispositivo), cada um
lendo o número do *próprio* registro — nunca o de um precedente citado (ADR-002).

### Como foi feito

O módulo expõe uma função por fonte e um despachante `numero_proprio(tribunal, natureza, texto)`.
Duas decisões de desenho atravessam todas elas:

**1. Janela de cabeçalho.** Os parsers de acórdão olham só os primeiros **400 caracteres**
(`JANELA_CABECALHO`). É o que separa "o número deste registro" de "números citados no corpo" — a
armadilha do ADR-002. O TST é a exceção justificada abaixo.

**2. Tudo vira dígitos.** `so_digitos()` reduz `1.741.784`, `1741784` e `1 741 784` ao mesmo
`1741784`. É a forma canônica de comparação usada pelo índice inteiro.

### Os parsers

| Fonte | Âncora usada | Exemplo |
|---|---|---|
| STJ | `Nº <número> - <UF>` | `RECURSO ESPECIAL Nº 1.741.784 - PR` |
| STF | `<número> <UF por extenso> RELATOR` | `RECLAMAÇÃO 76.532 RIO DE JANEIRO RELATOR :` |
| STM | primeiro número CNJ do cabeçalho | `Nº 7000380- 08.2023.7.00.0000/DF` |
| TSE | CNJ → número curto → fallback ruidoso | `Nº 310-76.2016.6.16.0006` |
| TST | rodapé → `estes autos de …` → qualquer `TST-CLASSE-nº` | `PROCESSO Nº TST-ED-E-ED-RR-3400-05…` |
| Súmula | `Súmula [Vinculante] n. N` → `S83` / `SV10` | `Súmula Vinculante n. 10 do STF` |
| Dispositivo | `Artigo N da|do <lei>` | `Artigo 93 da Constituição Federal de 1988` |

**Por que o STF não usa `Nº`:** o cabeçalho do STF simplesmente não tem esse marcador. O que delimita
o número é a UF por extenso seguida de `RELATOR`. O parser normaliza acentos antes de casar, porque
`SÃO PAULO` e `CEARÁ` aparecem acentuados.

**Por que o TST varre o texto todo:** o cabeçalho do TST começa pela ementa, que cita a lei de
regência (`EMBARGOS REGIDOS PELA LEI Nº 13.015/2014`) e vários precedentes — não há número próprio
nos primeiros 400 caracteres. Em compensação, os três padrões usados identificam explicitamente o
próprio processo (`PROCESSO Nº TST-…`, `estes autos de … TST-…`), então varrer o texto é seguro.
**Correção ao `DESIGN.md`:** o documento previa só o rodapé, que cobre 11 de 198 registros; sem o
padrão "estes autos de", 88 registros ficariam sem número — incluindo o `doc_0729`, cobrado pelo
gabarito.

### Ajustes feitos durante a medição

A primeira versão cobriu 992/1014. Os 22 que faltaram revelaram variações não previstas:

| Causa | Correção |
|---|---|
| STJ com número de 2 dígitos (`Nº 87 - DF`, cautelares) | `_CURTO` passou a aceitar `\d{2,9}` |
| TSE com ano partido por OCR (`1052-77. 201 5.6.26.0000`) | `_CNJ` passou a tolerar espaço entre os dígitos do ano |
| Dispositivo com artigo ordinal (`Artigo 7º`, `Artigo 5º`) | regex passou a aceitar o marcador de ordinal |
| TSE com estrutura CNJ destruída (`487-26.20126.06.0049`, `598- 2012 6 08 0018`) | fallback `_TSE_RUIDOSO`, ancorado no `Nº` |
| TSE com número curto sem parênteses (`AÇÃO CAUTELAR Nº 3.334 - CLASSE`) | `_TSE_CURTO` passou a aceitar `-` como delimitador |

### Resultado medido

**1013 de 1014 registros com número próprio extraído.**

| Fonte | Cobertura |
|---|---|
| STF acórdão | 200/200 |
| STJ acórdão | 199/199 |
| TST acórdão | 198/198 |
| TSE acórdão | 199/199 |
| STM acórdão | 199/200 |
| dispositivo | 13/13 |
| súmula | 5/5 |

O único sem número é o **`doc_0952`**, um extrato de ata do STM cujo cabeçalho é
`J SUPERIOR TRIBUNAL MILITAR. Secretaria Judiciária … EXTRATO DA ATA DA 52a SESSÃO DE JULGAMENTO` —
não traz número de processo. É o caso "legitimamente sem número" que o plano permite listar e
justificar. Não é cobrado pelo gabarito.

### Validação contra o gabarito (prévia do teste final)

Montando um índice provisório `número → ids` e tentando resolver as **82 citações `real` de
jurisprudência** do gabarito só pelos dígitos do trecho:

| Cenário | Resolvidas |
|---|---|
| dígitos crus do trecho | 73/82 |
| + prefixo de súmula (`S`/`SV`) | 78/82 |
| restantes | 4 |

As 4 que sobram são `5úmula 211 do STJ`, `AgInt no RESP 21737l8`, `Recurso Especial Nº 170076O` e
`AgRg no RESP 1.528.4S5/RJ` — todas **ruído de OCR no lado da citação**, que é trabalho da Frente B
(normalização) com a tabela de confusões da Tarefa 4. **Nenhuma falha vem do índice**: os 5 registros
de súmula entraram corretamente como `S83`, `S211`, `S443`, `SV10`, `S331`.

---

## Integração com a Frente B (merge da `main`, 2026-09-18)

A `main` recebeu o commit `b893496` ("extração e normalização") com `texto/`, `extracao/` e
**`tabelas/`**. Isso muda o escopo da Frente A: a Tarefa 4 (tabelas) já estava feita pela frente B,
que deixou o aviso no cabeçalho — *"Tabelas versionadas (provisórias da frente B; a frente A pode
refiná-las)"*. Em vez de duplicar, esta frente passou a **consumir e refinar** essas tabelas.

### Problema de dados encontrado e corrigido

Ao rodar a suíte completa, `tests/test_texto.py` falhava: 4 dos 192 trechos do gabarito não batiam
com `texto[inicio:fim]`. Investigação:

| Verificação | Resultado |
|---|---|
| Arquivo `txt/gen_n1_001.txt` no disco | 3.502 caracteres, 4 trechos deslocados |
| Mesmo arquivo dentro de `desafio-jusbrasil-bracis-2026.zip` | 3.498 caracteres, **0 trechos deslocados** |

O `.txt` no disco tinha sido editado (data de modificação posterior à do zip), inserindo ~4
caracteres e deslocando todos os offsets seguintes. **Não era bug da frente B nem da A.** Os 26
arquivos foram restaurados a partir do zip original; os 192 trechos passaram a bater e a suíte ficou
verde (34 testes).

> **Lição para a equipe:** os `.txt` da amostra são dados de referência com offsets travados pelo
> gabarito. Editá-los quebra silenciosamente qualquer medição de span. Restaurar sempre do zip.

### O que foi reusado da frente B (sem duplicar)

| Função / tabela | Uso na frente A |
|---|---|
| `tabelas.resolver_uf()` | converte `RIO DE JANEIRO` → `RJ` no cabeçalho do STF |
| `tabelas.classes()` | reconhece classes processuais no cabeçalho dos registros |
| `tabelas.resolver_lei()` | converte a descrição da lei do dispositivo → `lei_chave` |
| `tabelas/ocr.json` | tabela compartilhada de confusões de OCR |

### O que foi refinado nas tabelas

**1. `resolver_lei()` não entendia o formato da base.** Os 13 dispositivos escrevem
`Lei nº 4.737, de 15 de julho de 1965`; a função só reconhecia `Lei 13.105/2015`. Resultado: **3 de
13** resolviam.

A função foi estendida com dois padrões (`_LEI_POR_EXTENSO` e `_LEI_COM_BARRA`) e uma tabela de
prefixos (`lei` → `LEI`, `lei complementar` → `LC`, `decreto-lei` → `DL`). A ordem também mudou: o
**número explícito agora tem prioridade sobre o apelido**, porque `Lei nº 13.105, de 2015` é
inequívoca enquanto um apelido pode casar por substring.

Resultado: **13 de 13**, sem regressão nos casos que já funcionavam (`CPC`, `CLT`, `CF/88`,
`Lei 13.105/2015`, `lei nº 9.504/1997` continuam resolvendo).

**2. `classes.json` não tinha 16 classes que aparecem na base.** Faltavam
`EMBARGOS INFRINGENTES E DE NULIDADE` (STM, 15x), `RECURSO EM SENTIDO ESTRITO` (STM, 15x),
`RECURSO ORDINÁRIO` (TSE, 22x), `CAUTELAR INOMINADA CRIMINAL`, `CONFLITO DE JURISDIÇÃO`,
`PETIÇÃO`, `LISTA TRÍPLICE`, `PRESTAÇÃO DE CONTAS`, `AÇÃO PENAL`, entre outras. Foram acrescentadas
à tabela (siglas `EIN`, `RSE`, `RO`/`ROE`, `CautInom`, `CJ`, `CorPar`, `Pet`, `PC`, `LT`, `AP`, `MS`,
`ADI`, `AC`, `AIRR`, `CorPar`).

Efeito na cobertura de `classe_principal`: STM de 166→199, TSE de 170→194, STF de 198→200.

---

## Tarefa 3 — Extrair os demais atributos ✅

**Arquivo criado:** `src/verificador/base/atributos.py`

**O que o plano pedia:** extrair de cada registro `tribunal`, `classe_principal`, `cadeia_recursos`,
`uf`, `ano` e `relator` (normalizado), além do número já feito na Tarefa 2.

**Por que isso existe:** o número sozinho não decide. 69 números próprios da base aparecem em mais de
um registro (recursos internos do mesmo processo). Esses atributos são o que a frente D usa para
desempatar (ADR-007) — sem eles, toda citação com número repetido viraria `incompleta`.

### Decisão de desenho: colunas do banco antes do texto

A exploração da Tarefa 1 mostrou que a base **já traz `tribunal`, `ano` e `relator` como colunas**,
preenchidas em 993 dos 996 acórdãos. A primeira versão do módulo extraía tudo do texto e chegava a
**0/198 relatores no TST** — porque o TST não nomeia o relator no cabeçalho (ele assina no fim).

A versão final usa a coluna como fonte primária e o texto só como fallback. `extrair_relator` passou
a receber `(texto, coluna)`. Relator no TST foi de 0/198 para 196/198.

> Regra geral que ficou: **o que o banco já dá como coluna não se extrai do texto.** Só `uf`,
> `classe_principal` e `cadeia_recursos` precisam mesmo de parsing.

### As funções

| Função | O que resolve |
|---|---|
| `normalizar_relator(nome)` | `MINISTRO JOEL ILAN PACIORNIK` → `joel ilan paciornik` (sem título, sem acento, minúsculo) |
| `extrair_relator(texto, coluna)` | coluna do banco primeiro; cabeçalho como fallback |
| `extrair_uf(tribunal, texto)` | sigla colada ao número (STJ/STM), nome por extenso antes de `RELATOR` (STF), comarca + estado (TSE) |
| `extrair_ano(texto)` | ano do número CNJ → data de julgamento → ano do sequencial do STJ → ano solto |
| `extrair_classes(tribunal, texto)` | `(classe_principal, cadeia_recursos)` |

**Por que `normalizar_relator` existe aqui se a frente B tem uma função de mesmo nome:** a da frente B
limpa o lado da *citação* (`Rel. Min. Dias Toffoli`) e mantém a palavra "ministro"; esta limpa o lado
do *registro*, cujos títulos são outros (`MINISTRA`, `MIN.`, `DR.`, `DES.`). São lados opostos da
mesma comparação e não podem divergir — quando a frente D começar a comparar relatores, vale
unificá-las.

### Bug encontrado e corrigido: a classe principal errada

A regra do `DESIGN.md` é "numa cadeia `AgInt no AgInt no REsp`, a principal é a última". Implementada
sobre a janela de 400 caracteres, ela dava resultados errados:

```
doc_0203  →  principal='EDcl'   cadeia=('EDcl','AgRg','RMS')     ❌
doc_0202  →  principal='REsp'   cadeia=('AgRg','AREsp','AgRg')   ❌
```

Causa: a janela de 400 caracteres alcança o **corpo** do acórdão, e siglas de precedentes citados
entravam na cadeia. A cadeia de recursos vive inteira **antes do número**. Foi adicionado o corte
`_ATE_O_NUMERO`, que limita a leitura ao trecho anterior ao número do processo:

```
doc_0203  →  principal='RMS'    cadeia=('EDcl','AgRg')    ✅
doc_0202  →  principal='AREsp'  cadeia=('AgRg',)          ✅
doc_0205  →  principal='REsp'   cadeia=('AgInt','AgInt')  ✅
doc_0601  →  principal='RR'     cadeia=('EDcl','E','EDcl')✅  (TST, cadeia dentro do número)
doc_0201  →  principal='REsp'   cadeia=()                 ✅
```

É a mesma armadilha do ADR-002 aparecendo em outro campo: **confundir o que o registro é com o que
ele cita**.

**Caso especial do TST:** a cadeia não está em prosa, está dentro do próprio número
(`TST-ED-E-ED-RR-3400-05.2011.5.21.0009`). Tem parser próprio (`_TST_CADEIA` + tabela `_TST_SIGLA`).

### Resultado medido (996 acórdãos)

| Tribunal | total | relator | uf | ano | classe |
|---|---|---|---|---|---|
| STF | 200 | 200 | 200 | 200 | 200 |
| STJ | 199 | 199 | 199 | 199 | 199 |
| STM | 200 | 200 | 135 | 200 | 199 |
| TSE | 199 | 199 | 192 | 199 | 194 |
| TST | 198 | 196 | **22** | 198 | 198 |

**Sobre a UF baixa do TST (22/198):** é esperado e inofensivo. O número CNJ do TST codifica a *região
trabalhista*, não a UF, e o cabeçalho não traz estado. Verificação decisiva: das 10 citações `real`
do gabarito que apontam para acórdãos do TST, **nenhuma traz UF** (`TST-ED-E-ED-RR-3400-05.2011.5.21.0009`,
`ARR-213-85.2010.5.02.0030`, …). Como atributo ausente na citação não elimina candidato (ADR-007), a
UF do TST nunca é consultada no desempate.

**Sobre a UF do STM (135/200):** parte dos registros é extrato de ata sem UF no cabeçalho. Mesmo
raciocínio — ausência não elimina.

---

## Tarefas 5, 6 e 7 — `indexar()`, duplicidade e consultas ✅

**Arquivo criado:** `src/verificador/base/indice.py`
**Arquivo alterado:** `src/verificador/cli.py` (subcomando `indexar`)

As três tarefas são a mesma estrutura — construir o índice, guardar os duplicados, consultar — e
ficaram no mesmo módulo.

### A fronteira pública da frente A

```python
indexar(caminho_db) -> list[RegistroIndice]     # contrato do DESIGN.md
construir_indice(caminho_db) -> Indice          # + estrutura de consulta
Indice.por_numero(digitos) -> list[RegistroIndice]
Indice.por_lei_artigo(lei_chave, artigo) -> list[RegistroIndice]
```

`indexar()` mantém exatamente a assinatura combinada em "Contratos entre módulos", para a frente D
não precisar mudar nada. `construir_indice()` é o atalho que já devolve o objeto consultável.

### Tarefa 6 — duplicidade: as consultas devolvem listas

Decisão explícita: **`por_numero` e `por_lei_artigo` nunca devolvem um registro só, sempre uma
lista.** 81 números da base aparecem em mais de um registro, porque o mesmo processo gera o recurso
original e depois os agravos e embargos sobre ele — todos registros distintos, com ids distintos.

A frente A entrega **todos os candidatos**; quem escolhe é a frente D, com `classe_principal`,
`cadeia_recursos`, `uf` e `tribunal` (ADR-007). Se a frente A escolhesse, estaria decidindo — e
decidir é papel da consulta determinística da etapa [4], não do índice.

### Métodos de diagnóstico

`sem_numero()` e `numeros_repetidos()` existem para o CLI e para os testes: são o instrumento que
detecta parser quebrado sem precisar do gabarito.

### Bug encontrado pela contagem de duplicados

Ao montar o índice pela primeira vez, `numeros_repetidos()` acusou um número em **37 registros**:

```
4796020115040231  →  37 registros, todos do TST
```

Investigação: `479-60.2011.5.04.0231` é a **Arguição de Inconstitucionalidade** que 37 acórdãos do
TST citam na ementa (`TST-ArgInc-479-60.2011.5.04.0231`). Os três padrões do TST casavam com ela em
vez do número próprio — no `id=1974879879`, o próprio processo (`TST-RR-24945-56.2015.5.24.0091`)
está na posição 6.158 e o `ArgInc` na 23.737, mas o padrão do rodapé alcançava primeiro.

**É a armadilha do ADR-002 em ação, dentro do meu próprio código.** Foi adicionada a exclusão
`_NAO_PRECEDENTE` (`ArgInc`, `IncJulg`, `IRR`, `IUJ`) aos três padrões do TST. Resultado: o máximo de
registros por número caiu de **37 para 4** — agora só recursos internos legítimos.

> Sem a contagem de duplicados esse bug passaria despercebido: o número era extraído, o índice
> "funcionava", e 37 registros ficariam resolvíveis por um número que não é deles.

### Segundo bug: `Lei Complementar nº 64/1990`

Ao rodar o teste dos 96 reais, sobrou 1 falha: `art. 1º, I, 'g', da Lei Complementar nº 64/1990` não
resolvia. Causa: meu `_LEI_COM_BARRA` (Tarefa 3) não tolerava o `nº` entre o rótulo e o número —
`lei complementar 64/1990` resolvia, `Lei Complementar nº 64/1990` não. Corrigido.

### Resultado: critério de pronto atingido

```
REAIS RESOLVIDOS: 96/96
```

Rodando o caminho completo (trecho do `.txt` → `ler_campos` da frente B → consulta ao índice), **as
96 citações `real` do gabarito encontram o `id_canonico` certo.**

| Métrica | Valor |
|---|---|
| Registros indexados | 1.014 |
| Sem identificação | 1 (`doc_0952`, extrato de ata sem número) |
| Números em mais de um registro | 81 (máximo: 4) |
| Reais do gabarito resolvidos | **96/96** |
| Inventadas de jurisprudência que acham candidato | **0** |

### CLI

`cmd_indexar` deixou de só contar linhas e passou a construir o índice de verdade, imprimindo o
diagnóstico:

```
desafio1_bracis.db: 1014 registros em `documentos`
  acordao: 996
  dispositivo: 13
  sumula: 5
  sem número próprio: 1 ['2381771667']
  números em mais de um registro: 81
```

---

## Testes ✅

**Arquivo criado:** `tests/test_indice.py` — 15 testes, todos passando (suíte total: **49**).

Nenhum `id_canonico` nem trecho da amostra aparece como literal (R43): tudo é lido do
`goldenset_offsets.csv` e dos `.txt`, pelas fixtures que a frente B já deixou em `conftest.py`.

| Teste | O que prova |
|---|---|
| `test_indice_cobre_a_base_inteira` | 1 registro indexado por linha da base |
| `test_quase_todo_registro_tem_identificacao` | no máximo 1 sem número (o extrato de ata) |
| `test_numero_proprio_nao_vem_de_precedente` | **ADR-002**: nenhum número em mais de 6 registros |
| `test_numero_do_registro_esta_no_cabecalho` | o número escolhido está na abertura do próprio registro |
| `test_todas_as_reais_do_gabarito_resolvem` | **critério de pronto**: 96/96 |
| `test_inventadas_de_jurisprudencia_nao_acham_registro` | **0 inventadas** encontram candidato |
| `test_consultas_devolvem_listas` | contrato das consultas |
| `test_sumulas_entram_com_prefixo` | `S83` / `SV10` não colidem com processos |
| `test_dispositivos_tem_lei_e_artigo` | 13/13 com `lei_chave` e `artigo` |
| `test_cadeia_de_recursos_separa_principal` | o desempate do ADR-007 tem insumo |
| `test_relator_normalizado` | mesma convenção nos dois lados da comparação |
| `test_acordaos_tem_tribunal_e_ano` | atributos básicos completos |
| `test_tabelas_carregam_sem_chave_duplicada` | tabelas íntegras |
| `test_tabelas_resolvem_os_formatos_da_base` | formatos reais da base e da amostra |
| `test_numero_proprio_reduz_a_digitos` | forma canônica de comparação |

O teste `test_numero_proprio_nao_vem_de_precedente` é o mais importante depois do critério de pronto:
foi ele que pegaria o bug do `ArgInc` se alguém reintroduzisse o problema.

---

## Estado final da Frente A

| Tarefa | Estado |
|---|---|
| 1 — Explorar a base | ✅ |
| 2 — Parser de número próprio | ✅ 1013/1014 |
| 3 — Demais atributos | ✅ |
| 4 — Tabelas versionadas | ✅ entregue pela frente B; refinada aqui |
| 5 — `indexar()` | ✅ ligado ao CLI |
| 6 — Duplicidade | ✅ consultas devolvem listas |
| 7 — Funções de consulta | ✅ `por_numero`, `por_lei_artigo` |
| Testes | ✅ 15 novos; suíte com 49 |

**Pronto quando** (critério do plano): *"os 96 `real` resolvem para o `id` certo e nenhum registro
pega número de precedente"* — **atingido**.

### O que fica para a frente D

O índice entrega candidatos; a decisão é dela. Em particular:

- **desempate por atributos** (ADR-007) — o índice fornece `classe_principal`, `cadeia_recursos`,
  `uf`, `tribunal`, `ano` e `relator`; a regra de eliminação é da frente D;
- **UF ausente não elimina candidato** — relevante no TST (22/198 com UF) e no STM (135/200). Já
  verificado que nenhuma citação do TST no gabarito traz UF.

### Débito declarado

- `doc_0952` (extrato de ata do STM) fica sem número próprio; não é cobrado pelo gabarito.
- A exclusão de classes-precedente do TST (`ArgInc`, `IncJulg`, `IRR`, `IUJ`) é uma lista fechada;
  uma classe nova com o mesmo comportamento no conjunto final não seria excluída.
- `normalizar_relator` existe em duas versões (frente A para registros, frente B para citações).
  Quando a frente D comparar relatores, vale unificar — hoje elas não são idênticas.
