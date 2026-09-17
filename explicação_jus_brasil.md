# Jusbrasil × BRACIS 2026 — Verificação de citações jurídicas em pareceres de IA

## Resumo do desafio

Competição Kaggle (privada, só estudantes do Brasil, times de até 4) para construir um
**verificador automático de citações jurídicas** geradas por LLMs. O problema real por trás:
LLMs usados para redigir peças jurídicas às vezes citam jurisprudência ou lei que não existe
("alucinação de fonte"), ou citam de forma vaga demais pra verificar — e isso já gerou sanção
a advogados em tribunais reais.

## A tarefa

Entrada: documentos judiciais em `.txt`.
Para cada documento, o sistema deve:

1. **Encontrar** todos os spans de texto que são citações de jurisprudência/lei.
2. **Classificar** cada span em uma de três classes:
   - **real** — resolve a um único registro da base canônica (SQLite fornecida); exige entregar
     o `id_canonico` correto — acertar a classe sem o link não conta.
   - **inventada** — tem identificadores suficientes pra buscar, mas nenhum registro
     correspondente existe na base congelada. É a alucinação ativa.
   - **incompleta** — informação insuficiente pra formular a busca (ex: "conforme jurisprudência
     pacífica do tribunal"), ou suficiente pra buscar mas insuficiente pra identificar um único
     registro. É evasiva, não uma invenção.

Dois níveis de dificuldade: Nível 1 (formato padrão) e Nível 2 (ruído de OCR + variação de
superfície, mais realista e mais difícil).

Regras: só modelos/ferramentas open-weight e open-source (sem API paga tipo GPT/Claude
comercial durante a execução final — servir um modelo aberto via API paga no desenvolvimento é
ok, desde que a mesma versão rode offline). Qualquer dataset público pode ser usado no treino.

---

## O entregável, em detalhe

Existem três artefatos distintos:

### 1. JSON por documento (o contrato real, schema 1.2)

É o output de fato do seu pipeline — um JSON por documento de entrada. Formato inferido a
partir da estrutura do CSV de submissão:

```json
{
  "documento_id": "gen_n1_001",
  "citacoes": [
    {"inicio": 469, "fim": 498, "classe": "incompleta", "id_canonico": null, "confianca": 0.9},
    {"inicio": 589, "fim": 652, "classe": "real", "id_canonico": "acordao_stj_12345", "confianca": 0.8}
  ]
}
```

Aqui mora toda a engenharia: extração de span (NER), classificação em 3 classes e, para `real`,
resolução de entidade contra a base canônica (achar o registro exato, não só confirmar
existência).

**Campos e cuidados:**
- `inicio`/`fim`: offsets em **codepoints Unicode**, contados sobre o `.txt` exatamente como
  distribuído. Bibliotecas que contam bytes UTF-8 (multibyte) ou normalizam o texto antes de
  indexar quebram isso silenciosamente.
- `classe`: uma das 3 strings.
- `id_canonico`: só relevante para `real`; nos outros casos vira `null`/ausente → `-` no CSV.
- `confianca`: opcional; ausência não penaliza nem bonifica.

Campos exatos do schema 1.2 (nomes, possíveis metadados extras) ainda não confirmados — checar
assim que o material chegar por e-mail (25/08).

### 2. `submission.csv` (o que sobe no Kaggle)

Gerado automaticamente pelo script fornecido `json_to_submission.py` a partir dos JSONs — não é
escrito à mão. Uma linha por `documento_id`:

```
documento_id,citacoes
gen_n1_001,"469,498,incompleta,-,0.9|589,652,real,acordao_stj_12345,0.8"
gen_n1_002,-
```

- Cada citação: `inicio,fim,classe,id_canonico,confianca`, separadas por `|`.
- Campos ausentes viram `-`.
- **Todo `documento_id` do conjunto precisa aparecer**, mesmo sem citações — célula `-`, nunca
  vazia.

### 3. Reprodutibilidade (só para os finalistas do topo)

Repositório de código publicado + commit exato que gerou as saídas submetidas, executável de
ponta a ponta sem chaves de API pagas. Vale desenhar o pipeline desde já como script
reproduzível (não notebook exploratório solto), seguindo o padrão do `agente_questoes_enem`
(`cli.py`).

### Script auxiliar: `kaggle_metric.py`

Mesma métrica que roda no leaderboard oficial — reproduz localmente o score contra o gabarito
da amostra de dev, permitindo validar antes de gastar o teto diário de submissões.

---

## Avaliação — como a nota é montada

### Matching: IoU (Intersection over Union) entre spans

Emprestado de visão computacional (sobreposição de caixas), aqui aplicado a spans de texto
(offsets de caractere). Mede o quanto seu span previsto e o span do gabarito se sobrepõem,
proporcionalmente:

```
IoU = tamanho(interseção) / tamanho(união)
```

**Exemplo:**
- Gabarito: 469–520 (tamanho 51)
- Predição: 480–530 (tamanho 50)
- Interseção: 480–520 → 40
- União: 469–530 → 61
- IoU = 40/61 ≈ 0,656 → acima do limiar 0,5 → **casa**

Acima de 0,5, a classe e o `id_canonico` da predição são comparados ao gabarito. Abaixo de 0,5,
os dois ficam "órfãos": a citação do gabarito vira **erro de recall** (não achada), a predição
vira **falso positivo**. O matching é **1-para-1 pelo maior IoU** — se duas predições disputam a
mesma citação do gabarito, só a de maior IoU casa; a outra é falso positivo (pune spans
redundantes/sobrepostos).

**Implicação prática:** não precisa acertar a borda exata (pequenos erros de espaço/pontuação
não derrubam o IoU abaixo de 0,5), mas o extrator de spans precisa ser preciso — pegar
parágrafo inteiro em vez da citação, ou só um pedaço dela, derruba o IoU abaixo do limiar.

### Os pesos — funil de 4 camadas

```
1. F1 por classe (real/inventada/incompleta), sobre os pares casados por IoU≥0,5
2. macroF1 = média simples das 3 F1s
3. s = macroF1 × (1 − 0,5 × τ)                    ← penalidade do erro grave
4. score_nível = s × (1 + 0,10 × (1 − brier))     ← bônus de calibração
5. score_final = (1×score_Nível1 + 2×score_Nível2) / 3   ← Nível 2 vale o dobro
```

**1. Macro-F1 (peso igual entre classes).** Média simples de F1(real), F1(inventada),
F1(incompleta) — não ponderada pela frequência de cada classe. Se fosse F1 comum, um sistema
que sempre chuta `real` (provavelmente a classe majoritária) teria nota alta mesmo ignorando
`inventada` — que é a classe mais rara e mais central ao desafio. Macro-F1 evita isso. Para
`real`, só conta acerto se o `id_canonico` também bater.

**2. Penalidade do erro grave (τ).** `τ` = fração das citações `inventada` do gabarito que você
classificou como `real`. Esse é um peso adicional, fora do F1, porque nem todo erro é igualmente
ruim: rotular alucinação como "incompleta" é leve (vai pra revisão humana); rotular alucinação
como **"real"** é o pior erro possível — é dizer "verifiquei, existe" para algo inventado,
exatamente o cenário que já gerou sanção a advogados. Se 100% das inventadas "vazarem" como
real (τ=1), a nota **cai pela metade**, independente do resto do desempenho.

**3. Bônus de calibração (Brier, até +10%).** Campo `confianca` opcional; se enviado, mede-se o
Brier score nos pares casados. Confiança alta quando acerta e baixa quando erra aproxima o
multiplicador de 1,10. Não enviar = multiplicador 1,0 (nunca penaliza).

**4. Peso entre níveis de dificuldade.** `score_final = (1·score_N1 + 2·score_N2) / 3` — Nível 2
(ruído de OCR, mais realista e mais difícil) **pesa o dobro** do Nível 1. Não dá pra ganhar só
otimizando o caso fácil.

Uma submissão perfeita com `confianca=1.0` nos dois níveis pontua exatamente **1,1000**.

---

## Fases de avaliação

- **Fase de treino (agora, 01–30/09)**: leaderboard sobre a amostra de desenvolvimento
  (gabarito aberto) — referencial, serve pra validar o pipeline ponta a ponta.
- **Fase final**: conjunto cego novo; leaderboard reinicia usando 40% dele (parte pública); o
  ranking final vem dos 60% privados, sigilosos até o fim. Otimizar demais pro leaderboard
  público não garante o resultado final.

---

## Referências aos meus outros projetos

- **[clarus/Synthera](../clarus)** — parente mais próximo tecnicamente: RAG jurídico com
  "citação fina obrigatória (página + cláusula)" e hybrid search BM25+vector. O desafio do
  Jusbrasil é o inverso do que o Synthera faz: o Synthera *gera* respostas com citação
  ancorada; aqui construo o **verificador** que audita se uma citação (de outro sistema) é
  ancorável de verdade. A lógica de resolver uma citação para um id único numa base estruturada
  é o mesmo tipo de entity linking já resolvido lá.
- **[agente_questoes_enem](../agente_questoes_enem)** — mesma filosofia de produto:
  "verificação automática antes da revisão humana". Lá, itens gerados passam por um crivo
  automático (rubrica/critérios) antes da revisão humana; aqui, `incompleta` vai pra fila de
  revisão humana e `inventada` é bloqueada automaticamente. Mesmo padrão de pipeline
  **gerar → verificar → (bloquear | liberar | escalar pra humano)**.
- **[agente_estudos](../agente_estudos)** — mostra viabilidade de um agente com ferramentas
  (busca, parsing) decidindo os passos por conta própria; útil se a abordagem escolhida aqui for
  agêntica (LLM com tool de busca na base canônica) em vez de pipeline de NER fixo.

---

## Cronograma

| Marco | Data |
|---|---|
| Abertura das inscrições | 18/08/2026 |
| Envio dos dados por e-mail | 25/08/2026 |
| Webinar de tira-dúvidas | 28/08/2026 |
| Submissões com leaderboard ao vivo | 01/09 a 30/09/2026 |
| Fechamento das submissões | 30/09/2026, 23h59 BRT |
| Apresentação no BRACIS 2026 (Cuiabá-MT) | 19 a 22/10/2026 |

## Em aberto até os dados chegarem (25/08)

- Nomes exatos dos campos do schema 1.2 do JSON.
- Possíveis metadados extras por documento.
- Convenção de nomes de `id_canonico` na base SQLite.
