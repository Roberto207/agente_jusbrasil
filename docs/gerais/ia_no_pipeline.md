# IA no pipeline — onde, como e com que custo

**Data:** 2026-09-17
**Natureza:** registro da análise feita pela equipe antes de revisar o `DESIGN.md`. As decisões que
saíram daqui estão nos ADR-001 (revisado), ADR-011, ADR-012, ADR-013 e ADR-014.
**Base:** regras completas do desafio (`scope.md`), dados da amostra e pesquisa listada em
"Fontes".

---

## 1. O princípio: IA na leitura, consulta na decisão

O pipeline faz dois trabalhos de natureza diferente:

| Trabalho | Etapas do `DESIGN.md` | Quem faz melhor |
|---|---|---|
| **Ler linguagem** — achar o trecho, entender `Rec. Esp.`, tolerar OCR | [1] texto, [2] extração, [3] campos | modelos de IA ajudam muito |
| **Consultar fatos** — esse processo existe na base? | [A] índice, [4] decisão | consulta determinística; IA atrapalha |

Evidência externa: o benchmark **CITE** ("Who Checks the Citations?", 2026) testou LLMs
verificando citações jurídicas alucinadas. O melhor sistema (GPT-5 como agente, com acesso a banco
de jurisprudência) teve **F1 de 55%** (precisão 40,8%). Os autores apontam o **acesso ao banco de
dados** como gargalo, e 25% das citações ausentes do banco foram marcadas como falsas por engano.
No desafio a base é local e completa, então a consulta determinística já resolve a parte difícil;
a IA deve ficar do lado da leitura.

Por que um LLM não decide a classe: ele não sabe o que existe na cobertura congelada. Diante de
`REsp 1.741.784/PR` tende a dizer "real" porque parece real — o erro que corta a nota pela metade
(penalidade τ).

## 2. Por que o Nível 2 é o alvo principal da IA

O Nível 2 vale o dobro e mistura ruído de OCR (`5úmula`, `21737l8`, `Fedcral`) com variação de
superfície (`Rec. Esp.`, `No`, `(SC)`, nomes por extenso). Os moldes da amostra são poucos; o
conjunto final pode trazer frases que nenhum regex previu. A perda de recall só apareceria no
conjunto cego, onde não há como medir — por isso a análise de erro na amostra não basta para
decidir se a IA é necessária.

## 3. Opções analisadas por ponto do pipeline

### 3.1 Extração [2] — maior valor

| Opção | Como | Prós | Contras | Veredito |
|---|---|---|---|---|
| **A1. LLM zero/few-shot** | LLM recebe o parágrafo e devolve citações; LangExtract devolve as posições exatas | Generaliza para frases novas sem treino | Estudo em NER português: LLMs locais 7–14B tiveram F1 ~0,55 no LeNER-Br; supervisionados, 0,87–0,92. GPU, lento, posições via texto gerado | Não como extrator principal |
| **A2. Encoder NER supervisionado** | BERT português marca palavra por palavra o que é citação (BIO) | Posições nativas, rápido, determinístico, roda em CPU ou GPU, pequeno | Precisa de dados rotulados: 192 citações é pouco → sintético + LeNER-Br. Convenção de anotação do LeNER-Br difere do gabarito | **Recomendado** (ADR-011) |
| **A3. GLiNER** | Modelo pequeno (< 500M) que acha entidades pelo nome do tipo, multilíngue | Sem treino, CPU, dá para refinar com poucos exemplos | Sem avaliação conhecida em texto jurídico brasileiro | Alternativa a testar se A2 atrasar |
| **A4. Fine-tuning de LLM (LoRA)** | Unsloth no Kaggle; Qwen3.5-4B pede ~10 GB | Aprende formato e ruído | Herda os problemas de A1; treino mais caro | Não compensa diante de A2 |

Candidatos de encoder (licença a conferir contra a regra OSI antes de escolher):
- **BERTimbau** (NeuralMind), base e large;
- **Legal-BERTimbau**;
- **RoBERTaLexPT** — pré-treinado em ~125 GB de texto jurídico brasileiro (LegalPT), supera
  modelos maiores em tarefas jurídicas;
- modelos já treinados no **LeNER-Br** (F1 0,893 base / 0,908 large), que tem as entidades
  `LEGISLACAO` e `JURISPRUDENCIA`.

Uso previsto: **união** das candidatas do regex e do encoder, filtrada pelas quatro formas de
citação do `DEFINE.md` (o encoder não pode trazer "a jurisprudência pacífica desta Corte" de volta).

### 3.2 Leitura de campos [3]

| Opção | Como | Veredito |
|---|---|---|
| **B1. LLM com saída estruturada** | Só para citações que o leitor por regras não consegue ler (classe depois do número, OCR pesado, apelido desconhecido). LLM devolve JSON com campos; o número só é aceito se os dígitos saírem do trecho | **Opcional, entra por medição** (ADR-013) |
| **B2. Tabelas + distância de edição** | Sem IA | Base, cobre a maior parte |

Modelos candidatos para B1 (licença Apache 2.0): **Qwen3** 4B/8B, **Gemma 4** E4B. Descartados
pela regra OSI: GAIA (Gemma 3), Gemma 3, Llama.

### 3.3 Resolução [A]/[4] — onde entraria "RAG"

RAG clássico (buscar por semelhança + LLM responde) é **a ferramenta errada para decidir**:
- semelhança acha o parecido, não o igual — `REsp 1.741.785` ≈ `REsp 1.741.784`;
- o LLM tende a "real" diante de algo parecido;
- embeddings representam mal a diferença entre números.

O que aproveitamos da parte "buscar":
- **C1.** Casamento aproximado de números com mapa de confusões de OCR (`21737l8` → `2173718`) —
  sem IA, maior ganho no Nível 2.
- **C2.** O índice FTS5 que vem na base, para gerar candidatos, com conferência de que o número
  está no cabeçalho do registro (busca no texto inteiro traria 2 de 40 inventadas como candidatas
  e 10 de 77 reais ambíguas, medido na amostra).

### 3.4 Geração de dados — maior custo-benefício

Gerador sintético em duas camadas (ADR-012):
1. **Por código** (CPU): escolhe citações reais da base, fabrica inventadas (número emprestado com
   UF trocada, artigo inexistente de lei conhecida, número perturbado), injeta ruído de OCR. Gabarito
   sai de graça.
2. **Por LLM** (GPU): escreve a redação em volta da citação com frases variadas.

Serve para medir generalização (ADR-009) e treinar o encoder (ADR-011). Regra: dados sintéticos
usados no treino são **publicados** dentro do prazo.

### 3.5 Confiança [5]

| Opção | Veredito |
|---|---|
| E1. Tabela por caminho de decisão | Atual (ADR-008) |
| E2. Regressão logística / gradient boosting sobre caminho, correções de OCR, nº de candidatos, tamanho do trecho, com calibração | Testar se E1 não bater a confiança constante |

### 3.6 Abordagens que não se encaixam

| Abordagem | Por quê não |
|---|---|
| Agente com ferramentas (como no CITE) | Serve para banco remoto e enorme; a base aqui é local e pequena |
| Aprendizado ativo, anotação humana | Não cabe no prazo; e rotular o conjunto final é proibido (Foundational 4b) |
| Correção de OCR com modelo neural (ex.: ByT5) | Pesado; o mapa de confusões cobre os casos da amostra |

## 4. Recomendação

| Prioridade | O quê | Onde | Por quê |
|---|---|---|---|
| 1 | LLM como gerador de dados sintéticos | fora da execução | Maior valor por esforço; destrava 2 e mede tudo |
| 2 | Encoder NER treinado no sintético + LeNER-Br, em união com o regex | [2] | Frases novas, posições exatas, rápido, determinístico |
| 3 | Casamento aproximado de números com mapa de OCR | [A]/[4] | Resolve o Nível 2 sem IA |
| 4 | LLM com saída estruturada para campos difíceis | [3] | Opcional, entra se a medição mostrar ganho |
| — | Não fazer: RAG para decidir; LLM zero-shot como extrator principal; fine-tuning de LLM | | Risco de τ, F1 menor, custo alto |

## 5. Fluxo de uso

### Desenvolvimento (antes, em qualquer ambiente)

| O quê | Onde |
|---|---|
| Gerar dados sintéticos com LLM | Kaggle GPU |
| Treinar o encoder e publicar pesos no Hugging Face (revisão fixa) | Kaggle GPU |
| Publicar os dados sintéticos | Hugging Face (dataset público) |
| Índice, regras, avaliação | qualquer CPU (máquina local ou Kaggle CPU) |

### Execução (o comando que gera a submissão — um ambiente só)

```
python -m verificador rodar --entrada txt/ --saida runs/<id>

INÍCIO
  · monta o índice a partir do .db                              CPU
  · carrega o encoder (link + revisão fixa)                     GPU
  · carrega o LLM, se ligado (temperatura 0, seed fixa)         GPU

PARA TODOS OS DOCUMENTOS
  [1] cabeçalho, normalização, mapa de posições                 CPU
  [2] regex ∪ encoder → filtro das 4 formas → sobreposição      CPU + GPU
  [3] campos por regras → não leu? vai para a fila de difíceis  CPU

UMA CHAMADA EM LOTE
  [3b] LLM lê a fila → JSON → conferência dos dígitos           GPU

DE VOLTA PARA CADA CITAÇÃO
  [4] decisão contra o índice · [5] confiança · [6] JSON → CSV  CPU
```

- O LLM roda em lote, não por documento (na amostra, ~10% das 192 citações seriam ~20 chamadas).
- O LLM nunca decide a classe; a leitura dele é conferida contra o texto.
- Orçamento de VRAM no ambiente de avaliação (24 GB): encoder ~0,5 GB; Qwen3 8B em fp16 ~16–17 GB
  + cache; 14B só com 8 bits.

### Uso real (produto)

Encoder e LLM carregados uma vez num serviço; cada parecer passa por [1]–[4] em milissegundos;
só as difíceis vão para a fila do LLM em lotes de poucos segundos. Saída marcada em verde/vermelho/
amarelo, com a confiança decidindo a revisão humana. Diferença crítica para o desafio: **não existe
cobertura congelada** — "não achei" não é "inventada"; um produto precisaria de um quarto resultado,
"fora da cobertura". O índice vira ingestão incremental (o número CNJ normalmente já vem como
metadado).

## 6. Ambientes, GPU e horas

### Kaggle (fonte principal de GPU gratuita)

| Item | Valor |
|---|---|
| GPUs | T4 ×2 (16 GB cada) ou P100 (16 GB); ~32 GB de RAM |
| Cota de GPU | ~30 h **por semana** por conta, compartilhada entre T4 e P100; renova sábado 00h UTC (sexta 21h BRT) |
| Sessão | até 12 h; sessão interativa cai após 60 min ociosa |
| CPU | sem cota semanal, só o limite de 12 h por sessão |
| Requisito | verificação por telefone para GPU e internet |
| Arquivos | `/kaggle/input/` leitura; `/kaggle/working/` persiste (~20 GB) |
| Cuidados | T4 não suporta bfloat16 (usar float16); P100 não roda vLLM (capacidade 6.0 < 7.0) |

Google Colab gratuito: T4 sem garantia, limites dinâmicos (~15–30 h/semana relatados), sessão até
12 h, desconecta após ~90 min sem interação. Útil como reserva, não como ambiente oficial.

### Ambiente de avaliação da organização

1 GPU de 24 GB (L4/A10/4090), ~8 vCPUs, 32 GB de RAM. **O Kaggle não tem essas GPUs**: T4 e P100
são de arquitetura mais antiga. Regra de projeto (ADR-014): o pipeline de execução cabe em **uma**
T4 de 16 GB, com tipo numérico fixo em float16 — se cabe e roda lá, cabe nos 24 GB da organização.

### Estimativa de horas de GPU (ordem de grandeza, a medir)

| Atividade | Estimativa |
|---|---|
| Geração sintética com LLM (1–2 mil documentos, ~3 milhões de tokens, vLLM em lote) | 2–4 h, 1–2 vezes |
| Treino do encoder (base, alguns milhares de documentos, 3–4 épocas; referência pública: ~6–7 min/época numa T4 em NER) | 20–60 min por treino, 6–10 treinos → 3–8 h |
| Execuções completas com LLM ligado (amostra + controle) | 10–20 min cada, ~15–20 vezes → 3–6 h |
| Rodadas no conjunto final e confirmação de determinismo | < 1 h |
| **Total** | **~12–22 h de GPU** até o fechamento |

Cabe na cota de uma conta por semana (~30 h, ~4 h/dia em média); com 4 integrantes há ~120 h por
semana somadas.

## Fontes

- [Who Checks the Citations? Benchmarking Legal Hallucination Detection (CITE)](https://arxiv.org/html/2606.21155)
- [Local LLM Ensembles for Zero-shot Portuguese NER](https://arxiv.org/html/2512.10043)
- [LeNER-Br](https://teodecampos.github.io/LeNER-Br/) · [NER BERT base LeNER-Br](https://huggingface.co/pierreguillou/ner-bert-base-cased-pt-lenerbr) · [NER BERT large LeNER-Br](https://huggingface.co/pierreguillou/ner-bert-large-cased-pt-lenerbr)
- [RoBERTaLexPT](https://huggingface.co/eduagarcia/RoBERTaLexPT-base) · [Legal-BERTimbau](https://huggingface.co/rufimelo/Legal-BERTimbau-base) · [BERTimbau](https://huggingface.co/neuralmind/bert-base-portuguese-cased)
- [GLiNER](https://github.com/urchade/GLiNER) · [LangExtract](https://github.com/google/langextract) · [eyecite](https://free.law/projects/eyecite/)
- [Qwen3](https://qwenlm.github.io/blog/qwen3/) · [Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4) · [Gemma 4, Apache 2.0](https://www.ghacks.net/2026/04/06/google-releases-gemma-4-in-four-model-sizes-under-apache-2-0-license/)
- [Unsloth — fine-tuning Qwen3.5](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- [Kaggle Weekly GPU Quotas](https://www.kaggle.com/datasets/headsortails/kaggle-weekly-gpu-quotas) · [Kaggle: reset da cota de GPU](https://www.kaggle.com/general/135810) · [Resumo de limites do Kaggle](https://huggingface.co/datasets/John6666/knowledge_base_md_for_rag_1/blob/main/kaggle_20251121.md)
- [vLLM: bfloat16 e T4](https://github.com/vllm-project/vllm/issues/1157) · [vLLM: P100 sem suporte](https://github.com/vllm-project/vllm/issues/1431)
- [Colab: limites do plano gratuito](https://research.google.com/colaboratory/faq.html) · [Guia Colab 2026](https://joshthompson.co.uk/ai/google-colab-2026-guide-free-compute-automations-pro-tips/)
