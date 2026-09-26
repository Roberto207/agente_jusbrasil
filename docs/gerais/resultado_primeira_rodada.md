# Resultado da primeira rodada — versão só-regras

> **Documento histórico (25/09).** Retrato da primeira versão só-regras (18–19/09). Desde então: `sub-002`
> a `sub-006`, nota 1,1 na amostra, reforço do regex e encoder ligado. Estado atual em
> `docs/resultado_submissoes.md` e `tarefas_equipe.md`.

**Data:** 2026-09-18/19 · **Código:** `main`, ainda sem commit · **Ainda não submetida ao Kaggle.**
Detalhe técnico dos erros: `docs/gerais/analise_erros_baseline.md`. Próximos passos: `tarefas_equipe.md`, seção 3.1.

---

## 1. Resumo em uma frase

Na amostra oficial o sistema tira **0,9885 de 1,000**, sem nenhuma citação inventada chamada de real. Mas em textos
que ele nunca viu (o conjunto sintético) tira **~0,88**. A diferença entre os dois números é o problema de
**generalização**, explicado na seção 5.

---

## 2. Como a nota funciona (`kaggle_metric.py`)

Para cada nível de dificuldade:

```
score_nível = macroF1 · (1 − 0,5·τ) · (1 + b)
```

| Peça | O que mede | Valor ideal |
|---|---|---|
| **macro-F1** | Média do F1 das três classes (`real`, `inventada`, `incompleta`). Uma citação só conta como acerto se o span casar com o do gabarito (IoU ≥ 0,5) e a classe for a certa; para `real`, o id também precisa estar certo. | 1 |
| **τ (tau)** | Fração das citações **inventadas** que o sistema chamou de **reais**. É o erro grave: cada ponto de τ corta a nota pela metade desse ponto. | 0 |
| **b (bônus)** | Calibração da `confianca` enviada (Brier score). Vai de 0 a +0,10. Quem não envia confiança fica com `b = 0`, sem punição. | 0,10 |

A nota final junta os dois níveis, com o nível 2 (texto com ruído de OCR) valendo o dobro:

```
score_final = (1 · nível1 + 2 · nível2) / 3
```

Por isso **o máximo possível é 1,100**: 1,000 de acerto perfeito vezes 1,10 de bônus perfeito.

---

## 3. As métricas que atingimos

### Amostra oficial (26 documentos, 192 citações — a mesma que o leaderboard de treino usa)

| Conjunto | Score final | Nível 1 | Nível 2 | τ | Citações achadas |
|---|---|---|---|---|---|
| Amostra inteira | **0,9885** | 1,0000 | 0,9827 | 0 | 192/192 |
| ↳ parte de ajuste (14 docs) | 0,9955 | 1,0000 | 0,9932 | 0 | 101/101 |
| ↳ parte de controle (12 docs) | 0,9823 | 1,0000 | 0,9734 | 0 | 91/91 |

Das 192 citações, **190 recebem a resposta certa**. As 2 erradas:

> ⚠️ **Corrigido em 2026-09-21.** O texto abaixo era o entendimento da época e **estava errado nos dois
> casos**. A investigação está em `docs/gerais/limites_de_decisao.md`; o resumo é:
>
> - **`gen_n2_010` não é empate entre registros idênticos.** Os dois registros são processos diferentes:
>   `2684973273` é `AgInt no RECURSO ESPECIAL`, e `2679428592` é `AgInt nos EMBARGOS DE DIVERGÊNCIA EM
>   RESP`. A citação diz "Recurso Especial" e casa só com o primeiro. A ambiguidade é fabricada por uma
>   lacuna nossa: `classes.json` não conhece "Embargos de Divergência" (11 registros da base têm essa
>   classe), então o índice lê os dois como `REsp` e o desempate do ADR-007 fica sem sinal. **É defeito
>   do sistema, e corrigível.**
> - **`gen_n2_005` provavelmente não é erro do gabarito.** Três registros TST dividem o mesmo número CNJ
>   (estágios do mesmo caso) e o gabarito aponta o mais antigo. A hipótese mais provável é que a
>   organização vincule ao **caso**, não ao estágio recursal — o que seria um critério de desempate, não
>   um erro. Falta confirmar com a organização.

*Texto original, mantido para registro:*

- **`gen_n2_010`** — a base tem **dois registros idênticos** para o mesmo processo (mesma classe, recurso e UF). Não há
  como escolher um sem chutar, e a regra é "na dúvida, nunca `real`": o sistema responde `incompleta`, o gabarito `real`.
- **`gen_n2_005`** — a citação diz `AgARR`, mas o gabarito aponta um registro `AIRR`. O sistema segue o que está escrito;
  o gabarito parece ter um erro. Corrigir isso seria decorar o gabarito.

### Conjunto sintético (200 documentos, 994 citações, gerados por código)

| Conjunto | Score final | Nível 1 | Nível 2 | τ | Citações achadas |
|---|---|---|---|---|---|
| Sintético inteiro | **0,8864** | 0,9004 | 0,8793 | 0 | 821/994 (82,6%) |
| ↳ treino (160 docs) | 0,8875 | 0,9018 | 0,8804 | 0 | 649/784 |
| ↳ controle (40 docs) | 0,8817 | 0,8947 | 0,8751 | 0 | 172/210 |

- **Toda citação que o sistema acha recebe a classe e o id certos** (nenhum erro de classificação em 821) — em parte
  por construção, ver as ressalvas da seção 5.
- **Nenhum trecho inventado** (precisão de span 100%): frases como "jurisprudência pacífica desta Corte" nunca viram citação.
- **Limpo × ruidoso:** em 96% dos pares, o mesmo documento com e sem ruído de OCR tem exatamente a mesma resposta.
- **Toda a perda é de recall**: 173 citações não são achadas. As 4 causas estão em `tarefas_equipe.md` (3.1-b).

### Por que 0,9885 e não 1,100

| Parcela | Quanto falta | Por quê |
|---|---|---|
| Acerto (de 0,9885 até 1,000) | 0,0115 | As 2 citações da seção acima |
| Bônus de confiança (de 1,000 até 1,100) | 0,100 | **Não enviamos `confianca`** nesta rodada |

Com uma confiança bem calibrada, a amostra iria para perto de **1,08**. É a proposta 3.1-a do `tarefas_equipe.md`.

---

## 4. Configuração do sistema que produziu esses números

**Só regras e consulta à base. Sem modelo de linguagem, sem encoder, sem GPU, sem rede, sem confiança.**

| Etapa | O que faz nesta rodada | Onde |
|---|---|---|
| Índice da base | Lê os 1.014 registros e extrai o número próprio de cada um (1.013 identificados) | `base/` |
| Texto | Separa o cabeçalho (nada dele é citação), limpa OCR (`21737l8` → `2173718`, `5úmula` → `Súmula`) e guarda o mapa de posições para os spans voltarem ao texto original | `texto/` |
| Extração | Expressões regulares para as 4 formas: processo com número, súmula, artigo de lei, julgado sem número | `extracao/padroes.py` |
| Leitura de campos | Tribunal, classe, cadeia de recursos, número, UF, lei, artigo, ano, relator | `extracao/campos.py` |
| Decisão | 10 caminhos fixos (+1 para campos não lidos): número inexistente → `inventada`; existe mas contradiz a citação → `inventada`; um registro compatível → `real`; vários → `incompleta`; sem número → `incompleta` | `decisao/` |
| Saída | JSON por documento, validado antes de gravar, convertido pelo script oficial | `saida/` |

Configuração (`verificador.toml`):

```toml
usar_encoder = false             # encoder NER: Fase 4, só entra se ganhar desta linha de base
usar_llm = false                 # LLM leitor de campos: Fase 5, idem
extrair_referencia_vaga = false  # ADR-005, aguardando resposta da organização
semente = 0
```

Tempo: a amostra inteira roda em menos de 1 segundo em CPU. Duas execuções geram o mesmo `submission.csv` byte a byte.

---

## 5. A questão da generalização, explicada

### O problema

O sistema não aprende sozinho: **quem "aprende" somos nós**, escrevendo regras olhando os exemplos. Com só 26 documentos,
escritos com poucos moldes de frase, é fácil escrever regras que acertam **exatamente aqueles textos** e falham em textos
um pouco diferentes. Isso se chama **sobreajuste** (overfitting): decorar a prova em vez de aprender a matéria.

Um exemplo concreto: na amostra, toda citação sem número aparece assim:

> julgado do STF proferido em 2024 pela relatoria de Dias Toffoli

O regex foi escrito para esse molde e acerta 32 de 32. Mas se o conjunto final escrever

> decisão colegiada do STM em 2025, relatada pelo Ministro X

o regex não acha nada. A nota da amostra continua 100% nessa forma, e mesmo assim o sistema falharia no texto novo.

### Por que a nota da amostra engana

1. **O leaderboard da fase de treino usa a própria amostra**, que tem gabarito aberto. Uma nota alta ali mostra que as
   regras cobrem esses 26 textos, não que funcionam em outros. Dá para chegar a ~1,1 no leaderboard só decorando.
2. **O ranking final é calculado sobre o conjunto final cego**, que a organização avisa poder ter moldes, leis e formas
   de erro que a amostra não tem. Esse conjunto nós não vemos (e é proibido ajustar regras olhando para ele).

### Como estamos medindo de forma honesta (ADR-009)

| Medida | Como funciona | O que responde |
|---|---|---|
| **Ajuste × controle** | A amostra foi dividida uma única vez: 14 documentos para olhar os erros e ajustar regras, 12 que **nunca** são usados para ajustar, só para medir | "As regras funcionam em documentos da amostra que não usei para escrevê-las?" |
| **Conjunto sintético** | Um gerador fabrica documentos novos, com frases, leis, números e ruídos variados, e já sabe a resposta certa de cada citação | "As regras funcionam em textos que eu não vi?" |

Leitura dos nossos números com essa lente:

- **Ajuste 0,9955 × controle 0,9823**: diferença pequena. Não há sinal de que as regras decoraram documentos específicos
  da amostra.
- **Amostra 0,99 × sintético 0,88**: diferença grande, **e ela é a estimativa honesta do risco**. O sistema acha 100% das
  citações da amostra, mas só 82,6% das do sintético. As citações que não acha são justamente as de formas que a amostra
  não tem (moldes novos, siglas por extenso, `Súmula n. 83`).
- **O que é bom sinal:** o que o sistema acha, ele classifica certo (0 erros de classe no sintético) e nunca chama uma
  inventada de real. O problema medido é **cobertura** (achar), não **julgamento** (decidir) — com as ressalvas abaixo
  sobre o quanto o sintético consegue testar o julgamento.

### O problema medido é recall de extração

Toda a perda no sintético vem de citações **não encontradas** (cada uma vira falso negativo da sua classe e derruba o F1
dela). Por classe:

| Classe | Não encontradas | Principal causa |
|---|---|---|
| incompleta | 85 de 254 (33%) | forma (d) com molde de frase novo |
| inventada | 50 de 342 (15%) | siglas por extenso, `Súmula n.`, OCR |
| real | 38 de 398 (10%) | siglas por extenso, `Súmula n.`, OCR |

O ganho está em **achar mais**, e a classe mais prejudicada é `incompleta`. Mas "decisão e precisão estão boas" deve ser
lido com as ressalvas abaixo.

### Ressalvas sobre o que o sintético consegue provar

**1. O gerador também foi escrito por nós.** Pode ter o mesmo viés das regras, ou exagerar formas que talvez nunca
apareçam. Os 0,88 são uma estimativa, não uma previsão. A causa `Súmula n. 83` é a mais confiável (a própria base escreve
assim); os moldes novos da forma (d) são a mais incerta.

**2. O "0 erros de classificação" no sintético é em parte circular.** O gerador deduz o gabarito de cada citação aplicando
a **mesma lógica de consistência** que a decisão usa (ADR-007, em `sintetico/verdade.py`): mesmo filtro de tribunal, UF,
classe e cadeia de recursos. Se uma regra de decisão estiver errada — por exemplo, se eliminar candidatos pela classe no
TST não for o que a organização espera —, gerador e decisão erram **juntos** e o teste passa mesmo assim.

- O que o sintético **prova**: que a leitura do texto (frente B) chega aos mesmos atributos (classe, cadeia, UF, número)
  que o gerador usou, e que a cadeia texto → campos → índice não perde informação.
- O que ele **não prova**: que as regras de decisão estão certas.
- Onde as regras são testadas contra um gabarito **independente**: só na amostra oficial (190/192, com os 2 erros
  explicados). É pouco exemplo para os casos raros — número emprestado (nenhum na amostra) e registros duplicados (um só).

**3. A precisão de 100% também é otimista.** Os distratores do gerador são poucos e fixos ("jurisprudência pacífica",
"fls. 10/20", um número de protocolo). O conjunto final pode ter textos que o regex capture por engano — números de
lei soltos, referências a páginas, siglas parecidas com classes —, e esse tipo de erro não apareceria no sintético.

**Consequência prática:** toda correção é medida no ajuste e no sintético de treino e só é aceita se também melhorar o
**controle**; e a primeira submissão real é a primeira medida externa de decisão e precisão. Se a nota do leaderboard
diferir da local, a investigação começa por essas duas frentes, não pelo recall.

---

## 6. O que falta para esta rodada virar submissão

1. **Commit** do código (hoje tudo está fora do git; a submissão exige árvore limpa e uma tag `sub-001`).
2. Rodar o notebook no Kaggle na tag e **enviar o `submission.csv`**.
3. **Comparar** a nota do leaderboard com a local (0,9885). Como a amostra é a mesma dos dois lados, uma diferença grande
   indica erro de pipeline e deve ser investigada antes da próxima submissão.
