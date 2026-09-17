# DEFINE — Requisitos do verificador de citações jurídicas (EARS)

**Data:** 2026-09-17
**Versão:** v1 — primeira convergência, direto de `scope.md` (sem fase Brainstorm: a demanda é
um regulamento externo já fechado, não um pedido vago a explorar)
**Fase:** SDD 2b (convergente)
**Contrato:** implementa `scope.md`. Decisões duras de arquitetura (extração, busca, stack)
ficam para `DESIGN.md` e ADRs — ainda não escritos.
**Escopo:** MVP para a fase de treino do desafio (amostra de desenvolvimento, gabarito aberto).

Cada requisito segue um dos cinco moldes EARS (Ubiquitous / Event-driven / State-driven /
Unwanted / Optional). Requisito que não caiba em nenhum molde é decisão de design disfarçada e
pertence ao `DESIGN.md`.

---

## Glossário

- **Citação** — span de texto que referencia jurisprudência ou dispositivo legal.
- **Span** — par `(inicio, fim)` de offsets em codepoints Unicode delimitando uma citação no
  texto do documento.
- **Classe** — rótulo atribuído a uma citação: `real`, `inventada` ou `incompleta`.
- **id_canonico** — identificador único do registro na base canônica que uma citação `real`
  resolve.
- **Base canônica** — banco SQLite fornecido pela organização com o conjunto de referência
  (jurisprudência e lei) contra o qual citações são verificadas.
- **Cobertura congelada** — subconjunto da base canônica efetivamente coberto pelo desafio;
  ausência de um registro não significa que ele não existe no mundo real, só que está fora da
  cobertura congelada.
- **IoU** (Intersection over Union) — sobreposição entre o span previsto e o span do gabarito;
  decide se os dois representam a mesma citação (limiar ≥ 0,5).
- **Par casado** — par (predição, gabarito) resultante do matching por IoU ≥ 0,5, 1-para-1 pelo
  maior IoU.
- **τ (tau)** — fração das citações `inventada` do gabarito que o sistema classificou como
  `real`.
- **macroF1** — média simples do F1 de cada uma das 3 classes.
- **Nível 1 / Nível 2** — subconjuntos de dificuldade do dataset (padrão vs. ruído de OCR),
  pesos 1× e 2× respectivamente.
- **Brier score** — métrica de calibração de probabilidade usada no bônus de confiança.
- **Submission** — o arquivo `submission.csv` enviado ao Kaggle.
- **Gabarito** — anotação de referência (aberta na fase de treino, oculta na fase final) usada
  para calcular a métrica.

## Extração e delimitação de spans

- **R1** (Ubiquitous): O sistema DEVE identificar todo span de texto que constitua citação de
  jurisprudência ou de dispositivo legal em cada documento de entrada.
- **R2** (Ubiquitous): O sistema DEVE representar cada span como um par `(inicio, fim)` em
  codepoints Unicode sobre o texto exatamente como distribuído.
- **R3** (Unwanted): O sistema NÃO DEVE emitir dois spans previstos disputando, por
  sobreposição, o mesmo span do gabarito — apenas o de maior IoU deve valer como predição para
  aquele par; o outro é falso positivo puro.
- **R4** (Event-driven): QUANDO um span previsto tiver IoU < 0,5 contra qualquer span do
  gabarito ENTÃO esse span DEVE ser tratado como falso positivo, não como acerto de localização
  parcial.

## Classificação em 3 classes

- **R5** (Ubiquitous): O sistema DEVE classificar cada citação extraída em exatamente uma das
  três classes: `real`, `inventada`, `incompleta`.
- **R6** (Event-driven): QUANDO uma citação não tiver identificadores suficientes para formular
  uma consulta de busca ENTÃO o sistema DEVE classificá-la como `incompleta`.
- **R7** (Event-driven): QUANDO uma citação tiver identificadores suficientes para buscar mas a
  busca retornar mais de um registro candidato plausível na base canônica ENTÃO o sistema DEVE
  classificá-la como `incompleta`.
- **R8** (Event-driven): QUANDO uma citação tiver identificadores suficientes para buscar e
  nenhum registro correspondente existir na cobertura congelada ENTÃO o sistema DEVE
  classificá-la como `inventada`.
- **R9** (Event-driven): QUANDO uma citação resolver a exatamente um único registro da base
  canônica ENTÃO o sistema DEVE classificá-la como `real`.
- **R10** (Unwanted): O sistema NÃO DEVE classificar como `real` uma citação cuja resolução não
  seja única, mesmo que um dos candidatos pareça mais provável que os demais.

## Resolução de entidade contra a base canônica

- **R11** (Ubiquitous): SE a classe atribuída a uma citação for `real` ENTÃO o sistema DEVE
  entregar um `id_canonico` não vazio.
- **R12** (Ubiquitous): O `id_canonico` entregue DEVE corresponder exatamente ao registro
  esperado no gabarito para aquela citação.
- **R13** (Unwanted): O sistema NÃO DEVE entregar `id_canonico` para citações classificadas como
  `inventada` ou `incompleta`.
- **R14** (Unwanted): O sistema NÃO DEVE tratar uma citação como `real` apenas por encontrar um
  registro "parecido" na base canônica, sem identificadores explícitos suficientes na citação
  original para justificar essa resolução.

## Formato de saída

- **R15** (Ubiquitous): O sistema DEVE emitir um JSON por documento no formato do contrato
  "schema 1.2" (campos exatos a confirmar em 25/08/2026 — ver `scope.md`, seção "Em aberto").
- **R16** (Ubiquitous): O sistema DEVE gerar o `submission.csv` usando o script
  `json_to_submission.py` fornecido pela organização, sem reimplementar a conversão
  manualmente.
- **R17** (Ubiquitous): O sistema DEVE incluir, na submissão final, todo `documento_id` do
  conjunto de entrada, mesmo quando não houver nenhuma citação detectada nesse documento.
- **R18** (Event-driven): QUANDO um documento não tiver nenhuma citação detectada ENTÃO a célula
  correspondente no `submission.csv` DEVE conter `-`, nunca ficar vazia.
- **R19** (Ubiquitous): Campos ausentes de uma citação (`id_canonico` quando não aplicável,
  `confianca` quando não emitida) DEVEM ser representados como `-` no `submission.csv`.
- **R20** (Unwanted): O sistema NÃO DEVE calcular offsets em bytes UTF-8 nem sobre uma versão
  normalizada/reescrita do texto — apenas sobre o `.txt` exatamente como distribuído.

## Ferramentas e modelos permitidos

- **R21** (Ubiquitous): O sistema DEVE usar exclusivamente modelos e ferramentas de pesos e
  código abertos na execução final que produz a submissão.
- **R22** (Unwanted): O sistema NÃO DEVE depender de chave de API paga para rodar de ponta a
  ponta na versão final avaliada pela organização.
- **R23** (Optional): O sistema PODE servir um modelo de pesos abertos via API paga durante o
  desenvolvimento, desde que a mesma versão do modelo seja executável offline pela organização.
- **R24** (Optional): O sistema PODE usar qualquer dataset público adicional, restrito ao
  treino/ajuste — nunca como substituto da cobertura congelada na inferência.

## Calibração de confiança (opcional)

- **R25** (Optional): O sistema PODE emitir um campo `confianca` (0 a 1) por citação prevista.
- **R26** (Event-driven): SE o campo `confianca` for emitido ENTÃO ele DEVE refletir a
  probabilidade estimada de a classificação estar correta, para não prejudicar o bônus de
  Brier.
- **R27** (Unwanted): O sistema NÃO DEVE emitir `confianca` fixa/constante para todas as
  citações quando isso não refletir incerteza real — o bônus de calibração pune confiança mal
  calibrada tanto quanto a ausência dela deixa de bonificar.

## Validação local antes de submeter

- **R28** (Ubiquitous): O sistema DEVE ser validado localmente com `kaggle_metric.py` contra o
  gabarito da amostra de desenvolvimento antes de qualquer submissão ao leaderboard.
- **R29** (Event-driven): QUANDO o score local calculado por `kaggle_metric.py` divergir do
  score do leaderboard para a mesma submissão ENTÃO essa divergência DEVE ser investigada antes
  de novas submissões (indica erro de pipeline, não de modelo).

## Reprodutibilidade

- **R30** (Ubiquitous): O pipeline completo (da leitura dos `.txt` até a geração do
  `submission.csv`) DEVE ser executável de ponta a ponta via script, não como sequência manual
  de células de notebook.
- **R31** (Ubiquitous): O repositório de código DEVE ser publicável e o commit que gerou uma
  submissão enviada DEVE ser identificável, para a verificação de reprodutibilidade exigida dos
  finalistas.
- **R32** (Unwanted): O pipeline NÃO DEVE ter passos de execução que exijam intervenção manual
  não documentada (ex.: edição manual de arquivo intermediário) entre a entrada e a submissão
  final.

## DEVE / NÃO DEVE (síntese)

**DEVE:**
- Identificar e delimitar todo span de citação jurídica em cada documento (R1, R2).
- Classificar cada citação em `real`/`inventada`/`incompleta` pelos critérios de suficiência de
  identificadores e unicidade de resolução (R5–R9).
- Entregar `id_canonico` correto para toda citação `real` (R11, R12).
- Seguir o contrato de formato — schema 1.2, `submission.csv`, offsets em codepoints (R15–R20).
- Rodar de ponta a ponta só com ferramentas abertas (R21).
- Validar localmente antes de cada submissão (R28).
- Ser reproduzível por terceiros a partir de um commit (R30, R31).

**NÃO DEVE:**
- Classificar como `real` uma citação cuja resolução na base canônica não seja única (R10, R14).
- Entregar `id_canonico` fora da classe `real` (R13).
- Depender de API paga na execução final (R22).
- Emitir confiança não calibrada por conveniência (R27).
- Ter passos manuais não documentados no pipeline (R32).

## Critério de sucesso do MVP

A definir pelo usuário como meta interna (ex.: `score_final` mínimo aceitável na fase de treino
antes de considerar o pipeline pronto para a fase final). É decisão de gestão do projeto, não
regra da organização — o regulamento não define nota mínima para premiação.

## Autocrítica dos critérios (v1)

- R7 e R9 dependem de como a base canônica está indexada e de como "resolução única" é definida
  na prática (ex.: dois acórdãos do mesmo processo em datas diferentes contam como um ou dois
  candidatos?). Só pode ser resolvido quando o schema da base SQLite for conhecido
  (25/08/2026) — tratar como requisito provisório até lá.
- R26/R27 (calibração) são requisitos de qualidade, não binários — "bem calibrado" não tem um
  limiar testável definido aqui; a própria métrica oficial (Brier) já serve como esse teste, de
  modo que estes R# são mais orientação de design do que critério de aceite verificável
  isoladamente.
- Nenhum requisito aqui define a arquitetura de extração (regex vs. NER treinado vs. LLM) nem a
  estratégia de busca contra a base canônica (SQL direto, embeddings, fuzzy matching) —
  propositalmente: isso é decisão de `DESIGN.md`, ainda não escrito.
- R3 (descarte de spans redundantes por menor IoU) descreve o comportamento do matching da
  métrica oficial, não uma escolha do sistema — mantido aqui como lembrete de que emitir spans
  sobrepostos é estritamente pior que não emitir nenhum.
