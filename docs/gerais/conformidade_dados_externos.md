# Conformidade de dados externos — sintético não publicado, LeNER-Br, LLM diversificadora

**Data:** 2026-09-22 · **Item:** `tarefas_equipe.md`, seção 3.2, Tier 2/backlog de publicação
**Por que este documento existe:** dois achados de conformidade vieram à tona durante a auditoria
da circularidade do gabarito sintético (commit `734fb6e`) e a pesquisa do item Tier 2 (LeNER-Br +
LLM diversificadora). Nenhum dos dois é urgente por si só, mas os dois têm prazo fixo (30/09) e
consequência dura (desclassificação, não perda de nota) — merecem registro com peso, não só uma
linha de checklist.

## Achado 1 — o sintético que já usamos não está publicado

A regra do desafio (`specs/scope.md`, "Esclarecimentos definidos pela equipe"):

> **Dados sintéticos** gerados pela equipe são permitidos no treino, **desde que publicados**
> (entram como dataset público). Pesos de fine-tuning e dados sintéticos são publicados **dentro
> do prazo** da competição, com revisão fixa.

`tarefas_equipe.md:569` registra isso como tarefa e continua `- [ ]`:

> Publicar o dataset sintético no Hugging Face, revisão fixa, licença aberta (R46) — antes de
> 30/09 23h59 BRT. Criar a conta HF do projeto se ainda não existir.

**O que isso significa na prática, hoje:** usar o sintético *internamente* (medir score, calibrar
`taxa_acerto.json`, rodar os testes R35) é sempre permitido — é dado nosso, gerado localmente, sem
restrição para uso próprio. O que ainda não está resolvido é a condição que torna esse mesmo
sintético **elegível como "dataset público" para efeito da regra do desafio**: publicação real, com
revisão (commit/tag) fixa, antes do prazo.

**Estado da infraestrutura, checado nesta sessão:** zero. Não existe conta Hugging Face do projeto,
não existe token configurado em lugar nenhum (nem `.env`, nem `verificador.toml`, nem secret do
Kaggle — o único secret usado hoje nos notebooks é `GITHUB_TOKEN`, para clonar o repositório
privado), não existe a dependência `huggingface_hub` em `requirements.txt`, não existe nenhum
script de upload. A frase "criar a conta HF do projeto se ainda não existir" em `tarefas_equipe.md`
não é retórica — literalmente ninguém do time fez isso até agora.

**Consequência prática:** este é um bloqueador de prazo, não de nota. Regras 6c/R45/R46
(`specs/DEFINE.md:195-197`) tratam isso como requisito de reprodutibilidade — pipeline ou dado não
publicado corretamente é motivo de desclassificação do pacote reprodutível, não de perda de pontos
no score. Precisa entrar na Fase 4/6 com folga, não no último dia (o próprio `tarefas_equipe.md:653`
já registra esse risco na tabela de riscos).

## Achado 2 — LeNER-Br: licença ambígua, mas uso planejado é de baixo risco

**O dataset:** [LeNER-Br](https://github.com/peluz/lener-br) (Luz de Araujo et al., PROPOR 2018,
Universidade de Brasília) — corpus público de NER jurídico em português, 70 documentos, ~318 mil
tokens, com a entidade `JURISPRUDENCIA` que precisamos. Também espelhado no
[Hugging Face Datasets](https://huggingface.co/datasets/peluz/lener_br).

**A ambiguidade, checada nesta sessão:**
- O repositório GitHub tem um arquivo `LICENSE` na raiz dizendo **MIT** (copyright 2022, Pedro
  Henrique Luz de Araujo) — confirmado lendo `raw.githubusercontent.com/peluz/lener-br/master/LICENSE`.
- O card do dataset no Hugging Face marca o campo estruturado `license:` como **"unknown"**.
- Nenhuma das duas fontes declara explicitamente que o MIT cobre o **corpus de texto** (e não só o
  código do modelo LSTM-CRF que acompanha o mesmo repositório) — é a convenção usual (LICENSE na
  raiz cobre o repo inteiro), mas não é uma afirmação textual dos autores.

**Por que isso não bloqueia o uso planejado, mesmo sem resolver a ambiguidade:** a regra do desafio
trata "ferramentas" (modelos, bibliotecas, pesos — que *precisam* de licença aprovada pela OSI,
com a proibição explícita de Llama/Gemma como exemplo) separadamente de "dataset", onde a barra
declarada é só:

> Qualquer **dataset público** pode ser usado no treino.

LeNER-Br é inequivocamente público — repositório aberto, sem paywall, sem cadastro, publicado
academicamente numa conferência revisada por pares. O uso planejado (Tier 2 de `tarefas_equipe.md`)
é uma **sonda de medição interna**: rodar `preparar()`+`extrair()` do nosso próprio pacote por cima
do texto deles e contar quantas entidades `JURISPRUDENCIA` nosso regex captura. Isso não
redistribui o corpus, não incorpora os dados no que publicamos, não treina peso nenhum sobre ele —
é diagnóstico local, descartável, que não sai do nosso ambiente de desenvolvimento.

**Registro explícito da fronteira de risco:** se esse uso um dia mudar de escopo — por exemplo,
publicar algo derivado do LeNER-Br (um dataset combinado, resultados agregados detalhados o
suficiente para reconstruir o corpus, ou treinar e publicar pesos usando-o) — aí sim vale confirmar
a licença por escrito com os autores (contato do paper: `pedrohluzaraujo@gmail.com`) antes de
prosseguir. Enquanto for só sonda de recall interna, o risco é baixo e a regra "dataset público" já
cobre o uso.

**Fronteira cruzada em 2026-09-24 (decisão do Roberto):** o LeNER-Br `train` entra no treino do
encoder, e os pesos serão publicados se o go/no-go passar. *(25/09: passou; a equipe decidiu GO e
os pesos estão públicos em `Roberto2799/jusbrasil-encoder-citacoes` @ `d91d0914…`, com card que cita o
LeNER-Br e aponta link + commit.)* Fundamento: a regra do desafio permite
"qualquer dataset público" no treino, e o `LICENSE` na raiz do repositório declara MIT. O corpus não é
redistribuído (os pesos não o contêm, e o card só aponta link + commit `4999cb7…`). **Pendente:**
e-mail aos autores pedindo confirmação de que o MIT cobre o corpus. Se houver objeção, retreinar
sem o LeNER-Br custa minutos (`verificador.treino.dataset` sem essa fonte).

**Amostra do desafio no treino (mesma data):** os 14 documentos de `ajuste` entram no treino. A
licença da aba Data é "Subject to Competition Rules": treinar com eles é o uso previsto ("para as
equipes construírem suas soluções"), mas **não se republica** o texto. O `dataset.jsonl` fica em
`runs/` (fora do git e do HF), e o card dos pesos só cita a fonte. A regra 4b (rotulagem manual de
dados de validação/teste) não se aplica: o gabarito é da organização e a amostra não é o conjunto
final. **O conjunto final nunca entra em treino**, nem por pseudo-rótulo.

## Achado 3 — restrição de licença já conhecida, relevante para a LLM diversificadora

`specs/scope.md:151` proíbe explicitamente **Llama e Gemma** ("licenças próprias, não aprovadas
pela OSI, ex.: evitar licenças como Gemma 3 e Llama"). Isso descarta a maioria dos LLMs abertos
populares em português, porque quase todo fine-tune de PT-BR usa uma dessas duas arquiteturas como
base (herdando a licença restrita).

Opções com licença **Apache 2.0 genuína** confirmadas nesta sessão (via API do Hugging Face, tag
`license:` + contagem real de parâmetros nos pesos):

| Modelo | Parâmetros | VRAM (fp16) | Nota |
|---|---|---|---|
| [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | 7,6B | ~15 GB | **escolhido** para o notebook da diversificadora |
| [Mistral-7B-Instruct-v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | 7,3B | ~14,5 GB | alternativa |
| [EuroLLM-9B-Instruct](https://huggingface.co/utter-project/EuroLLM-9B-Instruct) | 9,2B | ~18 GB | foco em línguas europeias, incl. PT |
| [Tucano-2b4-Instruct](https://huggingface.co/TucanoBR/Tucano-2b4-Instruct) | 2,4B | ~5 GB | único nativo em PT; card pede cautela de uso (recomendação ética, não restrição de licença) |

Todos cabem no envelope de avaliação do desafio (1 GPU 24GB VRAM). Modelos descartados por não
atenderem aos critérios: Sabiá (só API paga), Gervásio-PT/Bode/derivados de Llama 2 (herdam Llama
License), BLOOM/BLOOMZ (licença BigScience OpenRAIL-M, não aprovada pela OSI).

## Achado 4 — licenças dos encoders candidatos (2026-09-24)

Conferidas pela tag `license:` da API do Hugging Face, contra a regra 6c (`specs/scope.md:151`:
licença aprovada pela OSI, sem restringir uso comercial). Contexto da decisão: `tarefas_equipe.md`,
Fase 4, "Decisão de 2026-09-24".

| Modelo | Licença | Situação |
|---|---|---|
| [neuralmind/bert-base-portuguese-cased](https://huggingface.co/neuralmind/bert-base-portuguese-cased) e `-large` | MIT | **Pode** — **escolhido** (base) |
| [rufimelo/Legal-BERTimbau-base](https://huggingface.co/rufimelo/Legal-BERTimbau-base) e `-large` | MIT | **Pode** — comparação (base) |
| [unb-labia/BERTomelo-ModernBERT-Base-v1](https://huggingface.co/unb-labia/BERTomelo-ModernBERT-Base-v1) e `-Large-v1` | Apache 2.0 | **Pode** — reserva |
| [urchade/gliner_multi-v2.1](https://huggingface.co/urchade/gliner_multi-v2.1) | Apache 2.0 | **Pode** — reserva, zero-shot |
| [PORTULAN/albertina-100m-portuguese-ptbr-encoder](https://huggingface.co/PORTULAN/albertina-100m-portuguese-ptbr-encoder) | MIT | **Pode** — não priorizado |
| [PORTULAN/albertina-900m-portuguese-ptbr-encoder](https://huggingface.co/PORTULAN/albertina-900m-portuguese-ptbr-encoder) | "other" | **Fora** — tag de licença não OSI |
| [eduagarcia/RoBERTaCrawlPT-base](https://huggingface.co/eduagarcia/RoBERTaCrawlPT-base) | CC BY 4.0 | **Fora** — idem RoBERTaLexPT |
| [eduagarcia/RoBERTaLexPT-base](https://huggingface.co/eduagarcia/RoBERTaLexPT-base) | CC BY 4.0 | **Fora** — Creative Commons não é licença aprovada pela OSI |
| [dominguesm/legal-bert-ner-base-cased-ptbr](https://huggingface.co/dominguesm/legal-bert-ner-base-cased-ptbr) | CC BY 4.0 | **Fora** — idem |
| [pierreguillou/ner-bert-base-cased-pt-lenerbr](https://huggingface.co/pierreguillou/ner-bert-base-cased-pt-lenerbr) (e `-large`) | não declarada | **Fora** — sem permissão de redistribuir |

O RoBERTaLexPT constava como candidato no ADR-011 e em `ia_no_pipeline.md`; sai pela licença, não por
desempenho. Pesos ajustados pela equipe a partir de um modelo MIT/Apache herdam a obrigação de manter
o aviso de licença do modelo-base no card do Hugging Face.

*Atualizado em 2026-09-24:* a ordem de preferência mudou depois de comparar tokenizadores e corpus de
pré-treino (o Legal-BERTimbau é jurídico de Portugal; o BERTomelo converte tudo para minúsculas).
Escolha e motivos em `tarefas_equipe.md`, Fase 4, "Modelos preferidos".

## Resumo — o que fica pendente

- [x] Publicar o sintético **atual** (camada 1, código) no Hugging Face — infraestrutura zero, é
  trabalho a criar do zero (conta, token, script de upload).
- [x] Rodar o notebook da LLM diversificadora no Kaggle (precisa de GPU; preparado, não executável
  neste ambiente) e publicar o resultado também.
  *2026-09-24* — as duas camadas estão em
  [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado)
  (público, MIT), com a camada 1 em `base/` e a camada 2 na raiz. Revisão fixa
  `0209a853e6e59b263b138200963b579105baca24`. Conferido por hash: os 409 arquivos são idênticos aos
  gerados no Kaggle, e a camada 1 é byte a byte igual ao `sintetico/` local.
- [ ] **Confirmar a licença do LeNER-Br com os autores** (`pedrohluzaraujo@gmail.com`). O uso já saiu
  do escopo "sonda interna": o LeNER-Br `train` treinou o encoder, e os pesos foram publicados em 25/09
  (decisão GO). Fundamento enquanto a resposta não vem: "qualquer dataset público" + `LICENSE` MIT na
  raiz do repositório. Se houver objeção, retreinar sem o LeNER-Br e publicar nova revisão.
- [x] Publicar os pesos do encoder (MIT, herda o aviso do BERTimbau): público em 25/09, revisão
  `d91d09142fdc2601cad04b8df1d509d87c5a1552`, card em `docs/modelos/card-jusbrasil-encoder-citacoes.md`.

Nada disso bloqueia o desenvolvimento/medição local continuarem — bloqueia é a validade da
submissão final, com prazo 30/09 23h59 BRT.
