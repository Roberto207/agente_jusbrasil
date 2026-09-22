# feat: correção de OCR dentro de palavras (`m↔rn`)

**Autor:** Caio · **Data:** 2026-09-22 · **Item:** `tarefas_equipe.md`, seção 3.2, **Tier 1**
**Princípio herdado:** ADR-015 (âncora, não vocabulário solto) · **Contrato:** ADR-003 (mapa de offsets)

> Nome do arquivo: o pedido era `feat: verificar ocr caio`. `:` é caractere inválido em nome de
> arquivo no Windows, então ficou `feat-verificar-ocr-caio.md`.

---

## 1. O problema

A página Data do desafio lista o ruído do nível 2 como `0↔O`, `1↔l`, `5↔S` e **`m↔rn`**.

Nossa tabela de OCR (`tabelas/ocr.json`) cobria **só letra→dígito dentro de número**. Corrupção de
palavra tinha **um único caso tratado, hardcoded**: `5úmula → Súmula`.

Consequência: se o conjunto cego trouxer `Reclarnação`, `Súrnula` ou `rninistro`, a citação **não é
uma classe errada — ela desaparece**. O padrão não casa, o span não existe, e a citação vira falso
negativo da sua classe. E o nível 2 pesa **2×** na nota final.

O agravante: **zero ocorrências na amostra**. Nunca tínhamos sido testados nisso.

## 2. Por que a solução óbvia está errada

Trocar `rn→m` às cegas destrói texto correto:

| Texto legítimo | Troca cega produz | Estrago |
|---|---|---|
| `Agravo Interno` | `Agravo Intemo` | `AgInt` é *Agravo **Interno*** — a classe se perde |
| `Og Fernandes` | `Og Femandes` | relator do STJ; quebra a leitura da forma (d) |
| `governo`, `externo`, `moderno` | `govemo`, `extemo`, `modemo` | ruído puro |

Por isso a especificação exige **correção contra vocabulário fechado**: só se troca quando o
resultado é um termo que sabemos existir. É o mesmo raciocínio do ADR-015 — ancorar no que é
invariante, nunca enumerar solto.

## 3. O que foi feito

### 3.1 Vocabulário fechado

Arquivo novo: **`src/verificador/tabelas/vocabulario_ocr.json`** — 31 termos, e só entra palavra que
satisfaz as duas condições:

1. é **âncora de extração** (se ela se perder, a citação se perde);
2. **contém `m` ou `rn`** (qualquer outra é peso morto — a correção nunca a produziria).

As âncoras saíram do código, não de intuição:

| Origem | Termos |
|---|---|
| `padroes.py::MARCADOR_RELATOR` | ministro, ministra, ministros, ministras, min |
| `padroes.py::_TRIBUNAL` | stm |
| `padroes.py::_compilar_sumula` | súmula, súmulas, súm |
| `padroes.py` (repercussão geral) | tema, temas |
| `tabelas/classes.json` | em, embargos, mandado, instrumento, interno, interna, regimental, reclamação, reclamações, competência, inominada, criminal, liminar, militar, cautinom, ms, rms |
| `tabelas/leis.json` | complementar, cpm, consumidor |

Por ser uma tabela em `tabelas/`, ela entra automaticamente no `hash_tabelas()` e, portanto, no
manifesto de cada execução: mudar o vocabulário muda o hash da run.

### 3.2 A correção

Em **`src/verificador/texto/normalizacao.py`**, `_corrigir_palavra()` com três guardas, nesta ordem:

```
1. palavra já no vocabulário         → não toca      (protege `interno`)
2. nenhuma variante no vocabulário   → não toca      (protege `Fernandes`, `Moraes`)
3. duas variantes no vocabulário     → não toca      (ambiguidade)
   exatamente uma variante conhecida → corrige
```

As variantes são geradas nos **dois sentidos** (`rn→m` e `m→rn`), cada ocorrência isolada e todas
juntas — `complementar` tem dois `m`. Enumerar todas as combinações seria exponencial sem ganho.

A caixa é fechada por construção: **o resultado de uma correção é sempre um termo da lista**. Nada
sai dela.

### 3.3 Tornar o item mensurável

Aqui está o ponto que quase passou despercebido. Com a correção pronta, medi nos três conjuntos:

| Conjunto | Antes | Depois |
|---|---|---|
| Amostra | 1,092719 | 1,092719 |
| Controle | 1,100000 | 1,100000 |
| Sintético | 1,095745 | 1,095745 |

**Nada se moveu** — porque **nenhum conjunto nosso contém `m↔rn`**. Nem a amostra, nem o gerador.
A correção era, literalmente, inverificável: não havia como saber se funcionava, nem se uma
regressão futura a quebraria.

Então o gerador ganhou o ruído: **`src/verificador/sintetico/ruido.py`**, funções `m_vira_rn` e
`rn_vira_m`, acrescentadas a `TRANSFORMACOES`. É a mesma lógica do Tier 2 da seção 3.2 — parte do
trabalho é construir o instrumento, não só melhorar o número.

## 4. Resultado medido

Experimento A/B no corpus de estresse (200 documentos, 994 citações, semente 0, **com** ruído
`m↔rn`), correção ligada × desligada:

| Métrica | Sem a correção | Com a correção | Δ |
|---|---|---|---|
| Score — sintético | 1,046158 | **1,095741** | **+0,0496** |
| Score — sintético-treino | 1,049061 | **1,098215** | +0,0492 |
| Score — **sintético-controle** | 1,031971 | **1,085300** | **+0,0533** |
| Recall de spans | 0,9406 (59 perdidos) | **0,9940** (6 perdidos) | **+5,3 pts** |
| Precisão de spans | 0,9936 (6 espúrios) | **1,0000** (0 espúrios) | +0,0064 |
| Citações emitidas | 941 | **988** | +47 |
| τ | 0 | 0 | — |

Dois pontos que valem destaque:

**A correção também recupera precisão.** Sem ela, 6 spans espúrios apareciam: palavra corrompida
faz o regex casar em fronteira errada. Com ela, precisão volta a 1,0 — o critério de aceite que a
equipe usou em todas as correções anteriores.

**O ruído passou a custar quase nada.** O corpus *com* `m↔rn` e correção ligada (1,095741) empata
com o corpus *sem* esse ruído (1,095745). Diferença de 4 na sexta casa.

### Não regrediu nada

| Verificação | Resultado |
|---|---|
| Amostra oficial | **1,092719** (idêntico), 192/192 spans |
| Controle da amostra | **1,100000** (teto), 91/91 |
| Precisão de spans | 1,0000 em todos os conjuntos |
| τ | 0 em todos os conjuntos |
| `pytest` | **181 verdes** (eram 150) |
| Determinismo (R49) | duas execuções, CSV idêntico byte a byte |

## 5. Dois defeitos encontrados no caminho

### 5.1 O mapa de offsets truncava a cauda da palavra

`RN` → `M` encurta o texto em um caractere. O `_aplicar` mapeava os caracteres novos para os
**primeiros** originais, então o último caractere da palavra ficava fora do span:

```
original:    artigo 29O, I do Código Penal RNilitar
span saía:   artigo 29O, I do Código Penal RNilita      ← falta o `r`
```

O span ainda casava por IoU (0,97), mas `ler_campos` normaliza o trecho **de novo** — e `RNilita`
não é termo conhecido, então a lei não resolvia. A citação ia de `real` para **`inventada`**.

Foi o teste **R35** (par limpo × ruidoso tem de concordar) que pegou isso. Correção: quando o
resultado encurta e tem 2+ caracteres, o último passa a apontar para o último original. A mudança
não toca as regras existentes — `- ` → `-`, `--` → `-` e `n°` → `nº` caem nos outros ramos.

### 5.2 O vocabulário nasceu com lacunas

A primeira versão esqueceu **`MS`**, **`RMS`**, **`CPM`** e **`consumidor`**. Sintoma: `artigo 290
do Código Penal RNilitar` continuava inventada, porque `CPM` não estava listado.

O remédio não foi só acrescentar as quatro. Foi o teste
`test_vocabulario_acompanha_as_tabelas_de_extracao`, que varre `classes.json` e `leis.json`, filtra
o que tem `m`/`rn` e **falha se algo estiver fora do vocabulário**. Quem acrescentar uma classe nova
amanhã é avisado na hora, em vez de perder citações em silêncio no conjunto cego.

## 6. Pastas e arquivos alterados

```
src/verificador/tabelas/
├── vocabulario_ocr.json      NOVO   31 âncoras, com nota de manutenção
└── __init__.py               EDIT   + vocabulario_ocr(), + chave_ocr()

src/verificador/texto/
└── normalizacao.py           EDIT   + _corrigir_palavra e auxiliares
                                     + _PALAVRA_OCR ligado em normalizar()
                                     ~ _CINCO_UMULA tolera `5úrnula`
                                     ~ _aplicar: mapa preserva a cauda ao encurtar
                                     ~ _substituir: pula substituição que não muda nada

src/verificador/sintetico/
└── ruido.py                  EDIT   + m_vira_rn, + rn_vira_m em TRANSFORMACOES

tests/
├── test_ocr_palavras.py      NOVO   31 testes (reparo, proteção, mapa, sincronia)
└── test_sintetico.py         EDIT   expectativa do ruído (agora age sem número)

docs/gerais/
└── feat-verificar-ocr-caio.md NOVO  este arquivo

tarefas_equipe.md             EDIT   caixinha do Tier 1 marcada, com os números
```

**Nada foi tocado em** `base/`, `extracao/`, `decisao/`, `saida/`, `avaliacao/` ou `cli.py`. A
correção vive inteira na normalização; as outras frentes não sabem que ela existe.

## 7. Limites declarados

- **O vocabulário protege âncora, não texto em volta.** Se o OCR corromper o sobrenome do relator
  (`Moraes` → `Rnoraes`), nada é reparado. A forma (d) sobrevive porque o padrão de nome só exige
  inicial maiúscula, mas a comparação de relator com o índice falharia. Não há caso medido.
- **`terna` → `tema` é possível.** `terna` é palavra portuguesa e vira `tema` pela regra. Só criaria
  citação dentro de `tema <número> da repercussão geral`, o que é implausível. Fica registrado.
- **Com um caractere só não dá para cobrir as duas pontas do span.** `- ` → `-` mantém o
  comportamento antigo (aponta para o início). Nenhuma regra atual depende da cauda nesse caso.
- **O ruído do gerador foi escrito por quem escreveu a correção** — a ressalva do ADR-012 continua
  valendo. Os ganhos acima são estimativa, não previsão. A frequência real de `m↔rn` no conjunto
  cego é desconhecida; o que sabemos é que a organização o documentou e que antes disso estávamos
  com 0% de cobertura.
- **O corpus de estresse não entra em submissão.** É instrumento de medida; a submissão continua
  saindo do texto oficial (`resultado_submissoes.md`, seção 2).

## 8. Próximos passos

**Imediato (antes de qualquer submissão)**

1. **Commit e PR** — o trabalho está na árvore, sem commit. Branch sugerido: `frente-b-ocr-palavras`.
2. **`verificador comparar`** entre a linha de base e esta versão na amostra, para o registro formal
   de que nada mudou nos dados oficiais (aqui foi conferido por score e recall, não pelo comparador).
3. **Recalibrar a confiança** (`verificador calibrar`): a tabela `taxa_acerto.json` foi medida antes
   do ruído `m↔rn` existir no sintético. O caminho `lei_apelido_desconhecido` mudou de frequência.

**Tier 1, item que continua aberto**

4. **Invariante da garantia do organizador** — *"todo ruído aplicado a uma citação real é recuperável
   por normalização; um dígito nunca é trocado por outro dígito"*. Logo, **toda citação `real` do
   gabarito que caia em `numero_ausente` é bug nosso**. Vira teste. É o outro item do Tier 1 e ainda
   não foi feito.

**Tier 2 — o que este trabalho mostrou ser necessário**

5. **LeNER-Br como sonda externa.** Este item deixou de ser opcional na minha leitura: a correção só
   pôde ser medida porque **nós mesmos** fabricamos o ruído. Texto jurídico real, escrito por gente
   de fora, é a única forma de saber se o vocabulário de 31 termos cobre o que aparece na prática.
6. **LLM diversificando o sintético** — mesma razão, agora com um exemplo concreto do problema.

**Manutenção**

7. Quem acrescentar classe em `classes.json` ou lei em `leis.json` será avisado pelo teste de
   sincronia se o termo tiver `m`/`rn`. **Não silencie esse teste** — acrescente o termo ou
   justifique no PR por que ele não é âncora.
