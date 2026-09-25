# Resultado das submissões — notas, conjuntos de dados e como lê-los

**Atualizado em:** 2026-09-25 · **Prazo final:** 30/09/2026, 23h59 (BRT)
Complementa `resultado_primeira_rodada.md` (explica a métrica e a generalização) e `tarefas_equipe.md` (plano de trabalho).

---

## 1. Nota do leaderboard do Kaggle

Equipe: **Guerreiros da T7**.

| Submissão | Tag / commit | Enviada? | Nota local (prevista) | **Leaderboard** | Posição |
|---|---|---|---|---|---|
| `sub-001` | `f04ee55` (só-regras, sem confiança) | não | 0,98850 | — | — |
| `sub-002` | `93d5b38` (recall causas 2/3 + confiança) | **21/09/2026** | 1,0860444451608189 | **1,08604** | **20º** |
| `sub-003` | `ceed22f` (merge do PR #4, execução `auditoria_head`) | não registrado | 1,09272 | — | — |
| `sub-004` | `e679784` (famílias de classe: outro estágio do mesmo caso deixa de ser número emprestado) | não registrado | 1,10000 | — | — |
| `sub-005` | `70ff324` (confiança suavizada, `ALFA = 7`) | **sim** (data a confirmar) | 1,099999951 | **1,100** | **13º** |
| `sub-006` | `015b523` (reforço do regex + encoder ligado) | não (conferida no Kaggle em 25/09) | 1,099999951 | — | — |

### `sub-005` — a última enviada

- **O que mudou em relação à `sub-004`:** só a confiança, de 1,0000 para 0,9993 (suavização da
  calibração: `ALFA = 7`, `PRIOR = 0,97`). Spans, classes e ids são idênticos na amostra.
- **Nota local:** 1,099999951 nos dois níveis. É o teto (1,1) menos o custo mínimo da confiança não
  ser 1,0 no bônus de calibração: macro-F1 1,0, τ = 0.
- **`submission.csv`:** sha256 `4c6e3538b46fc0be…`. A versão atual do projeto (`main`, 25/09, com o
  reforço do regex) gera **o mesmo arquivo** na amostra: as mudanças de depois cobrem formatos que a
  amostra não tem.
- **Tag:** `sub-005` enviada ao GitHub em 25/09 (o commit `70ff324` já estava em `origin/main`). A
  organização coleta "o repositório e o commit que produziram as saídas".
- **Leaderboard: 1,100, 13º lugar.** A nota local prevista (1,099999951) arredonda para o mesmo
  1,100: a simulação local continua exata. Todos os 12 acima também têm 1,100; o desempate é pela
  ordem de envio, e eles chegaram antes. **Na fase de treino não há mais o que ganhar:** estamos no
  teto da amostra. A disputa real é o conjunto final (cego), e é para ele que servem o reforço do
  regex e a decisão do encoder.

### `sub-006` — regex reforçado + encoder, conferida no Kaggle (25/09)

- **Não enviada:** na amostra, o `submission.csv` é o mesmo da `sub-005` (sha256 `4c6e3538…`) e daria
  1,100 de novo. O ganho dela (reforço do regex, encoder) é para o conjunto final.
- **Determinismo entre máquinas:** o notebook `08_sub-006` no Kaggle gerou `submission.csv`, JSONs e
  rastro **idênticos byte a byte** aos da execução local, e duas execuções no Kaggle deram o mesmo
  arquivo. Era a condição da equipe para o encoder entrar.

### A simulação local é exata

```
local       : 1.0860444451608189  →  1,08604
leaderboard : 1,08604
diferença   : 0,0000000000
```

Além disso, o `submission.csv` gerado no Kaggle é **byte a byte idêntico** ao local
(`sha256 e771973529eedc64…`, o mesmo hash do teste de determinismo R49). Isso valida, de uma vez:

- o clone na tag correta e a instalação no ambiente do Kaggle;
- a descoberta dos dados em `/kaggle/input`;
- o determinismo **entre máquinas diferentes**, não só entre duas execuções locais;
- que **podemos medir qualquer mudança localmente sem gastar submissão**, na fase 1.

### Decomposição da nota

| Nível | Score | macro-F1 | τ | b |
|---|---|---|---|---|
| 1 | **1,10000** (teto teórico) | 1,00000 | 0 | 0,10000 |
| 2 | 1,07907 | 0,98272 | 0 | 0,09804 |

O nível 1 está no máximo possível. **Todo** o gap até o teto de 1,1 vem do nível 2 (peso 2/3): 0,01396.
Ele se resume às 2 citações já documentadas em `resultado_primeira_rodada.md` §3 — `gen_n2_010` (dois registros
idênticos na base; ADR-006 manda `incompleta`) e `gen_n2_005` (citação diz `AgARR`, gabarito aponta `AIRR`).

### Contexto competitivo (21/09/2026)

| Posição | Equipe | Score |
|---|---|---|
| 11 | Leonardo Garcia10 | 1,09999 |
| 12 | Time 67 | 1,09998 |
| 13 | Thalles.Mota | 1,09997 |
| 19 | RafaelOleques | 1,08736 |
| **20** | **Guerreiros da T7** | **1,08604** |
| 21 | ArnoldMoya | 1,08001 |

O topo está em ~1,09999, praticamente o teto de 1,1 — ou seja, macro-F1 1,0 nos dois níveis, acertando as 2 citações
que deixamos de propósito. Duas leituras possíveis:

1. **Decoraram a amostra.** É viável: o leaderboard da fase 1 usa a amostra de gabarito aberto. Nesse caso a nota
   desaba no conjunto cego.
2. **Existe uma regra legítima que não vimos** (ex.: critério de desempate para registros duplicados que coincide com
   o modo como o gabarito foi montado). Se for isso, generalizaria e vale descobrir.

**Importante:** as submissões da fase de treino **não contam para o ranking final** (`scope.md`). A posição de hoje não
vale para o prêmio, e o gap de 0,014 na amostra é pequeno perto do risco real: **10,2% das citações não são encontradas**
no sintético. Perseguir 2 citações específicas da amostra é o que o ADR-009 proíbe.

---

## 2. O que é submetido

O `submission.csv` é gerado **só a partir dos `.txt` oficiais** do desafio (`rodar --entrada {DADOS}/txt`), pelo notebook
`notebooks/kaggle/02_sub-002.ipynb` (clona a tag no Kaggle, instala, roda e gera o CSV). As citações, os spans, as classes e os
ids vêm das regras aplicadas ao texto oficial e da consulta à base oficial. **Nenhum dado sintético entra na submissão.**

O sintético entrou em um único lugar: como base estatística da **tabela de confiança** (`taxa_acerto.json`, seção 4). Ele nunca
muda uma resposta; só influencia o número de `confianca` enviado por caminho de decisão.

---

## 3. Os conjuntos de dados

| Conjunto | O que é | Origem | Para que serve |
|---|---|---|---|
| **Amostra** | 26 documentos oficiais, 192 citações, gabarito aberto | Organização | Validar o pipeline ponta a ponta; é o que o leaderboard de treino usa |
| **Ajuste** | 14 documentos da amostra | Divisão nossa (ADR-009) | Olhar erros e escrever regras |
| **Controle** | 12 documentos da amostra, **nunca** usados para ajustar regras | Divisão nossa (ADR-009) | Medir se as regras generalizam |
| **Sintético** | 200 documentos (100 pares limpo × ruidoso), 994 citações | Nosso gerador (semente 0) | Testar textos que nunca vimos: recall e generalização |
| **Sintético-treino** | 160 documentos do sintético | Nosso gerador | Ajustar regras com margem para medir |
| **Sintético-controle** | 40 documentos do sintético, nunca usados para ajustar | Nosso gerador | Medir generalização no sintético |
| **Conjunto final cego** | Documentos novos, que ainda não vemos | Organização | **Define o ranking**: 40% público, 60% privado |

Não existe "sintético-controle oficial". *Controle* significa só "fatia reservada para medir": oficial na amostra, artificial no
sintético.

### Fases de avaliação do desafio

- **Treino (01–30/09):** leaderboard sobre a **amostra** (gabarito aberto). Referencial: valida o pipeline, não mede generalização.
- **Final:** conjunto **cego novo**; o leaderboard reinicia com 40% dele e o ranking final vem dos 60% privados, sigilosos até o fim.

---

## 4. O calibrador e a confiança

Cada citação termina em um **caminho de decisão** (`numero_unico`, `sem_numero`, `numero_ambiguo`…). O comando
`verificador calibrar` mede, por caminho, a fração de acertos no controle e grava em `src/verificador/avaliacao/taxa_acerto.json`.
Essa fração vira a `confianca` de cada citação daquele caminho (ADR-008). O calibrador **não decide nada**, só produz a tabela.

A métrica dá um bônus de calibração `b = 0,10 · (1 − Brier)`, medido sobre os pares casados. Com ~99,6% de acerto nos casados,
mandar qualquer confiança perto de 1 já rende ~+0,0996.

**Origem da tabela atual (`sub-002`):** amostra-controle (91 observações) + sintético-controle (190) = 281 observações.
Brier 0,00324 contra 0,00355 de uma confiança constante. Ajustada e medida no mesmo controle, então otimista; **fora da amostra**
(ajustando em ajuste + sintético-treino e medindo no controle) ficou empatada com a constante (0,003559 × 0,003551).

Ressalvas: quase todos os caminhos têm taxa 1,0 (exceto `numero_ambiguo`, 0,909). Se o conjunto final tiver mais erros que o
controle, o Brier sobe rápido. Suavizar as taxas de n pequeno reduziria esse risco.

---

## 5. Notas locais atuais (métrica oficial, gabarito aberto)

### Quais notas importam

| Nota | Papel |
|---|---|
| **Leaderboard do Kaggle** (treino, amostra) | Única nota "oficial" na fase atual, mas referencial. **Ainda não existe.** |
| **Controle da amostra** | Melhor medida honesta dos dados reais: nunca ajustamos regras nele |
| **Amostra inteira** | Só confere o pipeline; não informa generalização |
| **Sintético-controle / sintético** | Termômetro de generalização e de recall, com viés (regras e gerador escritos por nós) |
| **Conjunto final cego** | A nota que vale de fato. Só será conhecida na fase final |

### Score final: `sub-001` (base) × `sub-002` (novo)

| Conjunto | `sub-001` (sem confiança) | `sub-002` sem confiança | **`sub-002`** |
|---|---|---|---|
| Amostra | 0,9885 | 0,9885 | **1,0860** |
| Ajuste | 0,9955 | 0,9955 | **1,0937** |
| Controle | 0,9823 | 0,9823 | **1,0793** |
| Sintético | 0,8864 | 0,9263 | **1,0189** |
| Sintético-treino | 0,8875 | 0,9249 | **1,0174** |
| Sintético-controle | 0,8817 | 0,9319 | **1,0250** |

Em todos os conjuntos: τ = 0 e nenhum span espúrio.

### Por nível (`sub-002`)

| Conjunto | Nível 1 | Nível 2 | Bônus b (n1 / n2) |
|---|---|---|---|
| Amostra | 1,1000 | 1,0791 | 0,1000 / 0,0980 |
| Controle | 1,1000 | 1,0689 | 0,1000 / 0,0980 |
| Sintético | 1,0331 | 1,0119 | 0,0999 / 0,1000 |

### Recall de citações achadas

| Conjunto | `sub-001` | `sub-002` |
|---|---|---|
| Amostra | 192/192 | 192/192 |
| Sintético | 821/994 (82,6%) | **893/994 (89,8%)** |
| Sintético-controle | 172/210 (81,9%) | **190/210 (90,5%)** |

72 citações novas no sintético; 0 sumiram; 0 trocaram de classe ou id.

### De onde vem o ganho

- **Recall (causas 2 e 3):** +0,040 no sintético. Na amostra é 0, porque ela já estava 100% coberta.
- **Confiança:** +0,093 no sintético e +0,098 na amostra, quase todo o teto do bônus (0,10).
- **F1 no sintético (nível 1):** `real` 0,958 → 1,000; `inventada` 0,941 → 0,988; `incompleta` 0,802 → 0,830.

### O que ainda escapa

101 citações do sintético não são achadas: cerca de 75 são a forma (d) com moldes novos (causa 1) e sobram `CautInom nº 87`,
`CorPar nº …` e `DCG-…` (resíduo da causa 2, não investigado). A causa 4 (OCR no 1º dígito) segue pendente.

---

## 5-A. Fechamento da Fase 3 — causas 2 (resíduo) e 4 do recall (2026-09-21)

Quatro correções, aplicadas e medidas **uma por vez** (ADR-009). Nenhuma delas toca a amostra oficial, que já
estava em 192/192 — o ganho é inteiramente de **generalização**, medido no sintético.

| # | Correção | Onde | Recuperou |
|---|---|---|---|
| A | sigla solta `CorPar` (esquecida no commit `bd1ccdc`, que a acrescentou às outras 9 classes) | `tabelas/classes.json` | +6 |
| B | hífen como conector, só antes de número CNJ (`DCG-1340-57.2017.5.17.0010`) | `extracao/padroes.py` | +2 |
| D | OCR: ordem das operações + decisão por grupo | `texto/normalizacao.py` | +19 |
| C | número curto com marcador `nº` obrigatório (`CautInom nº 87`) | `extracao/padroes.py` | +2 |

### Antes × depois

| Conjunto | Score antes | Score depois | Recall antes | Recall depois |
|---|---|---|---|---|
| Amostra oficial | 1,08604 | **1,08604** (inalterado) | 192/192 | 192/192 |
| Controle (amostra) | 1,07925 | **1,07925** (inalterado) | 91/91 | 91/91 |
| Sintético | 1,01890 | **1,03940** | 893/994 (89,8%) | **922/994 (92,8%)** |
| Sintético-treino | 1,01740 | **1,03848** | 703/784 | 726/784 |
| Sintético-controle | 1,02500 | **1,04293** | 190/210 | **196/210 (93,3%)** |

Critérios de aceite, todos atendidos: amostra intacta em 192/192; **precisão de spans 1,0** (nenhum span
espúrio) em todos os conjuntos; **τ = 0**; melhora **também no controle**; `pytest` 136 verde; determinismo R49
em amostra e sintético. `comparar`: **29 citações apareceram, 0 sumiram, 0 trocaram de classe ou id**.
O `submission.csv` da amostra é **idêntico ao já submetido** — o leaderboard segue 1,08604, como previsto.

### Dois falsos positivos que a medição pegou (e como foram corrigidos)
Valem registro porque mostram o risco de alargar regex sem medir:
1. A primeira versão da regra de OCR decidia pelo **token inteiro** e transformava `REsp 1.111.222 – GO` em
   `…-90`: a UF de Goiás é feita só de letras confundíveis. Resolvido com a decisão por **grupo** entre
   separadores mais um guarda que impede o token de invadir uma sigla (`…456-SP`).
2. O guarda do número curto era estrito demais (`(?![\d.\-])`) e rejeitava `CautInom nº 87.` por causa do
   ponto final da frase. Como a alternância já tenta o número longo primeiro, bastou excluir dígito (`(?!\d)`).

### O que sobrou
O resíduo é **72 citações, 100% forma (d)** com molde de frase novo, todas da classe `incompleta` — é a
**causa 1** por inteiro. Ela não precisa de número nem de consulta à base: reconhecer o span *é* o problema,
que é exatamente o caso de uso do encoder NER (ADR-011). Segue para planejamento via `/sdd`.

---

## 6. Como ler tudo isso

1. O que confirma que o pipeline funciona é a nota do **leaderboard** na amostra (a obter).
2. O que informa generalização é o **controle da amostra**, complementado pelo **sintético-controle**.
3. O que vale de fato é a nota do **conjunto cego final**, que ainda não conhecemos. Otimizar demais para o leaderboard público
   não garante o resultado final (ADR-009).
4. Toda mudança futura deve ser medida com `verificador comparar` contra a linha de base e só é aceita se melhorar também o controle.

---

## 7. Origem dos dados da tabela de confiança — análise (2026-09-21)

A tabela da `sub-002` mistura amostra-controle (91 obs., oficial) e sintético-controle (190 obs.). A pergunta levantada:
tirar o sintético reduziria a generalização?

### Calibração não é treino

As regras de extração e decisão são escritas à mão; o sintético nunca as treinou. Tirá-lo da tabela **não muda nenhuma
citação, classe, span ou id** — só o número de `confianca` anexado. Generalização do *sistema*: impacto zero.
O trade-off existe só na generalização da *estimativa de confiança*.

### O que cada lado oferece

**A favor do sintético — cobertura da dimensão de OCR:**

| Conjunto | `correcao_ocr=false` | `correcao_ocr=true` |
|---|---|---|
| Amostra-controle | 91 | **0** |
| Amostra inteira | 187 | 5 |
| Sintético | 752 | **141** |

A tabela só-oficial tem 6 células, todas de texto limpo. Toda citação com número corrigido por OCR no conjunto cego cairia
na média de classe estimada só em texto limpo — e o **nível 2 vale o dobro** na nota final.

**Contra o sintético — circularidade:** ele contribuiu 190 observações com 190 acertos. Não é evidência, é construção: o
gerador deduz o gabarito com a *mesma lógica de consistência* da decisão (ADR-007, `sintetico/verdade.py`). Cobre a dimensão
de OCR, mas afirmando uma tautologia.

### Dois fatos da métrica que enquadram o risco

- `b = max(0, min(0,10, 0,10·(1−Brier)))` e o Brier nunca passa de 1 → **`b` nunca é negativo**. Enviar confiança é sempre
  melhor ou igual a não enviar; não há risco de baixa, só tamanho do ganho.
- O Brier conta **só pares casados** (`brier_termos` é preenchido dentro do laço `for gi, pi in pares`). Extração espúria e
  citação não achada **não entram no Brier** — machucam o F1. A única exposição é "achei o span, errei a classe ou o id".

### Quanto vale a escolha

Bônus `b` simulado para uma acurácia real `a` no conjunto cego, entre os pares casados:

| Acurácia real no cego | Tabela mista (p≈0,996) | Só-oficial (p≈0,989) | Calibração perfeita |
|---|---|---|---|
| 0,99 | 0,09901 | 0,09901 | 0,09901 |
| 0,95 | 0,09504 | 0,09510 | 0,09525 |
| 0,90 | 0,09008 | 0,09021 | 0,09100 |
| 0,80 | 0,08016 | 0,08043 | 0,08400 |

Diferença entre mista e só-oficial: **0,00006 a 0,0003** de bônus, ou ~0,0003 de nota final (`score = s·(1+b)`). Mesmo contra
calibração perfeita, a mista perde só 0,004 no cenário de 80% de acurácia. O bônus está quase saturado: qualquer confiança
alta captura ~0,098 dos 0,10.

### Por que as duas opções falham pelo mesmo motivo

A tabela só-oficial diz 1,0 em 5 das 6 células (taxa geral 0,989); a mista diz 1,0 em 9 das 11 (0,996). **As duas afirmam
quase-certeza.** Trocar uma pela outra não resolve nada e ainda perde a cobertura de OCR. Nossa evidência independente é
90/91 acertos, em texto que a organização avisou ser mais fácil que o cego.

### Recomendação

Manter o sintético e **suavizar** as taxas: `taxa = (acertos + α·m)/(n + α)`, com `m ≈ 0,97` e `α ≈ 5–10`. Mantém a cobertura
de OCR, impede que 190 acertos circulares afirmem certeza, nenhuma célula sai em 1,0. ~10 linhas em `calibrar.py` + teste.

**Prioridade:** isso vale ~0,0003 de nota. A causa 1 (forma (d), ~75 das 101 citações perdidas) vale +7,2 pontos de recall e
a causa 4 vale +3,8 no nível 2 — **20 a 70× mais**. Se o tempo até 30/09 apertar, deixar a tabela como está e ir para o recall.

A `sub-002` ainda é local (sem push), então mover a tag depois de recalibrar não reescreve nada publicado.
