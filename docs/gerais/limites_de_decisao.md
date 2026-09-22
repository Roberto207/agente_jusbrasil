# Onde mora o erro que sobrou — decisão, não extração

**Data:** 2026-09-21 · **Base de medida:** commit `835e068` (runs `mrg` / `mrg_sint`)
**Relacionado:** ADR-002 (índice pelo número próprio), ADR-006 (na dúvida, nunca real),
ADR-007 (desempate por classe), ADR-011 (encoder em união), ADR-015 (forma (d) ancorada)

Este documento registra um diagnóstico que **corrige uma explicação anterior errada** e propõe
caminhos para subir o acerto sem depender de encoder. Nada aqui foi implementado — são propostas com
risco e critério de aceite, para a equipe decidir.

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
