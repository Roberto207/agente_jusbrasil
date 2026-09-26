# DEFINE — Requisitos do verificador de citações jurídicas (EARS)

**Data:** 2026-09-17
**Versão:** v2.2 — v2 emendada a partir do material distribuído (base canônica, gabarito da
amostra, `kaggle_metric.py`, `json_to_submission.py`); v2.1 incorpora a crítica EARS
(subagente `sdd-ears-critico`): rótulos de molde corrigidos, contradição R1×R33 e conflito
R7×R40 resolvidos, critérios de processo e de design disfarçado retirados, critérios de
qualidade reescritos como testes verificáveis. v2.2 incorpora as regras completas da competição
(ambiente de avaliação, pesos e dados públicos com revisão fixa, pacote reproduzível, licenças OSI)
e o papel da IA (`docs/gerais/ia_no_pipeline.md`): R21, R30 e R31 emendados; R44–R49 novos. A v1 saiu
direto de `scope.md`, sem fase Brainstorm (a demanda é um regulamento externo já fechado).
**Fase:** SDD 2b (convergente)
**Contrato:** implementa `scope.md`. Arquitetura em `DESIGN.md`; decisões duras em
`docs/decisions/`.
**Escopo:** MVP para a fase de treino do desafio e pronto para rodar no conjunto final cego.

Cada critério segue um dos cinco moldes EARS: Ubiquitous ("O sistema DEVE / NÃO DEVE ..."),
Event-driven ("QUANDO ... ENTÃO ..."), State-driven ("ENQUANTO ..."), Unwanted ("SE <situação
indesejada> ENTÃO ...") e Optional ("ONDE <recurso> ..."). Critério que não caiba em nenhum molde
é decisão de design disfarçada e pertence ao `DESIGN.md`.

Os números R# são estáveis: critério retirado fica listado em "Critérios retirados", nunca é
renumerado.

---

## Glossário

- **Documento** — um arquivo `.txt` de entrada, lido como UTF-8 sem tradução de quebra de linha
  (os arquivos da amostra não têm BOM nem `\r`).
- **Cabeçalho do documento** — bloco inicial do documento (órgão, número dos autos, partes,
  relator, protocolo), antes do primeiro parágrafo corrido.
- **Número dos autos** — o número de processo que aparece no cabeçalho do documento como sendo o
  do próprio documento ("Processo nº", "Autos nº", "Referência: autos nº").
- **Número de processo** — sequência numérica que identifica um processo judicial, com ou sem
  pontuação, em formato curto (`1.741.784`) ou CNJ (`7000380-08.2023.7.00.0000`), inclusive quando
  corrompida por OCR de modo corrigível (`21737l8`).
- **Classe processual** — tipo do processo ou recurso: `REsp`, `AREsp`, `HC`, `RHC`, `Rcl`, `RE`,
  `ADI`, `APL`, `RSE`, `RR`, `REspe`..., por sigla ou por extenso.
- **Classe processual principal** — a última classe de uma cadeia de recursos internos: em `AgInt
  no AgInt no REsp`, a principal é `REsp` e a cadeia é `AgInt no AgInt no`.
- **Identificador de lei** — número da lei (`Lei nº 13.105/2015`), nome (`Código de Processo
  Civil`) ou sigla (`CPC`).
- **Lei canônica** — a lei a que um identificador de lei se refere, identificada por tipo, número
  e ano (`CPC` → Lei 13.105/2015; `CLT` → Decreto-Lei 5.452/1943; `Constituição da República` →
  Constituição Federal de 1988). Sigla sem ano refere-se à versão vigente.
- **Citação** — trecho do corpo do documento em uma destas quatro formas:
  - **(a) acórdão com número**: classe processual + número de processo;
  - **(b) súmula**: `Súmula` ou `Súmula Vinculante` + número;
  - **(c) lei com artigo**: artigo + identificador de lei;
  - **(d) acórdão sem número**: (tribunal ou classe processual) + ano + relator, sem número de
    processo.
- **Span** — intervalo semiaberto `[inicio, fim)` de offsets em codepoints Unicode sobre o texto
  do documento.
- **Classe** — rótulo atribuído a uma citação: `real`, `inventada` ou `incompleta`.
- **Base canônica** — `desafio1_bracis.db`, tabela `documentos`: 1.014 registros (acórdãos de
  STF, STJ, STM, TSE e TST; súmulas; dispositivos de lei).
- **Cobertura congelada** — o conjunto de registros da base canônica. Registro ausente da base
  conta como inexistente, mesmo que exista no mundo real.
- **Número próprio** — o número de processo do próprio registro da base (ou o número da súmula),
  em oposição a números de precedentes citados dentro do seu texto.
- **id_canonico** — valor da coluna `id` (doc_id numérico do Jusbrasil) de um registro, como
  string de dígitos. **Não** é a coluna `documento_id` da base (`doc_0001`).
- **Candidatos** — para as formas (a) e (b), os registros cujo número próprio, reduzido a dígitos,
  é igual ao número da citação reduzido a dígitos; para a forma (c), os registros com a mesma lei
  canônica e o mesmo número de artigo.
- **Candidatos consistentes** — candidatos que não contradizem nenhum atributo explícito da
  citação (tribunal, UF, classe processual principal, cadeia de recursos). Atributo ausente na
  citação, ou lido com correção de OCR, não elimina candidato.
- **Caminho de decisão** — nome estável da regra que produziu a classe de uma citação (ver
  `DESIGN.md`, etapa [4]).
- **Acerto** (para confiança) — num par casado, classe igual à do gabarito e, se `real`, id
  aceito pelo gabarito. É o `y` do Brier no `kaggle_metric.py`.
- **IoU** (Intersection over Union) — sobreposição entre dois spans.
- **Par casado** — par (predição, gabarito) com IoU ≥ 0,5, casado 1-para-1 pelo maior IoU.
- **τ (tau)** — fração das citações `inventada` do gabarito classificadas como `real`.
- **Nível 1 / Nível 2** — subconjuntos de dificuldade (formato padrão vs. ruído de OCR), pesos 1×
  e 2×.
- **Amostra de desenvolvimento** — os 26 documentos de `txt/` com gabarito aberto.
- **Conjunto de controle** — documentos não usados para ajustar regras: (1) a parte de medida da
  amostra, fixa e listada em arquivo versionado, e (2) o conjunto sintético versionado.
- **Execução** — uma rodada do pipeline identificada por `run_id`.
- **Ambiente de avaliação** — o ambiente da organização: 1 GPU de 24 GB de VRAM, ~8 vCPUs, 32 GB
  de RAM.
- **Artefato publicado** — pesos de modelo ou dataset em repositório público (ex.: Hugging Face),
  referenciado por link + revisão fixa (hash de commit do repositório).
- **Modelo de linguagem (LLM)** — modelo generativo usado para ler campos ou gerar dados; nunca para
  decidir a classe.

## Extração

- **R1** (Ubiquitous): O sistema DEVE extrair as citações do corpo de cada documento.
- **R2** (Ubiquitous): O sistema DEVE representar cada citação por um span sobre o texto do
  documento.
- **R3** (Ubiquitous): O sistema NÃO DEVE emitir, para um mesmo documento, duas citações com IoU
  ≥ 0,5 entre si.
  > **Emenda de 2026-09-17.** A v1 tratava isso como falso positivo. O `kaggle_metric.py` rejeita
  > a submissão inteira nesse caso.
- **R4** (Event-driven): QUANDO um span emitido tiver interseção não vazia com uma citação do
  gabarito ENTÃO o IoU entre os dois DEVE ser ≥ 0,5.
  > **Emenda v2.1.** A v2 era circular: "citação extraída" já pressupõe IoU ≥ 0,5. Agora qualquer
  > sobreposição conta, e span mal delimitado reprova.
- **R33** (Ubiquitous): O sistema NÃO DEVE emitir trecho que não esteja em uma das quatro formas
  de citação.
  > **Novo em 2026-09-17; reescrito na v2.1.** Referências vagas ("a jurisprudência pacífica
  > desta Corte", "o entendimento sumulado", "o artigo correspondente do CPC") aparecem na amostra
  > e não estão no gabarito, embora o regulamento use exemplo parecido para `incompleta`. A v2
  > definia a exclusão pelo que faltava e contradizia o R1; agora a definição de citação resolve
  > as duas coisas. Ver ADR-005.
- **R34** (Ubiquitous): O sistema NÃO DEVE emitir span dentro do cabeçalho do documento nem
  span cujo número de processo seja igual ao número dos autos.
- **R35** (Event-driven): QUANDO um documento do conjunto de controle tiver uma versão com ruído
  de OCR (letra↔dígito dentro de número, espaço, ponto ou quebra de linha dentro de número,
  variação de `nº` ou de travessão) ENTÃO o sistema DEVE produzir, para cada citação, a mesma
  classe e o mesmo id que produz na versão sem ruído.
  > **Emenda v2.1.** "Reconhecer ruído" não tinha critério de aprovação. Agora é teste de pares
  > limpo × ruidoso gerados pelo conjunto sintético.

## Classificação

- **R5** (Ubiquitous): O sistema DEVE atribuir a cada citação emitida exatamente uma classe.
- **R6** (Event-driven): QUANDO uma citação estiver na forma (d) ENTÃO o sistema DEVE
  classificá-la como `incompleta`.
  > **Emenda de 2026-09-17; reescrito na v2.1.** Na amostra, as 32 incompletas são exatamente as
  > citações sem número, e tribunal + ano + relator sempre bate com vários registros.
- **R8** (Event-driven): QUANDO uma citação nas formas (a), (b) ou (c) não tiver candidatos ENTÃO o
  sistema DEVE classificá-la como `inventada`.
  > **Emenda de 2026-09-17.** Na amostra, as 64 inventadas (50 de jurisprudência, 14 de lei)
  > seguem essa regra.
- **R40** (Event-driven): QUANDO uma citação tiver candidatos e nenhum deles for consistente ENTÃO
  o sistema DEVE classificá-la como `inventada`.
  > **Novo em 2026-09-17; reescrito na v2.1.** Não ocorre na amostra; é a forma mais plausível de
  > alucinação no conjunto final (número existente emprestado). A v2 conflitava com o R7 quando
  > o filtro zerava; agora as três saídas (0, 1, N consistentes) são disjuntas. Ver ADR-007.
- **R9** (Event-driven): QUANDO uma citação tiver exatamente um candidato consistente ENTÃO o
  sistema DEVE classificá-la como `real`.
- **R7** (Event-driven): QUANDO uma citação tiver mais de um candidato consistente ENTÃO o sistema
  DEVE classificá-la como `incompleta`.
  > **Emenda de 2026-09-17.** O mesmo número de processo aparece em vários registros da base
  > (recursos internos do mesmo processo).
- **R36** (Event-driven): QUANDO uma citação na forma (c) trouxer inciso, parágrafo ou alínea
  ENTÃO o sistema DEVE produzir a mesma classe e o mesmo id que produz para o mesmo artigo sem
  eles.
  > **Reescrito na v2.1.** Na amostra, `art. 93, IX, da Constituição da República` é real e
  > resolve ao dispositivo do artigo 93.

## Resolução

- **R12** (Event-driven): QUANDO a classe de uma citação for `real` ENTÃO ela DEVE ter
  `id_canonico` igual ao id do seu único candidato consistente.
  > **Emenda v2.1.** Absorveu o R11 ("id não vazio"), que era mais fraco.
- **R13** (Event-driven): QUANDO a classe de uma citação for `inventada` ou `incompleta` ENTÃO o
  JSON da citação NÃO DEVE conter `resolucao.id_canonico`.
- **R14** (Ubiquitous): Toda citação classificada como `real` DEVE ter número (reduzido a dígitos)
  igual ao número próprio do registro resolvido, ou lei canônica e artigo iguais aos dele.
  > **Reescrito na v2.1** como propriedade verificável da saída: semelhança de tribunal, ano ou
  > relator nunca basta para `real`.
- **R48** (Event-driven): QUANDO um modelo de linguagem fornecer o número de uma citação ENTÃO o
  sistema DEVE aceitá-lo somente se a sequência de dígitos puder ser obtida do trecho normalizado da
  citação; caso contrário, a citação DEVE ser tratada como sem número lido.
  > **Novo na v2.2.** Impede que o LLM "corrija" OCR inventando dígitos. Ver ADR-013.
  > **25/09:** sem efeito na execução — o LLM leitor não foi adotado (ADR-013). Vale se ele voltar.

## Formato de saída

- **R15** (Ubiquitous): O sistema DEVE gravar, para cada documento, um arquivo
  `<documento_id>.json` numa mesma pasta, com `documento_id` e a lista `citacoes`; cada citação
  com `inicio` e `fim` inteiros, `trecho`, `tipo`, `classificacao` e, quando emitida,
  `confianca` numérica em [0, 1].
- **R38** (Ubiquitous): O `trecho` de cada citação DEVE ser igual a `texto[inicio:fim]`.
- **R42** (Ubiquitous): O `tipo` de cada citação DEVE ser `lei` para a forma (c) e
  `jurisprudencia` para as demais.
- **R16** (Ubiquitous): O sistema DEVE gerar o `submission.csv` executando, sem modificação, o
  `json_to_submission.py` distribuído pela organização.
- **R17** (Ubiquitous): O `submission.csv` DEVE ter uma linha para cada documento de entrada.
- **R18** (Event-driven): QUANDO um documento não tiver citação ENTÃO a coluna `citacoes` da sua
  linha DEVE conter `-`.
- **R19** (Ubiquitous): Na coluna `citacoes`, `id_canonico` ausente e `confianca` ausente DEVEM
  aparecer como `-`.
  > **Nota v2.1.** R18 e R19 são garantidos pelo conversor oficial (R16); ficam como verificação
  > do CSV gerado.

## Ferramentas

- **R21** (Ubiquitous): Toda biblioteca usada na execução que produz a submissão DEVE ter licença
  aprovada pela OSI que não restrinja uso comercial, e todo modelo usado DEVE ter pesos abertos sob
  licença desse tipo. Sistema operacional e drivers de hardware não contam.
  > **Emenda v2.2.** Foundational Rules 6c do Kaggle. Na prática: Qwen3 e Gemma 4 (Apache 2.0)
  > sim; Gemma 3, GAIA e Llama (licenças próprias) não.
- **R22** (Ubiquitous): A execução que produz a submissão NÃO DEVE fazer chamada a API externa,
  paga ou gratuita.
  > **Emenda v2.1.** "API paga" deixava passar API gratuita com chave.
- **R44** (Ubiquitous): A execução que produz a submissão DEVE caber no ambiente de avaliação: no
  máximo 24 GB de VRAM em uma GPU, 32 GB de RAM e ~8 vCPUs.
  > **Novo na v2.2.** Pipeline fora desse envelope é desclassificado.
- **R45** (Ubiquitous): Todo modelo carregado pela execução DEVE ser referenciado por link de
  repositório público e revisão fixa.
- **R46** (Ubiquitous): Os pesos de todo modelo treinado ou ajustado pela equipe e todo dataset
  gerado pela equipe e usado no treino DEVEM estar publicados como artefato publicado antes de
  30/09/2026 23h59 (BRT).
  > **Novo na v2.2.** Regra de fine-tuning (pesos publicados) e esclarecimento da equipe (dados
  > sintéticos permitidos desde que públicos).

## Confiança

- **R26** (Optional): ONDE a confiança for emitida, o Brier score no conjunto de controle DEVE ser
  menor que o de uma confiança constante igual à taxa média de acerto nesse conjunto.
  > **Reescrito na v2.1.** A v2 prescrevia o cálculo (design). Agora exige o resultado: a
  > confiança precisa ser melhor que um chute constante. O método fica no ADR-008. Absorveu o
  > R27.

## Avaliação

- **R28** (Ubiquitous): Toda execução DEVE gravar um relatório com score, F1 por classe, τ e
  Brier, por nível, calculados pelo `kaggle_metric.py`, para a amostra e para o conjunto de
  controle.
  > **Reescrito na v2.1.** Absorveu o R39. A v2 descrevia processo da equipe; agora é saída do
  > sistema.
- **R41** (Ubiquitous): A saída do sistema NÃO DEVE mudar quando os `documento_id` e os nomes dos
  arquivos de entrada forem trocados por outros.
- **R43** (Ubiquitous): O código-fonte NÃO DEVE conter, como literal, `id_canonico`,
  `documento_id` ou trecho de citação da amostra.
  > **Reescrito na v2.1.** A v2 juntava duas exigências e proibia "regra específica de
  > documento", o que não é verificável. O que dá para verificar ficou aqui; o resto é prática do
  > ADR-009.

## Reprodutibilidade

- **R30** (Ubiquitous): Dentro do ambiente de execução declarado do projeto (notebook do Kaggle com
  ambiente fixado, ou imagem Docker equivalente) e com a pasta de dados presente, um único comando
  DEVE executar indexação da base, carregamento dos modelos, processamento dos documentos e geração
  do `submission.csv`.
  > **Emenda v2.2.** O pacote reproduzível exige ambiente declarado (`requirements`/`Dockerfile`)
  > e o comando exato.
  > **Emenda v2.2.1 (revisão de escopo).** O notebook do Kaggle não aceita imagem Docker própria —
  > o ambiente real das submissões é o notebook com ambiente fixado (ADR-014,
  > `docs/gerais/guia_kaggle.md`); o `Dockerfile` é o formato de entrega equivalente para fora do Kaggle.
- **R31** (Event-driven): QUANDO uma submissão for gerada para envio ENTÃO o sistema DEVE recusar
  árvore git com mudanças não commitadas, DEVE registrar no manifesto o commit, as revisões dos
  modelos e a versão do ambiente de execução (tag da imagem do notebook Kaggle ou digest da imagem
  Docker), e DEVE criar uma tag git para ela.
- **R47** (Event-driven): QUANDO a execução usar um modelo generativo ENTÃO a decodificação DEVE ser
  determinística (temperatura 0, semente fixa registrada no manifesto).
  > **25/09:** a execução não usa modelo generativo (LLM não adotado); o encoder não é generativo e
  > roda em CPU. Continua valendo para a geração de dados fora da execução (camada 2 do sintético).
- **R49** (Ubiquitous): Duas execuções do mesmo comando, no mesmo ambiente e sobre a mesma entrada,
  DEVEM produzir `submission.csv` byte a byte idênticos.
  > **Novo na v2.2.** Regra do pacote reproduzível ("comando exato que reproduz as saídas
  > submetidas"). Ver ADR-014.

## Permissões (não são critérios de aceite)

- Um modelo de linguagem de pesos abertos pode ser servido por API durante o desenvolvimento
  (ex.: para gerar dados), desde que a mesma revisão de pesos rode localmente (ex-R23).
- Datasets públicos — inclusive os sintéticos gerados e publicados pela equipe — podem ser usados
  para treino e ajuste, nunca para resolver citações (ex-R24).
- Fine-tuning é permitido, com pesos publicados (R46).
- A confiança é opcional (ex-R25).
- Treino e geração de dados podem rodar em qualquer ambiente; a regra de reprodução vale para a
  execução que gera as saídas (ADR-014).

## Práticas da equipe (não são critérios de aceite)

- Avaliar localmente antes de submeter (ex-R28 da v2).
- Na fase de treino, o leaderboard usa a mesma amostra do gabarito local: diferença entre os dois
  scores indica erro de pipeline e deve ser investigada antes de nova submissão (ex-R29).
- Documentos do conjunto final são só processados, nunca lidos para ajustar regras (Foundational
  4b; tentar inferir o teste privado desclassifica).
- Repositório de código privado durante a competição, acesso só da equipe; uma conta Kaggle por
  pessoa (Foundational 5a, 5d, 6b).

## Critérios retirados

| R# | Destino |
|---|---|
| R10 | Consequência de R7 + R9 |
| R11 | Absorvido pelo R12 |
| R20 | Absorvido por R2 + R38 (a forma de calcular offsets é design: ADR-003) |
| R23, R24, R25 | Permissões |
| R27 | Absorvido pelo R26 |
| R29 | Prática da equipe |
| R32 | Absorvido pelo R30 |
| R37 | Design disfarçado: critério de pronto da frente A no `DESIGN.md` (ADR-002) |
| R39 | Absorvido pelo R28 |

## DEVE / NÃO DEVE (síntese)

**DEVE:**
- Extrair do corpo as citações nas quatro formas, com spans bem delimitados (R1, R2, R4).
- Classificar: forma (d) → `incompleta`; sem candidatos ou sem candidatos consistentes →
  `inventada`; um consistente → `real`; vários consistentes → `incompleta` (R6–R9, R40).
- Dar a mesma resposta com e sem ruído de OCR, e com e sem inciso/parágrafo (R35, R36).
- Entregar o id do único candidato consistente para toda `real` (R12, R14).
- Seguir o contrato do JSON e usar o conversor oficial sem modificação (R15–R19, R38, R42).
- Rodar só com dependências e modelos de licença OSI, sem API, dentro do ambiente de avaliação,
  por um comando na imagem Docker (R21, R22, R30, R44).
- Referenciar modelos por link + revisão e publicar pesos e dados sintéticos no prazo (R45, R46).
- Aceitar número lido por LLM só se os dígitos saírem do trecho (R48).
- Gerar a mesma submissão em duas execuções, com decodificação determinística (R47, R49).
- Relatar score na amostra e no conjunto de controle a cada execução (R28).
- Amarrar cada submissão a um commit, às revisões dos modelos e a uma tag (R31).

**NÃO DEVE:**
- Emitir citações sobrepostas com IoU ≥ 0,5 (R3).
- Emitir referências vagas, spans do cabeçalho ou o número dos autos (R33, R34).
- Entregar id fora da classe `real` (R13).
- Depender do nome dos documentos nem guardar literais da amostra no código (R41, R43).

## Critério de sucesso do MVP

Proposta, a confirmar pela equipe:
- os 96 reais da amostra resolvem para o `id_canonico` certo;
- τ = 0 na amostra e no conjunto de controle;
- nenhuma submissão rejeitada pelo `kaggle_metric.py`;
- a diferença de score entre a parte de ajuste e o conjunto de controle é pequena o bastante para
  não indicar regra decorada — o limiar fica a definir.

## Autocrítica dos critérios (v2.1)

- **R33 depende de uma divergência não resolvida** com o regulamento. Se o conjunto final anotar
  referências vagas, R33 custa recall de `incompleta`. Em análise pela equipe.
- **R49 vale para o mesmo ambiente.** O hardware da organização (L4/A10/4090) difere do Kaggle
  (T4); identidade entre ambientes não é garantida nem testável pela equipe. ADR-014 reduz o risco
  limitando o LLM a pontos com conferência (R48).
- **R44 é verificável só por aproximação**: sem acesso a uma GPU de 24 GB, a equipe testa em 16 GB
  (margem de segurança).
- **R40 e R7 têm pouca evidência**: nenhuma inventada da amostra reaproveita número existente, e
  só uma real tem dois candidatos. Os testes vêm do conjunto sintético.
- **A definição de citação é fechada em quatro formas.** Ficam fora, sem requisito: artigo sem
  lei ("o art. 5º"), súmula sem número, informativos. **Correção de 2026-09-18:** temas de repercussão geral *aparecem* na amostra (`Temã 2.680 da repercussão
  geral`, `inventada`) e o pipeline os extrai; sem classe, a decisão os trata como `numero_ausente`. O resto não aparece na amostra. Citações no plural ("arts. 489 e 1.022 do CPC") também não aparecem, e não
  há decisão se viram um span ou dois.
- **"Sigla sem ano refere-se à versão vigente"** (lei canônica) pode errar em citações ao CPC/1973;
  não há caso na amostra.
- **R35 e R41 são testes metamórficos**: dependem do gerador sintético e de uma rodada com nomes
  trocados. Sem essas ferramentas, não verificam nada.
- **O cabeçalho do documento** (R34) é delimitado por heurística ("antes do primeiro parágrafo
  corrido"); a fronteira exata é decisão de design.
