# Onde mora o erro que sobrou — decisão, não extração

**Data:** 2026-09-21 · **Base de medida:** commit `835e068` (runs `mrg` / `mrg_sint`)
**Relacionado:** ADR-002 (índice pelo número próprio), ADR-006 (na dúvida, nunca real),
ADR-007 (desempate por classe), ADR-011 (encoder em união), ADR-015 (forma (d) ancorada)

Este documento registra um diagnóstico que **corrige uma explicação anterior errada** e propõe
caminhos para subir o acerto sem depender de encoder.

> **Leia a seção 9 em diante antes de agir.** As seções 1–8 descrevem o estado de 21/09 **antes** da
> correção; a ideia A já foi aplicada (`EDv`), as auditorias A e B já foram rodadas, e os números
> mudaram. O que continua aberto está na seção 11.

---

## 1. O problema, em uma frase

A extração está saturada na amostra oficial: **192/192 de recall e 100% de precisão**. Os 2 erros que
restam (99,0% de acerto) são de **decisão** — qual registro da base vincular —, e nenhum extrator,
regex ou encoder, os alcança.

| Nível | Score | macro-F1 | τ | Recall |
|---|---|---|---|---|
| 1 | 1,10000 (teto) | 1,00000 | 0 | — |
| 2 | 1,07905 | 0,98272 | 0 | — |
| **Final** | **1,08603** | | 0 | **192/192, precisão 1,0** |

Todo o gap de 0,01397 até o teto está no nível 2, e vem de duas citações.

```bash
python -m verificador rodar   --entrada desafio-jusbrasil-bracis-2026/txt --run X --dados desafio-jusbrasil-bracis-2026
python -m verificador avaliar --run X --dados desafio-jusbrasil-bracis-2026
```

---

## 2. Correção de um registro anterior errado

O `resultado_primeira_rodada.md` afirmava que `gen_n2_010` era um empate entre **dois registros
idênticos**, e concluía que não havia como escolher sem chutar. **Isso está errado.** Os dois registros
são processos diferentes:

| id | Cabeçalho na base | Classe verdadeira |
|---|---|---|
| `2684973273` (gabarito) | `AgInt no RECURSO ESPECIAL Nº 1.597.443 - PR` | AgInt no **REsp** |
| `2679428592` | `AgInt nos EMBARGOS DE DIVERGÊNCIA EM RESP Nº 1597443 - PR` | AgInt nos **EREsp** |

A citação do parecer diz `AgInt no Recurso Especial nº 1.597.443 - PR`, que casa **só com o primeiro**.

A causa raiz é que `src/verificador/tabelas/classes.json` **não conhece "Embargos de Divergência"** —
nem `EREsp`, nem `EDv`. Sem essa classe, o índice lê os dois registros como `classe_principal='REsp'`,
`cadeia=('AgInt',)`, e o desempate do ADR-007 não tem por onde separar. A ambiguidade é **fabricada por
uma lacuna nossa**, não pela base.

E é sistemático: **11 registros** da base têm "EMBARGOS DE DIVERGÊNCIA" no cabeçalho.

```bash
python - <<'E'
import sqlite3, re
con = sqlite3.connect('desafio-jusbrasil-bracis-2026/desafio1_bracis.db')
n = sum(1 for _, t in con.execute("select id,texto from documentos")
        if re.search(r"EMBARGOS\s+DE\s+DIVERG[EÊ]NCIA", " ".join((t or "")[:260].split()), re.I))
print(n)
E
```

---

## 3. A escala real do problema

Números compartilhados entre registros são comuns na base:

| Situação | Grupos |
|---|---|
| Números presentes em mais de um registro | **81** (171 registros, ~17% da base) |
| ↳ separáveis hoje por classe + cadeia | 4 |
| ↳ parcialmente separáveis | 2 |
| ↳ **classe + cadeia idênticas** | **75** |

Nos 75, os registros só diferem em `ano` e `relator` — atributos que a citação da forma (a) raramente
carrega. Corrigir `EREsp`/`EDv` move alguns para "separável"; a maioria continua indistinguível com o
que extraímos hoje.

**Mas a frequência real é baixa:** o caminho `numero_ambiguo` dispara **1 vez em 192** na amostra
(0,5%). No sintético dispara 92 vezes, o que é artefato do gerador — ele fabrica ambiguidade de
propósito —, não reflexo do mundo. Isso deve pesar na priorização.

---

## 4. O segundo erro (`gen_n2_005`) é de outra natureza

Três registros TST dividem o CNJ `25823-78.2015.5.24.0091` — estágios diferentes do mesmo caso:

| id | Classe indexada | Ano |
|---|---|---|
| `1974934139` (gabarito) | `AIRR` | 2017 |
| `2813052232` (nosso) | `ARR`, cadeia `AgRg` | 2024 |
| `2482651776` | (outro número próprio) | 2024 |

A citação diz `AgARR`, que não é exatamente nenhum dos dois. O registro anterior concluía que "o
gabarito parece ter um erro". **Hipótese alternativa, mais provável:** a organização vincula ao **caso**
(pelo número CNJ), não ao estágio recursal — o que explicaria apontar o registro mais antigo. Se for
isso, existe critério de desempate e ele é "o mais antigo" ou "aquele cujo próprio cabeçalho traz o
número". Não está documentado em lugar nenhum do desafio.

Reforça a hipótese: `kaggle_metric.py` aceita **conjunto** de ids no gabarito
(`doc_ids: conjunto aceito, separado por ":"`), mas **nenhuma linha** do `goldenset_offsets.csv` usa
`:`. Ou seja, a organização sempre tem uma resposta única em mente — não trata esses casos como empate.

---

## 5. Por que encoder não resolve a decisão

Encoders **são** classificadores, em dois modos: classificação de token (NER, acha o span) e de
sequência (rotula um span). O que não encaixa é o **formato** deste problema:

- A classe `real` exige emitir o **`id_canonico` certo entre 1014 registros**. Isso é *entity linking*,
  não classificação em 3 rótulos. Um classificador de 1014 saídas treinado em 192 exemplos não se sustenta.
- Se a citação é `real` ou `inventada` depende de **o número existir na base** — uma consulta, não um
  juízo de linguagem. Nenhuma compreensão de texto informa se `1.597.443` está lá.
- Em `gen_n2_010`, a resposta certa vem de um atributo **estrutural** (EREsp ≠ REsp). Uma regra acerta
  isso por construção; um modelo apenas aproximaria.

**Onde um encoder caberia de verdade na decisão:** re-ranquear candidatos com um *cross-encoder* que
pontua a similaridade entre o texto da citação e o cabeçalho de cada registro, quando vários casam.
É técnica real, mas ataca os 75 grupos indistinguíveis — onde nem o texto da citação tem sinal, porque
ela não traz ano nem relator. Baixo retorno esperado.

Isso não contradiz o ADR-011: lá o encoder serve à **extração** (achar spans de frases não vistas),
que é outro problema e onde ele continua fazendo sentido.

**A alternativa ao encoder para a decisão é atributo melhor e recuperação melhor** — ideia A abaixo.

---

## 6. Ideias de solução

Ordenadas por valor generalizável dividido por custo, com o risco explícito. **Nenhuma implementada.**

### A. Auditar a tabela de classes contra a base, não contra a amostra — *recomendada*
Extrair a expressão de classe do cabeçalho dos 1014 registros e listar as que não mapeiam para nenhuma
sigla conhecida. `EREsp` e `EDv` apareceram por acaso ao investigar um erro; a auditoria acharia o resto
de uma vez. Ataca a ambiguidade na origem, e vale para o conjunto cego tanto quanto para a amostra.

- **Arquivos:** `src/verificador/tabelas/classes.json`, `src/verificador/base/atributos.py`
- **Risco:** baixo — mesmo perfil das causas 2 e 3, já feitas e medidas
- **Aceite:** lista de classes desconhecidas vazia; contagem de grupos "classe+cadeia idênticas" cai de 75

### B. Auditar o índice contra o ADR-002 — *recomendada*
Conferir sistematicamente que o número de cada registro vem do **próprio cabeçalho**, não de um
precedente citado no corpo. O caso `2679428592` passou, mas 17% da base compartilha número e essa
propriedade nunca foi medida em escala.

- **Arquivo:** `src/verificador/base/indice.py`
- **Risco:** baixo — é só medição
- **Aceite:** relatório de quantos registros têm o número fora do cabeçalho; idealmente zero

### C. Desempate por atributo que a citação carrega — *condicional*
Quando a citação traz `ano` ou `relator` (algumas formas (a) trazem: `Rcl 123/SP, Rel. Min. X, 2020`),
usá-los para separar registros que dividem número. Hoje `decidir` só filtra por tribunal, UF, classe e
cadeia.

- **Arquivo:** `src/verificador/decisao/`
- **Risco: médio — mexe em τ.** Todo desempate que converte `incompleta` em `real` pode transformar uma
  `inventada` em `real`, que é o erro grave (corta a nota pela metade do τ). Hoje τ = 0 em todos os
  conjuntos, e isso é patrimônio a proteger.
- **Aceite:** τ **permanece 0** em todos os conjuntos; reversão imediata se sair

### D. Perguntar à organização o critério de desempate — *humano, sem custo técnico*
Levar junto com as duas pendências já abertas no `scope.md` (data do conjunto cego, teto diário de
submissões). Perguntas concretas:

1. Quando vários registros da base compartilham o número do processo, qual deles o gabarito espera?
2. O vínculo é ao **caso** (número CNJ) ou ao **estágio recursal** específico?
3. O campo `doc_ids` do gabarito aceita conjunto — isso é usado no conjunto final?

### Fora de escopo
Reescrever as formas (a)/(b)/(c) no estilo ancorado da forma (d): elas dependem de número, que é âncora
forte por natureza, e a precisão está em 1,0. Não há sinal de problema.

---

## 7. Protocolo, para quem for implementar

Linha de base: runs `mrg` / `mrg_sint` — amostra 1,08603 (192/192); sintético 1,09571 (988/994);
sintético-controle 1,08530 (206/210).

Uma mudança por vez, revertendo a que falhar (ADR-009):

- amostra **não regride** de 192/192 nem de 1,08603;
- **precisão de spans 1,0** e **zero espúrios** em todos os conjuntos;
- **τ = 0** — o critério mais importante aqui, porque C mexe justamente nisso;
- melhora **também** no controle e no sintético-controle;
- `pytest` verde (145 hoje) e R49 determinístico.

```bash
pytest
bash scratchpad/medir.sh <run>
python -m verificador comparar --run mrg --run <run>
```

---

## 8. O que continua em aberto

- O critério de desempate da organização (ideia D) — bloqueia decidir C com fundamento.
- Se o conjunto cego usa a mesma base canônica (`scope.md`, "Ainda em aberto").
- Quanto dos 75 grupos indistinguíveis sobra depois da auditoria A — só medindo.

---

# Atualização — 2026-09-21 (depois do `EDv`)

**Base de medida:** commit do fix do padrão solto (runs `fix` / `fix_sint`)

## 9. O que mudou

A ideia A deste documento foi aplicada: `EDv` entrou em `classes.json` (commit `7b3ea35`) e o
`gen_n2_010` está resolvido.

| Conjunto | Antes | Depois |
|---|---|---|
| Amostra oficial | 1,08603 | **1,09648** |
| **Controle** | 1,07923 | **1,10000** ← teto teórico exato |
| Sintético | 1,09571 | 1,09571 |
| Sintético-controle | 1,08530 | 1,08530 |

O controle atingir 1,10000 é o dado mais informativo aqui: **o sistema chega ao teto quando o dado
permite**. O que sobra na amostra não é limitação do pipeline.

Detalhe do ajuste posterior no alias em `specs/edv_padrao_solto.md`.

## 10. Auditorias A e B: ambas rodadas, ambas limpas

Este documento propunha as duas. Foram executadas, e o resultado é **evidência negativa** — vale
registrar para ninguém refazer:

| Auditoria | Método | Resultado |
|---|---|---|
| **A** — tabela de classes × base | `classe_principal` de todos os 1014 registros | **1008/1014 (99,4%)** já mapeados. Os 6 restantes são cabeçalhos com OCR corrompido (`AGRAVO REGIMÈNTAL`, `EMBARGOS DE DECLARAcA0`) ou formato atípico do TSE (`ACÓRDÃO - CLASSE 32 ELEITORAL`) — não classes ausentes |
| **B** — índice × ADR-002 | posição da 1ª ocorrência do número no texto | 802 registros têm o número nos primeiros 400 caracteres. Os 193 "tardios" são **todos TST**, onde o número vem do rodapé `PROCESSO Nº TST-…` **por especificação**. **Zero violações** |

**Conclusão: o `EDv` era a lacuna real, e não há mais ganho a colher nessas duas frentes.**

## 11. O que falta para 1,100 — e por que não vamos atrás

Faltam **0,00352** na amostra, e é **uma causa só**, não duas:

| Cenário | Score | Ganho |
|---|---|---|
| Hoje | 1,09648 | — |
| Só corrigir o link do `gen_n2_005` | 1,09928 | +0,00281 |
| Só zerar o Brier | 1,09719 | +0,00071 |
| Os dois | **1,10000** | +0,00352 |

O nível 1 já tem **Brier exatamente zero**. No nível 2 o Brier é 0,010753, e há 93 citações:
`1/93 = 0,010753`, bate na sexta casa. Ou seja, o Brier não-zero **é** a única predição errada,
enviada com confiança ≈1,0. Corrigir o link levaria macro-F1 a 1,0 e Brier a 0 simultaneamente.

**Não vamos implementar**, e o motivo é a base empírica:

- só **2** citações `real` da amostra têm número com mais de um registro na base;
- uma (`gen_n2_010`) já foi resolvida pela classe `EDv`;
- sobra **n=1**.

A regra "escolher o mais antigo" acerta 2/2 — assim como "classe mais próxima", "menor id" e outras.
Com um exemplo efetivo, a regra é infalsificável, e escrevê-la é o que o **ADR-009** proíbe.

Isso permanece como a **ideia D**: perguntar à organização se o vínculo é ao caso (número CNJ) ou ao
estágio recursal.

## 12. Procedimento novo: regenerar o sintético depois de mexer no índice

Descoberto nesta rodada, e quase virou falso alarme de regressão.

O gerador sintético deriva a verdade do índice (`sintetico/citacoes.py:66` usa `classe_principal`).
Quando o `EDv` entrou, o sintético em disco ficou **velho**: o gabarito ainda dizia que
`Agravo Interno no Recurso Especial 1.726.922` era `real`, porque na geração aquele registro era lido
como `REsp`. Com o índice corrigido, o pipeline passou a dizer `inventada` — e o placar caiu de
1,09571 para 1,09350, com duas citações `real|inventada`.

Não era regressão. Depois de `gerar-sintetico`, voltou a 1,09571 exato.

> **Regra:** toda mudança em `classes.json`, em `base/` ou em qualquer coisa que altere o índice exige
> `python -m verificador gerar-sintetico … --semente 0` **antes** de medir. Sem isso o gabarito
> sintético contradiz o código e a medição mente nas duas direções.

---

# Atualização — 2026-09-21 (as regras do desafio)

A página **Data** da competição responde perguntas que este documento deixava abertas. Ela foi lida
na íntegra; a competição é privada, então não há como buscá-la por URL sem login.

## 13. Não existe critério de desempate — e isso inverte o problema

> | Candidatos encontrados | Classe | Saída |
> | exatamente 1 | **real** | `id_canonico` |
> | 0 | **inventada** | null |
> | 2 ou mais candidatos distintos, **sem critério de desempate** | **incompleta** | null |
>
> **Cada citação real do desafio resolve para exatamente um registro da base — as duplicatas
> remanescentes do acervo não têm nenhuma citação apontando para elas.**

A seção 11 deste documento perguntava qual registro escolher quando vários compartilham o número.
A resposta é que **isso não deveria acontecer**: se o gabarito diz `real` e nós achamos 2 candidatos,
o candidato a mais é erro nosso. Não é desempate melhor — é candidato indevido.

## 14. O candidato indevido, encontrado

A página nomeia a causa: *"Separar o registro de quem apenas o cita — esta é a armadilha que mais
custa precisão."* Era exatamente isso.

| Registro | Posição do número | Contexto |
|---|---|---|
| `1974934139` (gabarito) | 4.309 | *"**Vistos, relatados e discutidos estes autos de** … nº TST-AIRR-25823-78…"* → é o processo |
| `2813052232` (nosso) | 32.487 | *"…não provido". (PROCESSO Nº TST-AIRR-25823-78… )* → decisão **transcrita** |

`numero_proprio.py` tentava o rodapé `PROCESSO Nº TST-…` **antes** da fórmula `estes autos de …`, e o
rodapé pode aparecer dentro de uma transcrição. Invertida a ordem, **20 dos 199 registros do TST
(10%) passaram a ter o número certo** — o `2813052232` é na verdade
`TST-Ag-ARR-10132-34.2015.5.03.0018`. Grupos de número compartilhado caíram de 81 para 77.

Antes do fix, cada um desses 20 custava nos dois sentidos: citação ao número verdadeiro deles dava
`inventada` por engano, e citação ao número roubado dava ambiguidade falsa.

## 15. O que o fix revelou sobre o `gen_n2_005`

Com um único candidato pelo número, o **R40** passou a vetá-lo: a citação diz `AgARR` e o registro é
`AIRR` — mesmo caso (mesmo CNJ), estágio recursal diferente. Resultado `inventada`, pior que o link
errado de antes.

O `gen_n2_005` estava **certo pelo motivo errado**: acertava a classe porque existia um candidato
espúrio cuja classe casava por acaso.

Custo na amostra: 1,09648 → **1,09272**. Controle segue em **1,10000**, sintético em 1,09574.
**Decisão: manter o fix.** O que conta é o conjunto cego, e lá 20 registros mal numerados custam mais
que 0,0038 na amostra. A queda vem do R40, não do fix.

A tabela da página sugeriria não vetar candidato único por classe. Mas o R40 existe para o "número
emprestado" (`inventada` com número real e classe trocada), que o sintético exercita — mexer nele com
base neste único caso cairia no ADR-009. Fica como pergunta à organização.

## 16. O gabarito distribuído não bate com a página

| | Distribuído | Página Data |
|---|---|---|
| Gabarito | `goldenset_offsets.csv`, **192** citações | `goldenset.csv`, **225** |
| `incompleta` | **32** | **65** |
| `real` / `inventada` | 96 / 64 | 96 / 64 |
| Base | **1.014** | **1.016** |

`real` e `inventada` batem exatamente — **os 33 de diferença são todos `incompleta`**.

**Correção de 21/09 (noite):** eu havia atribuído os 33 às referências vagas. Fui contar: os 26
documentos têm **11** dessas frases (`a jurisprudência pacífica desta Corte`, `o entendimento
sumulado sobre a matéria`, `o artigo correspondente do CPC`, `a orientação jurisprudencial da Corte
Superior`, `o dispositivo legal de regência`), e nenhuma está no gabarito de 192. **11 não fecham
33** — a origem da diferença segue **sem explicação**. A aritmética das classes é sólida; a
atribuição às referências vagas era inferência minha e só se sustenta em parte.

Novo download em 21/09 veio **byte a byte idêntico** ao de 15/09 — o dataset não mudou. E a submissão
marcou 1,08604, igual ao cálculo local sobre 192, então o leaderboard usa o arquivo distribuído.

**Risco, com o número corrigido:** se o conjunto final anotar as referências vagas e nós não as
extrairmos, perderíamos 11 de 43 `incompleta` — F1 da classe ~0,85, score ~1,046, perda de ~0,046.
Menos que os 0,118 que projetei antes, mas ainda três vezes o gap que separa o 20º lugar do topo.
Nenhum teste local resolve; ver ADR-005.
