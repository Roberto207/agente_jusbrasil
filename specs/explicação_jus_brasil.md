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
superfície, mais realista e mais difícil). Detalhes na seção abaixo.

### O que é o Nível 2

Os documentos vêm em dois níveis. Na amostra de desenvolvimento são 13 de cada
(`gen_n1_*.txt` e `gen_n2_*.txt`), com o mesmo tipo de parecer, a mesma base canônica e as mesmas
três classes. O que muda é **como o texto está escrito**:

- **Nível 1 — formato padrão.** Texto limpo, citações no formato que um advogado digitaria:
  `AgInt no AREsp nº 1.996.496/RJ`, `Súmula Vinculante 10`, `art. 373, I, do CPC`.
- **Nível 2 — ruído de OCR + variação de superfície.** Simula um documento que foi impresso,
  escaneado e lido por OCR (reconhecimento óptico de caracteres), escrito por alguém com outro
  estilo. Dois tipos de problema se misturam:

  1. **Ruído de OCR** — o leitor óptico confunde letras parecidas:
     - no texto comum: `Fedcral` (federal), `origcm` (origem), `lnsurge` (insurge), `dellto`
       (delito), `equivocãda`, `Magãlhães`. Na amostra há 92 palavras corrompidas assim;
     - dentro das citações, que é onde dói: `5úmula 211 do STJ` (S virou 5), `AgInt no RESP
       21737l8` (1 virou l), `Recurso Especial Nº 170076O` (0 virou O), `R.Esp. n° 1.45g.779`
       (9 virou g), `RE nº 5. 230.808-DF` (espaço no meio do número).
  2. **Variação de superfície** — a mesma citação escrita de outro jeito:
     - abreviações diferentes: `Rec. Esp.`, `R.Esp.`, `REspe.`, `Ag. Int.`;
     - `No`, `n°`, `n.` no lugar de `nº`; UF entre parênteses `(SC)` ou com travessão `– SP`;
     - número sem pontuação (`1145207`, `7000171-3920237000000`) ou quebrado em linhas;
     - nomes longos por extenso: `EDcl nos EDcl no AgInt no Agravo em Recurso Especial`;
     - formatos do TST: `TST-ED-E-ED-ARR-1099-66.2011.5.02.0251`.

**Por que pesa o dobro:** é o cenário realista — peças escaneadas e texto sujo são o que um
verificador encontra em produção — e é onde soluções simples quebram. Uma busca exata por
`Súmula 211` não acha `5úmula 211`; um regex que espera `nº` não pega `No`. Como
`score_final = (1·N1 + 2·N2) / 3`, uma solução perfeita no Nível 1 e zerada no Nível 2 fica com
no máximo 0,37.

**Importante:** as posições (`inicio`/`fim`) continuam sendo contadas sobre o texto sujo, exatamente
como distribuído. Corrigir o OCR para achar a citação é permitido; entregar a posição do texto
corrigido não.

Regras principais (texto completo em `scope.md`):
- só modelos, bibliotecas e ferramentas de pesos e código abertos, sem API nem serviço pago na
  execução; pelas regras do Kaggle, código aberto com licença aprovada pela OSI;
- pesos em repositório público (ex.: Hugging Face) com link + revisão fixa; fine-tuning permitido se
  os pesos forem publicados;
- qualquer dataset público no treino — dados sintéticos da equipe valem se forem publicados;
- a solução inteira precisa caber no ambiente de avaliação: **1 GPU de 24 GB, ~8 vCPUs, 32 GB de
  RAM**, senão é desclassificada;
- rotular ou tentar inferir o conjunto de teste desclassifica.

---

## O entregável, em detalhe

Existem três artefatos distintos:

### 1. JSON por documento (o contrato real, schema 1.2)

É o output de fato do seu pipeline — um JSON por documento de entrada. Formato confirmado no
`json_to_submission.py` distribuído:

```json
{
  "documento_id": "gen_n1_001",
  "citacoes": [
    {"inicio": 589, "fim": 652, "trecho": "julgado do STF proferido em 2024 pela relatoria de Dias Toffoli",
     "tipo": "jurisprudencia", "classificacao": "incompleta", "resolucao": {}, "confianca": 0.9},
    {"inicio": 1284, "fim": 1302, "trecho": "...", "tipo": "lei",
     "classificacao": "real", "resolucao": {"id_canonico": "28893055"}, "confianca": 0.8}
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
- `trecho` e `tipo` (`jurisprudencia` ou `lei`): obrigatórios no JSON, mas não entram no CSV.
- `classificacao`: uma das 3 strings.
- `resolucao.id_canonico`: só relevante para `real`; é o doc_id numérico do Jusbrasil (coluna
  `id` da base, não a coluna `documento_id`, que tem valores tipo `doc_0001`). Nos outros casos
  fica ausente → `-` no CSV.
- `confianca`: opcional; ausência não penaliza nem bonifica.

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

As finalistas entregam um pacote: repositório com código, README, referência dos modelos (link +
revisão), ambiente (`requirements`/`Dockerfile`) e o **comando exato que reproduz as saídas
submetidas**, com decodificação determinística (temperatura 0, semente fixa). O que a organização
reproduz é a execução que gera a submissão, a partir dos pesos e dados publicados — não o treino.
Durante a competição o repositório fica privado (só a equipe); código só pode ser compartilhado
publicamente no fórum do Kaggle. Detalhes em `DESIGN.md` e ADR-010/ADR-014.

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
que sempre chuta `real` (a classe majoritária: 96 de 192 citações no gabarito da amostra)
teria nota alta mesmo ignorando `incompleta` (32 de 192, a mais rara) e `inventada` (64 de 192,
a mais central ao desafio). Macro-F1 evita isso. Para `real`, só conta acerto se o
`id_canonico` também bater.

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

## Status dos pontos que estavam em aberto

Resolvidos com o material distribuído — ver `scope.md` (contrato do JSON, detalhes da métrica e
divergência entre regulamento e gabarito) e `DEFINE.md` v2.
