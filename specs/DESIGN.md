# DESIGN — Arquitetura do verificador de citações

**Data:** 2026-09-17
**Versão:** v2.1 — alinhado ao `DEFINE.md` v2.2. A v1 era só regras determinísticas; a v2 incorpora
as regras completas da competição (ambiente de avaliação com GPU, pesos e dados públicos, pacote
reproduzível) e a IA na leitura (`docs/ia_no_pipeline.md`); a v2.1 corrige o ambiente de execução —
o notebook do Kaggle não aceita imagem Docker própria, então o ambiente único das submissões é o
notebook com versão fixada, e o `Dockerfile` de entrega parte da imagem pública do Kaggle
(ADR-014, `docs/guia_kaggle.md`).
**Fase:** SDD 2c (arquitetural)
**Contrato:** implementa `DEFINE.md`. Decisões duras em `docs/decisions/` (ADR-001 a ADR-014).

---

## Decisão arquitetural central

A classe de uma citação é o resultado de uma **consulta à base por identificadores**: sem número
→ `incompleta`; número (ou lei + artigo) fora da base → `inventada`; exatamente um registro
consistente → `real` com o `id`. **A decisão é sempre determinística; a IA entra na leitura**
(ADR-001):

| Trabalho | Quem faz |
|---|---|
| Achar citações no texto | regex **∪** encoder NER treinado (ADR-011) |
| Ler os campos de uma citação | regras; LLM opcional só para as difíceis, com conferência (ADR-013) |
| Decidir a classe e o id | consulta ao índice da base, sem IA (ADR-006, ADR-007) |
| Gerar dados de treino e de controle | código + LLM, fora da execução (ADR-012) |

### Evidência de viabilidade (rascunhos descartáveis, 2026-09-17)

| Verificação na amostra | Resultado |
|---|---|
| Incompletas sem número de processo | 32 de 32 |
| Inventadas de jurisprudência com número ausente da base (índice por número próprio) | 50 de 50 |
| Citações de lei que seguem "lei + artigo na base ↔ real" | 28 de 28 |
| Reais de jurisprudência resolvidas por um índice rascunho | 68 de 82 — as 14 falhas foram de leitura de número (`21737l8`, CNJ sem pontuação, `SÚMULA` maiúsculo) |
| Busca do número no texto inteiro da base, sem índice por número próprio | 2 de 40 inventadas viram candidatas; 10 de 77 reais ficam ambíguas |
| Números fora do gabarito | 43, todos de cabeçalho, protocolo, OAB ou valores |
| Offsets do gabarito vs. `texto[inicio:fim]` | 192 de 192 batem |

## Dois momentos: desenvolvimento e execução

| Momento | O quê | Onde roda | Artefato |
|---|---|---|---|
| **Desenvolvimento** | gerar dados sintéticos (código + LLM) | Kaggle GPU (LLM), qualquer CPU (código) | dataset público no Hugging Face (R46) |
| | treinar o encoder NER | Kaggle GPU | pesos públicos no Hugging Face (R46) |
| | regras, tabelas, índice, avaliação | qualquer CPU | código no repositório privado |
| **Execução** | o comando que gera `submission.csv` | notebook do Kaggle, ambiente fixado, **uma** GPU T4 ≤ 16 GB, float16 (`docs/guia_kaggle.md`) | submissão + manifesto + relatório (ADR-014) |

Treino e geração não precisam ser refeitos pela organização: o que ela reproduz é a execução, a
partir dos artefatos publicados (link + revisão). O notebook do Kaggle não aceita imagem Docker
própria — a reprodução da execução é feita clonando o repositório numa tag fixa dentro do ambiente
oficial do Kaggle (`docs/guia_kaggle.md`); o `Dockerfile` entregue à organização parte da mesma
imagem pública do Kaggle, para que o pacote reproduzível funcione fora do Kaggle também
(ADR-014).

## Pipeline de execução

```
INÍCIO — uma vez por execução
[A] Índice            desafio1_bracis.db → índice estruturado                    R12, R14 · ADR-002, ADR-004
[M] Modelos           encoder NER (link + revisão) · LLM se ligado (link +       R21, R44, R45, R47 · ADR-011, ADR-013, ADR-014
                      revisão, temperatura 0, seed) — float16, uma GPU

PARA TODOS OS DOCUMENTOS
[1] Texto             .txt original → cabeçalho delimitado + cópia normalizada   R2, R34, R35, R38 · ADR-003
                      + mapa de offsets normalizado→original
[2] Extração          regex ∪ encoder NER → filtro das formas a·b·c·d             R1, R4, R33 · ADR-005, ADR-011
                      → resolução de sobreposição                                R3
[3] Campos            candidata → campos por regras                              R35, R36
                      └─ não leu? → fila de difíceis

EM LOTE, SÓ PARA A FILA (se o LLM estiver ligado)
[3b] Campos por LLM   trecho → JSON de campos → conferência dos dígitos          R47, R48 · ADR-013

DE VOLTA PARA CADA CITAÇÃO
[4] Decisão           campos × índice → candidatos → consistentes → caminho      R5–R9, R12–R14, R40 · ADR-006, ADR-007
[5] Confiança         caminho → taxa de acerto medida no controle                R26 · ADR-008
[6] Saída             JSON por documento → json_to_submission.py → CSV           R15–R19, R38, R42
[7] Avaliação         kaggle_metric.py (amostra + controle) → relatório          R28, R41, R43, R49 · ADR-009
```

### [A] Índice da base

Um parser por natureza e tribunal extrai o **número próprio** do registro (ADR-002):

| Fonte | Onde está o número próprio | Exemplo |
|---|---|---|
| STJ | primeira ocorrência `Nº` no cabeçalho | `AgRg no AGRAVO EM RECURSO ESPECIAL Nº 1.327.863 - PR` |
| STF | classe + número depois de data e órgão | `AG.REG. NA RECLAMAÇÃO 76.532 RIO DE JANEIRO` (UF por extenso) |
| STM, TSE | primeiro número CNJ do cabeçalho | `APELAÇÃO CRIMINAL Nº 7000075-58.2022.7.00.0000/PR` |
| TST | rodapé `PROCESSO Nº TST-...` (não o primeiro número do texto) | `PROCESSO Nº TST-ED-E-ED-RR-3400-05.2011.5.21.0009` |
| Súmula | `Súmula [Vinculante] n. N do TRIBUNAL` | `Súmula n. 83 do STJ` |
| Dispositivo | `Artigo N da\|do <lei>` | `Artigo 373 da Lei nº 13.105, de 16 de março de 2015` |

Alternativa mais barata a medir: gerar candidatos pelo índice FTS5 que vem na base e conferir se o
número está no cabeçalho do registro — troca "um parser por tribunal" por "uma checagem de posição".

Esquema do índice (uma linha por registro):

```
id                 str   # coluna id da base = id_canonico
natureza           acordao | sumula | dispositivo
tribunal           STF | STJ | STM | TSE | TST | None
numero             str   # só dígitos; súmula: "S83" / "SV10"
classe_principal   str   # REsp, AREsp, HC, RHC, Rcl, RE, APL, RSE, RR, REspe...
cadeia_recursos    tuple # ("AgInt", "AgInt") para "AgInt no AgInt no REsp"
uf                 str | None
ano                int | None
relator            str | None   # normalizado: sem "Min.", sem acento, minúsculo
lei_chave          str | None   # LEI-13105-2015, DL-5452-1943, CF-1988...
artigo             str | None   # "373", "5"
```

Tabelas versionadas, fora do código: **apelidos de lei** (CPC, CLT, CDC, CPP, CPM, Código Civil,
Código Eleitoral, Constituição Federal/da República, LC 64/1990... → `lei_chave`), **classes
processuais** (sigla e nome por extenso → `classe_principal`: `Rec. Esp.`, `R.Esp.`,
`Recurso Especial` → `REsp`), **UFs** (sigla ↔ nome por extenso), **confusões de OCR**
(`l`→`1`, `O`→`0`, `S`→`5`, `g`→`9`).

### [M] Modelos

- **Encoder NER** (ADR-011): candidatos RoBERTaLexPT, BERTimbau, Legal-BERTimbau — escolha por
  medição e licença OSI (R21). Marcação BIO por token; posições voltam ao texto original pelo mapa.
  ~0,5 GB de VRAM; também roda em CPU.
- **LLM** (ADR-013, opcional): candidatos Qwen3 8B, Gemma 4 E4B (Apache 2.0). vLLM ou
  `transformers`, float16, temperatura 0, semente fixa. Qwen3 8B em float16 ocupa ~16–17 GB + cache;
  o conjunto encoder + LLM precisa caber numa T4 de 16 GB para garantir margem sobre os 24 GB
  (ADR-014) — se não couber, usar o modelo menor.
- Ambos carregados **uma vez** por execução, por link + revisão (R45).

### [1] Texto: cabeçalho, normalização e mapa de offsets

- **Cabeçalho**: bloco inicial com órgão, número dos autos, partes, relator e protocolo, até o
  primeiro parágrafo corrido. Nada do cabeçalho é extraído (R34). Critério de pronto: nenhum dos
  43 números fora do gabarito vira candidata.
- **Normalização** (ADR-003), sem alterar o original: quebra de linha → espaço;
  `n°`/`No`/`n.`/`N.` → `nº`; travessões → `-`; espaços dentro de números colapsados; troca
  letra→dígito **só dentro de token numérico**; `5úmula` → `Súmula`. Toda troca que muda o tamanho
  do texto registra o deslocamento no mapa.
- **Mapa**: vetor `posição normalizada → posição original`. Todo span sai por ele.

### [2] Extração

Duas fontes de candidatas, somadas:

1. **Regex** — uma família de padrões por forma de citação do glossário do `DEFINE.md`, sobre o corpo
   normalizado (ADR-005, R33):

| Forma | Nome no código | Padrão (ideia) | Exemplo da amostra |
|---|---|---|---|
| (a) | `com_numero` | [cadeia de recursos] classe processual + `nº`? + número [+ UF] | `AgInt no AREsp nº 1.996.496/RJ` |
| (b) | `sumula` | `Súmula [Vinculante]` + número [+ `do` tribunal] | `Súmula 211 do STJ` |
| (c) | `lei_artigo` | `art.`/`artigo` + número [+ inciso/§/alínea] + `da`/`do` + identificador de lei | `art. 896, § 1º-A, da CLT` |
| (d) | `sem_numero` | (`julgado`/`precedente`/`acórdão` do TRIBUNAL \| CLASSE [do TRIBUNAL]) + ano + (`relatoria de`/`Rel. Min.`) + nome | `Rcl de 2022, Rel. Min. Alexandre De Moraes` |

2. **Encoder NER** — spans marcados pelo modelo sobre o **corpo original** (o encoder é treinado com
   ruído de OCR, então não precisa da cópia normalizada).

**Filtro**: toda candidata do encoder precisa se encaixar numa das quatro formas depois da leitura de
campos; o que não se encaixa é descartado (impede que "a jurisprudência pacífica desta Corte" volte).

**Sobreposição** (R3): candidatas com IoU ≥ 0,5 entre si viram uma só — fica a mais específica
(com número > sem número), depois a presente nas duas fontes, depois a mais longa. Candidata contida
em outra é descartada.

O detector de **referência vaga** existe atrás de uma chave **desligada**, enquanto a equipe analisa
a divergência com o regulamento (ADR-005).

### [3] Campos

Cada família tem seu leitor por regras. Número sai só com dígitos; `correcao_ocr = True` se alguma
troca letra→dígito aconteceu dentro dele. Relator normalizado como no índice. Inciso, parágrafo e
alínea ficam fora de `artigo` (R36).

**Fila de difíceis**: vai para o LLM a candidata em que o leitor por regras não conseguiu extrair o
que a forma exige (número nas formas a/b; lei + artigo na c; tribunal ou classe + ano + relator na d).

### [3b] Campos por LLM (opcional)

- Uma chamada em lote com todas as difíceis da execução (na amostra, estimativa de ~20 citações).
- Prompt fixo e versionado; saída JSON com os campos da forma.
- **Conferência** (R48): o número devolvido só é aceito se seus dígitos puderem ser obtidos do trecho
  normalizado aplicando só as trocas da tabela de confusões de OCR. Falhou → sem número.
- Resultado marcado `fonte = "llm"` no rastro.

### [4] Decisão

Duas etapas, com os termos do glossário do `DEFINE.md` (ADR-006, ADR-007):

1. **Candidatos** — formas (a) e (b): registros com o mesmo número reduzido a dígitos (súmula:
   `S...`/`SV...`, de qualquer tribunal); forma (c): mesma lei canônica e mesmo artigo.
2. **Consistentes** — candidatos que nenhum atributo explícito da citação contradiz, na ordem
   tribunal, UF, classe processual principal, cadeia de recursos. Atributo ausente ou lido com
   correção de OCR não elimina ninguém.

Cada citação termina em exatamente um **caminho** com nome estável:

| Caminho | Condição | Classe | id | Critério |
|---|---|---|---|---|
| `sem_numero` | forma (d) | incompleta | — | R6 |
| `numero_ausente` | formas (a)/(b), 0 candidatos | inventada | — | R8 |
| `numero_contradito` | formas (a)/(b), candidatos, 0 consistentes | inventada | — | R40 |
| `numero_unico` | formas (a)/(b), 1 candidato, consistente | real | `id` | R9 |
| `numero_desempatado` | formas (a)/(b), N candidatos, 1 consistente | real | `id` | R9 |
| `numero_ambiguo` | formas (a)/(b), N consistentes | incompleta | — | R7 |
| `lei_apelido_desconhecido` | forma (c), identificador fora da tabela de apelidos → sem lei canônica → 0 candidatos | inventada | — | R8 |
| `lei_ausente` | forma (c), 0 candidatos | inventada | — | R8 |
| `lei_unica` | forma (c), 1 candidato | real | `id` | R9 |
| `lei_ambigua` | forma (c), N candidatos | incompleta | — | R7 |

A tabela é exaustiva e os caminhos são disjuntos. O caminho não depende de quem leu os campos
(regras ou LLM); a origem fica registrada para a confiança.

### [5] Confiança

`confianca = taxa_de_acerto[caminho, correcao_ocr, fonte_dos_campos]`, lida de uma tabela gerada pela
avaliação no conjunto de controle; menos de 5 ocorrências → taxa média da classe (ADR-008). O
relatório compara o Brier obtido com o de uma confiança constante (R26); se não for menor, a
confiança não é enviada.

### [6] Saída

Um arquivo `<documento_id>.json` por documento no contrato (R15, R38, R42): `trecho` sempre
`texto_original[inicio:fim]`; `tipo` `lei` para a forma (c) e `jurisprudencia` para as demais;
`resolucao.id_canonico` só em `real` (R13). O `submission.csv` sai do `json_to_submission.py`
oficial, chamado sem modificação (R16); o manifesto guarda o hash do script.

### [7] Avaliação

`kaggle_metric.py` (a função `avaliar()`, sem reimplementação) roda sobre a amostra e sobre o
conjunto de controle (parte de medida da amostra + fatia reservada do sintético). Testes metamórficos:
pares limpo × ruidoso (R35), nomes de documento trocados (R41). A submissão só é enviada se duas
execuções derem CSV idêntico (R49).

## Contratos entre módulos

Estruturas imutáveis compartilhadas (`src/verificador/contratos.py`). Cada frente pode trabalhar com
dados falsos nesse formato antes das outras ficarem prontas.

```python
TextoPreparado(original: str, corpo_inicio: int, normalizado: str, mapa: list[int])

Candidata(inicio: int, fim: int, trecho: str,          # offsets e trecho do ORIGINAL
          tipo: Literal["jurisprudencia", "lei"],
          forma: Literal["com_numero", "sumula", "lei_artigo", "sem_numero"],
          padrao: str,                                  # nome do padrão ou "encoder"
          origem: frozenset[Literal["regex", "encoder"]])

Campos(tribunal, classe_principal, cadeia_recursos: tuple[str, ...], numero, uf,
       ano, relator, lei_chave, artigo, correcao_ocr: bool,
       fonte: Literal["regras", "llm"])                               # demais opcionais

RegistroIndice(id, natureza, tribunal, numero, classe_principal, cadeia_recursos,
               uf, ano, relator, lei_chave, artigo)

Resolucao(classificacao: Literal["real", "inventada", "incompleta"],
          id_canonico: str | None, caminho: str,
          candidatos: tuple[str, ...], confianca: float | None)

CitacaoVerificada(candidata: Candidata, campos: Campos, resolucao: Resolucao)
```

Assinaturas de fronteira:

```python
indexar(caminho_db) -> list[RegistroIndice]                          # frente A
preparar(texto: str) -> TextoPreparado                               # frente B
extrair(t: TextoPreparado, encoder) -> list[Candidata]               # frente B
ler_campos(c: Candidata) -> Campos | None                            # frente B (None → fila)
ler_campos_llm(fila: list[Candidata], llm) -> list[Campos | None]    # frente D
decidir(campos: Campos, forma, indice) -> Resolucao                  # frente D
escrever_json(documento_id, list[CitacaoVerificada], pasta)          # frente C
```

## Os 3 pilares de produção

### Identidade

Cada execução grava `runs/<run_id>/manifesto.json`: `run_id`, data/hora, commit, árvore suja ou não,
hash da configuração, hash das tabelas, hash do `.db`, hash do `json_to_submission.py`, **link +
revisão de cada modelo**, tipo numérico, semente, **versão do ambiente do notebook Kaggle**
(imagem/tag fixada), GPU e driver. Cada
submissão enviada tem uma tag git `sub-NNN` (R31).

### Observabilidade

`runs/<run_id>/relatorio.md`, separado por nível e por conjunto (ajuste, medida, sintético):
- score, macro-F1, F1 por classe, τ e Brier — do `avaliar()` do `kaggle_metric.py`;
- recall de spans (IoU ≥ 0,5), spans espúrios, duplicatas (deve ser zero);
- candidatas por origem (só regex, só encoder, ambos) e quanto cada uma acerta;
- tamanho da fila de difíceis, taxa de campos aceitos e recusados na conferência do LLM;
- matriz de confusão das 3 classes e contagem por caminho de decisão;
- índice: registros sem número extraído, números repetidos;
- tempo por etapa, pico de VRAM e de RAM (R44);
- diferença contra a execução anterior.

### Rastreabilidade

`runs/<run_id>/rastro.jsonl`: uma linha por citação com documento, span, origem (regex/encoder),
padrão, campos lidos e fonte (regras/llm), resposta bruta do LLM quando houver, correções de OCR,
candidatos no índice, caminho, classe, id e confiança. `runs/<run_id>/erros.md` junta o rastro com o
gabarito e agrupa os erros: span perdido, span espúrio (por origem), classe errada por caminho, link
errado, real perdida por dúvida (ADR-006). O rastro fica fora do JSON do contrato.

### Débito técnico consciente e declarado

- Delimitação do cabeçalho é heurística.
- Tabelas de apelidos, classes e confusões de OCR são mantidas à mão.
- O gerador sintético reproduz os vieses de quem o escreveu (ADR-012).
- A convenção de anotação do LeNER-Br difere do gabarito (ADR-011).
- `numero_contradito` e `lei_apelido_desconhecido` não têm exemplo na amostra.
- Identidade de saída entre o Kaggle (T4) e o ambiente da organização (L4/A10/4090) não é testável
  (ADR-014).

## Stack e restrições

| Camada | Escolha | Razão |
|---|---|---|
| Linguagem | Python 3.13 | Mesmo ambiente dos scripts oficiais |
| Base | `sqlite3` da biblioteca padrão, só leitura | A base já vem em SQLite |
| Padrões | `re` da biblioteca padrão | Sem dependência |
| Encoder | `torch` + `transformers` | Treino e inferência de NER |
| LLM (opcional) | `vllm` ou `transformers` | Lote eficiente; vLLM só na T4 (não na P100) |
| Avaliação | `pandas`, `numpy` | Exigidos pelo `kaggle_metric.py` |
| Testes | `pytest` | — |
| Execução (submissões) | notebook do Kaggle, ambiente fixado + `requirements.txt` (`docs/guia_kaggle.md`) | O Kaggle não aceita imagem própria; é o ambiente real das submissões |
| Ambiente (entrega) | `Dockerfile` a partir da imagem pública `gcr.io/kaggle-gpu-images/python` (tag fixa) + `requirements.txt` | Pacote reproduzível (R30) fora do Kaggle |
| Artefatos | Hugging Face (pesos e dataset públicos) | Regra de pesos e dados públicos (R45, R46) |

Toda biblioteca e todo modelo passam por conferência de licença OSI antes de entrar (R21).

Restrições: sem rede no caminho principal, exceto baixar modelos por link + revisão (ou tê-los em
cache na imagem); uma GPU ≤ 16 GB em float16 na execução; modo "só CPU e sem LLM" sempre funcional.

## Estrutura do repositório

```
agente_jusbrasil/                         # GitHub privado durante a competição (ADR-010)
├── scope.md · DEFINE.md · DESIGN.md · explicação_jus_brasil.md
├── docs/ia_no_pipeline.md
├── docs/decisions/ADR-*.md
├── desafio-jusbrasil-bracis-2026/        # dados oficiais — fora do git
├── src/verificador/
│   ├── cli.py                            # indexar · rodar · avaliar · submeter
│   ├── contratos.py
│   ├── configuracao.py                   # chaves: encoder, llm, referência vaga; revisões; dtype
│   ├── base/                             # frente A: parsers por tribunal, índice
│   ├── tabelas/                          # apelidos de lei, classes, UFs, confusões de OCR, confiança
│   ├── texto/                            # frente B: cabeçalho, normalização, mapa
│   ├── extracao/                         # frente B: regex, encoder, filtro, sobreposição, campos
│   ├── decisao/                          # frente D: caminhos, desempate, confiança, leitor LLM
│   └── saida/                            # frente C: JSON, chamada ao conversor, manifesto
├── avaliacao/                            # frente C: relatório, divisão da amostra, testes metamórficos
├── sintetico/                            # frente C: gerador (código + prompts do LLM), publicação
├── treino/                               # frente B: treino do encoder, publicação dos pesos
├── notebooks/kaggle/                     # notebooks finos que só clonam o repo e chamam a CLI
├── tests/
├── runs/                                 # saídas por execução — fora do git
├── Dockerfile                            # a partir da imagem pública do Kaggle (ADR-014)
└── requirements.txt
```

Passo a passo de como o código chega ao notebook do Kaggle (clonar com token, fixar ambiente,
instalar, rodar): `docs/guia_kaggle.md`.

Comandos:

```
python -m verificador ambiente                                            # grava commit, GPU, driver, versões
python -m verificador indexar  --dados desafio-jusbrasil-bracis-2026
python -m verificador rodar    --entrada <pasta de .txt> --run <run_id> [--sem-llm] [--sem-encoder]
python -m verificador avaliar  --run <run_id>
python -m verificador submeter --run <run_id>   # árvore limpa, roda duas vezes, compara, cria tag
```

## Frentes de trabalho

| Frente | Módulos | Critério de pronto |
|---|---|---|
| A — Índice | `base/`, tabelas de apelidos, classes, UFs, confusões de OCR | zero registro sem número próprio, sem pegar número de precedente (ADR-002); os 96 reais da amostra encontram seu `id` pelo número |
| B — Texto, extração e encoder | `texto/`, `extracao/`, `treino/` | teste de mapa: 192 trechos batem (R38); R4 e R3 na amostra; nenhum dos 43 números de cabeçalho extraído (R34); encoder publicado e medido contra só-regex |
| C — Avaliação e dados | `saida/`, `avaliacao/`, `sintetico/`, `cli.py`, `Dockerfile` | toda execução gera manifesto, relatório (R28), rastro e erros; gerador com pares limpo × ruidoso (R35) e números emprestados (R40), dataset publicado; testes R41, R43, R49; `submeter` cumpre R31 |
| D — Decisão, confiança e LLM | `decisao/`, tabela de confiança, leitor LLM | um teste por caminho da tabela [4]; R36; τ = 0 na amostra e no controle; R26; LLM medido contra sem-LLM e conferência R48 testada |

## Ordem de implementação

1. `contratos.py`, `configuracao.py` e o esqueleto de `cli.py` (frente C) — o resto depende deles.
2. **Esqueleto andante**: `rodar` gera JSON vazio para cada documento, converte com o script oficial,
   `avaliar` roda o `kaggle_metric.py`, `Dockerfile` mínimo a partir da imagem do Kaggle, primeiro
   notebook em `notebooks/kaggle/` clonando o repositório (`docs/guia_kaggle.md`). Primeira
   submissão só para validar o formato de ponta a ponta, inclusive o caminho repo → notebook.
3. Frentes A, B (regex) e C (gerador por código) em paralelo, integrando por pull request contra os
   contratos; D implementa a decisão sobre campos falsos.
4. **Primeira versão só-regras integrada** → submissão → análise de erro. É a linha de base de tudo
   que vem depois.
5. Gerador com LLM (Kaggle GPU) → treino do encoder → publicação dos pesos → encoder integrado e
   medido contra a linha de base.
6. Leitor LLM de campos difíceis, medido contra a versão sem LLM; entra só se ganhar.
7. Confiança calibrada.
8. Congelamento: publicação final de pesos e dataset (dentro do prazo), README, `Dockerfile` com
   versões fixas, verificação de determinismo, `code-review`.

## Fora do escopo

Treinar modelo do zero; fine-tuning de LLM; interface web; API na execução; LLM decidindo classe;
qualquer ajuste guiado pelo leaderboard da fase de treino ou pela leitura do conjunto final.
