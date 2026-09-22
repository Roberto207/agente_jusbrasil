# Scope — Verificação de citações jurídicas em pareceres de IA (Jusbrasil × BRACIS 2026)

**Origem:** regulamento oficial do desafio (Kaggle, competição privada, Jusbrasil × BRACIS 2026)
**Data:** 2026-09-17
**Revisão:** 2026-09-17 — contrato do JSON e regras da métrica preenchidos a partir do material
distribuído (`json_to_submission.py`, `kaggle_metric.py`, `sample_submission.csv`); regras
completas da aba Rules (ambiente de avaliação, pesos públicos, pacote reproduzível, Foundational
Rules) e esclarecimentos da equipe incorporados.
**Revisão:** 2026-09-22 — texto oficial das abas Overview/Data/Rules capturado na íntegra em
`regulamento_oficial_kaggle.md` (inclui as Foundational Rules completas, que aqui só aparecem
resumidas). Essa captura trouxe números diferentes dos usados neste documento (1.016 registros
na base vs. 1.014 locais; 225 citações no gabarito vs. 192 locais); re-baixados os dados no mesmo
dia e confirmado que os arquivos não mudaram — divergência era só na descrição da página, sem
efeito na fase de treino. Risco a vigiar na fase de avaliação final (ver "Ainda em aberto").
**Natureza:** demanda externa fechada — este documento reproduz fielmente o que a organização
pede (regulamento + material distribuído), sem decisão de arquitetura ou de implementação.
Decisões técnicas ficam em `DESIGN.md` e `docs/decisions/`. Requisitos internos de engenharia
ficam em `DEFINE.md`.

---

## Contexto

LLMs generativos já são usados para redigir pareceres, petições e memorandos jurídicos. Um dos
riscos mais documentados desses sistemas é a alucinação de fontes: o modelo cita jurisprudência
ou dispositivos legais que não existem, ou apresenta citações tão vagas que não podem ser
verificadas. Tribunais no Brasil e no exterior já sancionaram advogados por protocolar peças com
citações inventadas geradas por IA.

O desafio pede a construção do verificador automático que falta nesse fluxo de trabalho: um
sistema que lê um documento judicial, identifica todas as citações de jurisprudência e de lei, e
decide, para cada uma, se ela é real, inventada ou incompleta.

## A tarefa pedida

Entrada: documentos judiciais em texto (`.txt`).

Para cada documento, identificar todas as citações e classificar cada uma em uma de três
classes:

- **real** — a citação resolve a um único registro da base canônica do desafio: tem
  identificadores suficientes e a busca confirma sua existência. Exige entregar o
  `id_canonico` correto — acertar o rótulo sem o link não conta.
- **inventada** — identificadores suficientes para buscar, mas nenhum registro correspondente
  existe na cobertura congelada.
- **incompleta** — informação insuficiente para formular a consulta (ex.: "conforme
  jurisprudência pacífica do tribunal"), ou suficiente para buscar mas insuficiente para
  identificar um único registro.

A distinção entre `inventada` e `incompleta` importa em produção: a primeira é alucinação ativa
(o LLM inventou um número de acórdão); a segunda é evasiva. Sistemas reais tratam cada caso de
forma diferente — incompletas vão para revisão humana; inventadas devem ser bloqueadas.

O conjunto tem dois níveis de dificuldade:
- **Nível 1** — formato padrão, peso 1×.
- **Nível 2** — ruído de OCR e variação de superfície, peso 2×.

## Formato de entrega exigido

1. **JSON por documento** (contrato "schema 1.2"). É o output real do sistema. Campos lidos
   pelo `json_to_submission.py`:
   ```json
   {
     "documento_id": "gen_n1_001",
     "citacoes": [
       {
         "inicio": 1284, "fim": 1302,
         "trecho": "...", "tipo": "jurisprudencia",
         "classificacao": "real",
         "resolucao": {"id_canonico": "2106313729"},
         "confianca": 0.91
       }
     ]
   }
   ```
   - `trecho` e `tipo` (`jurisprudencia` ou `lei`) são obrigatórios no JSON, mas não entram no
     CSV — a métrica pontua span, classe, link e confiança.
   - `id_canonico` é o doc_id numérico do Jusbrasil (só dígitos) — na base distribuída, a
     coluna `id` da tabela `documentos`.
2. **Conversão para `submission.csv`** via `json_to_submission.py` (script fornecido pela
   organização) — não deve ser reimplementado manualmente. Uma linha por `documento_id`:
   ```
   documento_id,citacoes
   gen_n1_001,"469,498,incompleta,-,0.9|589,652,incompleta,-,0.8"
   gen_n1_002,-
   ```
   - Cada citação: `inicio,fim,classe,id_canonico,confianca`, separadas por `|`.
   - Campos ausentes viram `-`.
   - Documento sem citações leva `-` na célula — nunca vazia.
   - Todo `documento_id` do conjunto precisa estar presente na submissão.
3. **Offsets em codepoints Unicode**, contados sobre o `.txt` exatamente como distribuído (não
   bytes UTF-8, não texto normalizado).
4. **`kaggle_metric.py`** (fornecido) reproduz localmente, nível a nível, o mesmo score do
   leaderboard — inclusive o matching — antes de qualquer submissão.

### Material distribuído

| Arquivo | Conteúdo |
|---|---|
| `txt/` | 26 documentos da amostra de desenvolvimento (13 de Nível 1, 13 de Nível 2) |
| `desafio1_bracis.db` | base canônica SQLite: tabela `documentos` (1.014 registros — acórdãos de STF, STJ, STM, TSE e TST, súmulas e dispositivos de lei) + índice full-text FTS5 |
| `goldenset_offsets.csv` | gabarito da amostra: `nivel, documento_id, citacao_id, inicio, fim, trecho, tipo, classificacao, id_canonico` (192 citações) |
| `json_to_submission.py` | conversor JSON → `submission.csv` |
| `kaggle_metric.py` | métrica oficial |
| `sample_submission.csv` | exemplo de submissão vazia (`-` em todas as células) |

## Regras da competição (aba Rules)

A participação implica aceitar as regras abaixo e as **Foundational Competition Rules** do
Kaggle, que prevalecem em caso de conflito.

### Regras do desafio

- **Equipes e elegibilidade**: individual ou equipes de até 4 pessoas, apenas estudantes, do
  Brasil. Elegibilidade verificada pela organização (nas finalistas, antes do resultado).
  Inscrição no BRACIS não é pré-requisito; vencedores comparecem (ou enviam representante) à
  sessão de encerramento.
- **Ferramentas — somente abertas**: apenas modelos, bibliotecas e ferramentas de pesos e código
  abertos, executáveis pela organização sem chaves de API ou serviços pagos.
  - **Pesos em repositório público** (ex.: Hugging Face), referenciados por **link + revisão
    fixa**.
  - **Fine-tuning é permitido**, desde que os pesos resultantes sejam **publicados e
    referenciados**.
  - Qualquer **dataset público** pode ser usado no treino.
- **Ambiente de avaliação (envelope de execução)**: a solução completa deve rodar em **1 GPU de
  24 GB de VRAM** (ex.: NVIDIA L4 / A10 / RTX 4090), **~8 vCPUs** e **32 GB de RAM**. Pipeline que
  não caiba nesse envelope é considerado não reproduzível e **desclassificado**.
- **Submissões**: múltiplas durante todo o período, com teto diário por equipe. Fases do
  leaderboard descritas abaixo.
- **Pacote reproduzível (bundle)**: as finalistas entregam repositório com código, README,
  referência dos modelos (link + revisão), ambiente (`requirements`/`Dockerfile`) e o **comando
  exato que reproduz as saídas submetidas**, com **decodificação determinística** (ex.:
  `temperature=0`, seed fixa) sempre que aplicável. Solução não reproduzível não entra no
  ranking.
- **Ranking e recurso**: ranking final só sobre a parte privada do conjunto final, com
  verificação de reprodutibilidade após o encerramento e janela de recurso após a divulgação
  preliminar.
- **Desclassificação**: tentar extrair, inferir ou obter o conjunto de teste privado; plágio sem
  crédito; violar a regra de ferramentas abertas.
- **Publicação**: as melhores soluções são apresentadas no BRACIS 2026; o desafio vira benchmark
  público após a conferência.

### Pontos das Foundational Rules do Kaggle que afetam o projeto

| Seção | Regra | Efeito prático |
|---|---|---|
| 4b | Submissões não podem usar rotulagem manual ou predição humana dos dados de validação/teste | Documentos do conjunto final não são lidos para ajustar regras |
| 5a | Uma única conta Kaggle por pessoa | Cada integrante usa só a própria conta |
| 5d, 6a | Proibido compartilhar código ou dados em particular fora da equipe | Repositório privado, acesso só da equipe |
| 6b | Compartilhamento público de código da competição só no fórum/notebooks do Kaggle, sob licença OSI | Não publicar o código fora do Kaggle durante a competição |
| 6c | Código aberto usado precisa de licença aprovada pela OSI, sem restringir uso comercial | Conferir licença de cada biblioteca e modelo (ex.: evitar licenças próprias como Gemma 3 e Llama) |

### Esclarecimentos definidos pela equipe

- **Dados sintéticos** gerados pela equipe são permitidos no treino, **desde que publicados**
  (entram como dataset público).
- **Pesos de fine-tuning** e **dados sintéticos** são publicados **dentro do prazo** da
  competição, com revisão fixa.
- **Referências vagas** ("jurisprudência pacífica"): em análise pela equipe (ver divergência
  abaixo).

## Métrica oficial

O alinhamento entre citações previstas e gabarito é por **sobreposição de spans com IoU ≥ 0,5**
(matching 1-para-1 pelo maior IoU). Citação do gabarito sem par vira erro de recall; predição
sem par vira falso positivo.

Sobre os pares casados, a nota de cada nível é montada em três passos:

1. **Macro-F1 das 3 classes** — F1 por classe (real, inventada, incompleta), média simples entre
   elas. Para a classe `real`, só conta acerto se o `id_canonico` entregue for o esperado no
   gabarito.
2. **Penalidade do erro grave** — `τ` = fração das citações `inventada` do gabarito preditas
   como `real`; `s = macroF1 · (1 − 0,5 · τ)`. Se todas as alucinações "vazarem" como real, a
   nota cai pela metade.
3. **Bônus de calibração (até 10%)** — campo `confianca` opcional; se enviado, mede-se o Brier
   score sobre os pares casados: `score = s · (1 + 0,10 · (1 − brier))`. Quem não envia
   confiança não ganha nem perde.

Combinação dos níveis: `score_final = (1 · score_Nível1 + 2 · score_Nível2) / 3`.

Uma submissão perfeita com `confianca = 1.0` pontua 1,1000.

### Detalhes que só aparecem no `kaggle_metric.py`

- **Duplicata rejeita a submissão**: duas citações do mesmo documento com IoU ≥ 0,5 entre si
  levantam erro — a submissão inteira é recusada.
- **Classe errada custa duas vezes**: FN na classe do gabarito e FP na classe predita. Link
  errado num par `real`×`real` custa só um FP.
- **Regra EXTRA**: predição sem par que esteja ≥ 90% contida numa citação do gabarito já casada
  é ignorada (tolera granularidade a mais, ex.: `art. 1.021` e `§4º` separados).
- **Classe sem ocorrência** no gabarito de um nível fica fora da média do macro-F1.
- **Gabarito aceita vários ids**: a solução guarda, para cada real, um conjunto de doc_ids
  aceitos; basta acertar um.
- `confianca` fora de [0, 1], `id_canonico` não numérico em real, ou span com `fim <= inicio`
  também rejeitam a submissão.

> O detalhamento didático de por que o IoU e os pesos funcionam assim (com exemplo numérico)
> está em `explicação_jus_brasil.md`, já escrito neste projeto — este documento só declara a
> regra oficial, não a ensina.

## Cronograma oficial

| Marco | Data |
|---|---|
| Abertura das inscrições | 18/08/2026 |
| Envio dos dados por e-mail aos inscritos | 25/08/2026 |
| Webinar de tira-dúvidas com a organização | 28/08/2026 |
| Período de submissões com leaderboard ao vivo | 01/09 a 30/09/2026 |
| Fechamento das submissões | 30/09/2026, 23h59 (BRT) |
| Apresentação das melhores soluções no BRACIS 2026 (Cuiabá-MT) | 19 a 22/10/2026 |

Todas as datas em horário de Brasília (BRT).

## Fases do leaderboard

- **Fase de treino (agora)**: material distribuído é a amostra de desenvolvimento, com gabarito
  aberto. Leaderboard roda sobre ela e é referencial — serve para validar o pipeline de ponta a
  ponta, não define o resultado.
- **Fase de avaliação final**: conjunto final, cego, em construção pela organização. Quando
  ativado, o leaderboard reinicia: passa a usar 40% dele (parte pública), e o ranking final é
  calculado sobre os 60% restantes, mantidos em sigilo até o encerramento. Submissões da fase de
  treino não contam para o ranking final.

## Premiação e reconhecimento

- As 5 melhores soluções apresentam na sessão de encerramento do BRACIS 2026, em Cuiabá-MT
  (presencial ou representante).
- Não é necessário estar inscrito no BRACIS para participar — só as equipes vencedoras precisam
  comparecer.
- O desafio libera um benchmark público de NLP jurídico em português após a conferência; as
  soluções vencedoras entram como referência.

## Fora do escopo deste documento

- Qualquer decisão de arquitetura, stack, modelo ou estratégia de extração/classificação/linking
  — fica em `DESIGN.md` e `docs/decisions/`.
- Requisitos internos de engenharia (DEVE/NÃO DEVE do próprio sistema) — ficam em `DEFINE.md`.
- Exploração de hipóteses e abordagens técnicas concorrentes — ficaria para `BRAINSTORM.md`,
  deliberadamente deferido: a demanda aqui é uma regra externa já fechada, não um pedido vago
  que precise de pesquisa para corrigir a premissa.

## Divergência entre o regulamento e o material distribuído

O regulamento dá "conforme jurisprudência pacífica do tribunal" como exemplo de `incompleta`.
No gabarito da amostra, referências vagas desse tipo ("a jurisprudência pacífica desta Corte",
"o entendimento sumulado sobre a matéria", "o artigo correspondente do Código de Processo
Civil") **aparecem nos textos mas não são anotadas**. Toda `incompleta` anotada traz tribunal
ou classe processual, ano e relator, sem número. Como o sistema é pontuado contra o gabarito,
`DEFINE.md` segue o gabarito — ver ADR-005. A decisão está em análise pela equipe.

## Ainda em aberto

- Valor exato do teto diário de submissões por equipe.
- Data de ativação do conjunto final cego, e se ele usa a mesma base canônica.
- Se o conjunto final anota referências vagas como `incompleta` (em análise pela equipe).
- **Divergência de números — checada e resolvida em 22/09/2026** (ver `regulamento_oficial_kaggle.md`):
  o texto da aba Data no Kaggle fala em 1.016 registros na base canônica e 225 citações no
  gabarito (116 no Nível 1, 109 no Nível 2); os arquivos deste projeto têm 1.014 registros e 192
  citações. Re-baixados os dados da aba Data no mesmo dia: nada mudou, era só a descrição da
  página desatualizada/arredondada. **Sem efeito na fase de treino.** Repetir essa checagem
  (contagem de registros recebidos vs. o que a organização anunciar) quando o conjunto final cego
  da fase de avaliação final for ativado — lá não há gabarito local pra comparar, então uma
  contagem errada passaria despercebida sem essa verificação manual.
