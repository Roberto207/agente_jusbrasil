# Scope — Verificação de citações jurídicas em pareceres de IA (Jusbrasil × BRACIS 2026)

**Origem:** regulamento oficial do desafio (Kaggle, competição privada, Jusbrasil × BRACIS 2026)
**Data:** 2026-09-17
**Natureza:** demanda externa fechada — este documento reproduz fielmente o que a organização
pede, sem decisão de arquitetura ou de implementação. Decisões técnicas ficam para `DESIGN.md`
e ADRs (ainda não escritos). Requisitos internos de engenharia ficam para `DEFINE.md`.

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

1. **JSON por documento** (contrato "schema 1.2", detalhado na aba Data do Kaggle — campos
   exatos a confirmar quando os dados chegarem). É o output real do sistema: para cada
   documento, a lista de citações encontradas, cada uma com span (`inicio`/`fim`), `classe`,
   `id_canonico` (quando aplicável) e `confianca` (opcional).
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

## Restrições impostas pela organização

- Somente **modelos e ferramentas de pesos e código abertos** — sem chaves de API nem serviços
  pagos na execução final. Servir um modelo de pesos abertos via API paga durante o
  desenvolvimento é permitido, desde que o mesmo modelo e revisão sejam executáveis offline pela
  organização.
- Qualquer dataset público pode ser usado **no treino**.
- Elegibilidade: apenas estudantes do Brasil; participação individual ou em equipes de até 4
  pessoas (mesclagem de equipes pelo próprio Kaggle); elegibilidade verificada pela organização.
- **Reprodutibilidade obrigatória para o topo do ranking**: as soluções finalistas passam por
  verificação de reprodutibilidade ao final — repositório de código e o commit exato que
  produziu as saídas submetidas serão coletados.
- Teto diário de submissões por equipe (valor configurado na competição, não especificado no
  regulamento textual).

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
  — fica para `DESIGN.md` (ainda não escrito).
- Requisitos internos de engenharia (DEVE/NÃO DEVE do próprio sistema) — fica para `DEFINE.md`.
- Exploração de hipóteses e abordagens técnicas concorrentes — ficaria para `BRAINSTORM.md`,
  deliberadamente deferido: a demanda aqui é uma regra externa já fechada, não um pedido vago
  que precise de pesquisa para corrigir a premissa.

## Em aberto até os dados chegarem (25/08/2026)

- Nomes exatos dos campos do schema 1.2 do JSON por documento.
- Possíveis metadados extras por documento além de `citacoes`.
- Convenção de nomes de `id_canonico` na base canônica SQLite.
- Valor exato do teto diário de submissões por equipe.
