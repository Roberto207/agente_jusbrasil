# Tarefas da equipe — do esqueleto à submissão final

**Data:** 2026-09-18 · **Prazo final:** 30/09/2026, 23h59 (BRT) · **Dias úteis restantes:** 12
**Estado de partida:** o esqueleto andante (itens 1–2 do `BUILD_PROMPT.md`) está pronto e verificado:
`rodar` gera JSON vazio por documento → `json_to_submission.py` → `submission.csv` → `avaliar` roda o
`kaggle_metric.py` (score 0, como esperado). **Toda a lógica real ainda não existe.**

Este arquivo é o plano de trabalho das próximas etapas (3 a 8 do `BUILD_PROMPT.md`), quebrado em
tarefas que cada integrante pode pegar. Complementa, sem substituir:

| Documento | Serve para |
|---|---|
| `specs/DEFINE.md` (R#) | *o que* o sistema deve fazer — os critérios de aceite citados abaixo |
| `specs/DESIGN.md` | *como* — arquitetura, contratos, tabela de caminhos de decisão |
| `docs/decisions/ADR-*` | *por quê* — decisões duras já tomadas (não reabrir sem motivo) |
| `ação_humana_pendente.md` | o que só um humano faz (contas, tokens, e-mail, submissão) |
| `docs/guia_kaggle.md` | como rodar no Kaggle |

Marque `[x]` ao concluir. Onde houver `Responsável: ____`, preencher na reunião de divisão.

---

## 0. Como o trabalho se encaixa

```
.txt ─► [B] acha citações + offsets ─► [B] lê campos ─► [D] decide classe/id ─► [C] JSON → CSV → nota
                                                              ▲
                                     [A] índice da base (1014 registros) ─┘
```

Cada frente entrega uma função com assinatura fixa (`DESIGN.md`, "Contratos entre módulos"):

```python
indexar(caminho_db) -> list[RegistroIndice]                          # A
preparar(texto: str) -> TextoPreparado                               # B
extrair(t: TextoPreparado, encoder) -> list[Candidata]               # B
ler_campos(c: Candidata) -> Campos | None                            # B   (None → fila do LLM)
decidir(campos: Campos, forma, indice) -> Resolucao                  # D
escrever_json(documento_id, list[CitacaoVerificada], pasta)          # C
```

Por isso as quatro frentes começam **ao mesmo tempo**, cada uma com dados falsos no formato dos
contratos, e só se encontram no dia de integração.

### Números de referência da amostra (para os testes)

- 26 documentos (13 de nível 1 + 13 de nível 2) em `txt/`; gabarito em `goldenset_offsets.csv`.
- 192 citações no gabarito: **96 `real`**, **64 `inventada`** (50 jurisprudência + 14 lei), **32 `incompleta`**
  (todas sem número, forma d).
- Base: 1014 registros (acórdãos de STF/STJ/STM/TSE/TST, súmulas, dispositivos de lei).
- 43 números de cabeçalho que **não** podem virar citação (R34).
- A coluna `id` da base é o `id_canonico`; **não** confundir com `documento_id` (`doc_0001`).

### Regras de convivência (valem para todas as frentes)

1. **`contratos.py` é congelado.** Mudança de campo = avisar o grupo antes, porque as 4 frentes dependem dele.
2. **Um branch por frente** (`frente-a-indice`, `frente-b-extracao`…), PR para `main`. Não commitar direto em `main`.
3. **Cada PR traz seus testes** — os critérios de pronto viram testes `pytest`, não checklist manual.
4. **Nada específico da amostra no código** (R43): nenhum `id_canonico`, `documento_id` ou trecho de citação do
   gabarito como literal. Vale também para os testes de produção — fixtures da amostra ficam em `tests/` e são
   lidas do arquivo, nunca coladas como constante no `src/`.
5. **Saída independe do nome do arquivo** (R41): nunca usar `documento_id` como sinal de decisão.
6. **Não ajustar regra olhando o leaderboard** (ADR-009). Ajuste na parte *ajuste* da amostra; meça na parte
   *controle*.
7. **Dependências novas só com licença OSI** (R21) e listadas em `requirements.txt` com versão fixa. Nada de
   chamada de rede na execução (R22).
8. Antes de mexer no `cli.py`, avisar a frente C (é o arquivo mais compartilhado).


## 1. Divisão sugerida das frentes

| Pessoa | Frente | Por quê | Responsável |
|---|---|---|---|
| 1 | **B** — texto e extração | Maior e mais sujeita a erro; precisa de fluência em regex e string | ____ |
| 2 | **A** — índice da base | Parsing sobre dados reais; muito independente das outras | ____ |
| 3 | **D** — decisão + integração do `rodar` | D começa leve (tabela pequena); sobra tempo para ligar A+B+D | ____ |
| 4 | **C** — avaliação, sintético e saída | Mede tudo; depois alimenta encoder e LLM | ____ |

**Variação se B ficar pesada:** dividir em **B1** (cabeçalho, normalização, mapa de offsets) e **B2** (regex das
4 formas + leitura de campos). Quem terminar A cedo assume B2.

**Sugestão para o Roberto:** D + integração — conhece o fluxo inteiro e sabe onde cada erro nasce.

---

## Fase 1 — Frentes em paralelo (19–24/09)

### Frente A — Índice da base (`src/verificador/base/`)

**Responsável:** ____ · **Branch:** `frente-a-indice` · **Depende de:** só de `contratos.py`
**Requisitos:** R12, R14 · ADR-002, ADR-004 · **Entrega:** `indexar(caminho_db) -> list[RegistroIndice]`

**Status: ✅ concluída** pelo colega Caio (commit `57cd9ed`; ver `mudancas_caio_fase_1_a.md`). 96/96 reais resolvem;
o índice ficou idêntico após a troca da tabela de siglas TST (agora compartilhada com a frente B).

**Contexto.** A base tem 1014 registros, mas o número próprio de cada um está *dentro* do texto do cabeçalho, em
formato diferente por tribunal. O risco central (ADR-002) é pegar o número de um *precedente citado* no corpo
em vez do número do próprio registro. A decisão real/inventada depende inteiramente de o índice estar certo.

**Tarefas**

- [x] **Explorar a base.** Abrir `desafio1_bracis.db` (tabela `documentos`: `documento_id, id, tribunal, ano,
      relator, natureza, tipo, texto, texto_len`). Contar registros por `natureza` e `tribunal`; ler 3–5
      cabeçalhos de cada tipo. Anotar as variações de formato encontradas em `docs/` (ou no PR).
- [x] **Parser de número próprio por fonte** (tabela do `DESIGN.md`, seção [A]):
  - [x] STJ: primeira ocorrência `Nº` no cabeçalho (`AgRg no AGRAVO EM RECURSO ESPECIAL Nº 1.327.863 - PR`).
  - [x] STF: classe + número depois de data e órgão; UF por extenso (`RECLAMAÇÃO 76.532 RIO DE JANEIRO`).
  - [x] STM e TSE: primeiro número CNJ do cabeçalho (`7000075-58.2022.7.00.0000/PR`).
  - [x] TST: rodapé `PROCESSO Nº TST-...` — **não** o primeiro número do texto.
  - [x] Súmula: `Súmula [Vinculante] n. N do TRIBUNAL` → número `S83` / `SV10`.
  - [x] Dispositivo de lei: `Artigo N da|do <lei>` → `lei_chave` + `artigo`.
  - *Alternativa a medir se os parsers ficarem caros:* gerar candidatos pelo índice FTS5 que já vem na base
    (`documentos_fts`) e conferir se o número está *no cabeçalho* do registro.
- [x] **Extrair os demais atributos** de cada `RegistroIndice`: `tribunal`, `classe_principal`,
      `cadeia_recursos` (ex.: `("AgInt","AgInt")` para `AgInt no AgInt no REsp`), `uf`, `ano`, `relator`
      (normalizado: sem `Min.`, sem acento, minúsculo).
- [x] **Tabelas versionadas, fora do código** (ex.: `src/verificador/base/tabelas/*.toml` ou `.json`):
  - [x] **Apelidos de lei** → `lei_chave` (CPC, CLT, CDC, CPP, CPM, Código Civil, Código Eleitoral,
        Constituição Federal / da República, LC 64/1990…; `CPC` → `LEI-13105-2015`, `CLT` → `DL-5452-1943`).
        **Começar pelas leis que realmente aparecem na base e na amostra.**
  - [x] **Classes processuais**: sigla e nome por extenso → `classe_principal`
        (`Rec. Esp.`, `R.Esp.`, `Recurso Especial` → `REsp`; `AgInt`, `AgRg`, `EDcl`…).
  - [x] **UFs**: sigla ↔ nome por extenso.
  - [x] **Confusões de OCR**: `l→1`, `O→0`, `S→5`, `g→9` (a mesma tabela é usada pelo R48 e pela frente B).
- [x] **Implementar `indexar()`** de verdade (substitui a checagem de contagem que o CLI faz hoje) e ligar ao
      subcomando `indexar` (coordenar com a frente C).
- [x] **Tratar duplicidade:** o mesmo número de processo aparece em vários registros (recursos internos do
      mesmo processo). O índice deve permitir buscar **todos** os registros por número reduzido a dígitos.
- [x] **Função de consulta** (usada pela frente D): `por_numero(digitos) -> list[RegistroIndice]` e
      `por_lei_artigo(lei_chave, artigo) -> list[RegistroIndice]`.

**Testes (pytest)**

- [x] Zero registro sem número próprio (exceto os que legitimamente não têm — listar e justificar).
- [x] **Nenhum registro usa número de precedente** (ADR-002): para uma amostra de registros, o número escolhido
      está no cabeçalho, não no corpo.
- [x] **Os 96 `real` do gabarito encontram o `id_canonico` certo pelo número** (leitura do gabarito a partir de
      `goldenset_offsets.csv`; nenhum id literal no código).
- [x] Cada tabela carrega, não tem chave duplicada e cobre as classes/leis vistas na amostra.

**Pronto quando:** os 96 `real` resolvem para o `id` certo e nenhum registro pega número de precedente.

---

### Frente B — Texto e extração (`src/verificador/texto/`, `extracao/`)

**Responsável:** ____ (B1: ____ · B2: ____) · **Branch:** `frente-b-extracao` · **Depende de:** `contratos.py`;
tabela de confusões de OCR e de classes (frente A) — pode começar com listas provisórias
**Requisitos:** R1–R4, R33–R36, R38 · ADR-003, ADR-005 · **Entrega:** `preparar`, `extrair`, `ler_campos`

**Status: ✅ concluída** pelo colega (commit `b893496`). Revisão em 2026-09-18 achou 4 problemas reais, já corrigidos
na `main`: ramo TST (`AIRR`/`RRAG`/`ROT`/`IRR`/`AgInt` lidos como `RR`, `EDcl`→`EDCL`), siglas `ED`×`EDcl` e
`AREspEl`×`AREsp` diferentes do índice, UF espúria `RR` no TST e `NameError` latente. Ida e volta do TST: 51% → 100%.
**Lacunas de recall conhecidas (não corrigidas; medir/tratar depois):** moldes novos da forma (d), siglas só por
extenso (`EIN`, `MS`, `ROE`, `SLS`, `AP`, `AC`), `Súmula n. 83 do STJ`, OCR no 1º dígito de um grupo (`l.272.322`).

**Contexto.** É a frente que decide o **recall**: citação que não é achada não pode ser classificada. Cada span
tem que bater com `texto[inicio:fim]` no texto **original**, mesmo depois de normalizar OCR.

#### B1 — Texto: cabeçalho, normalização e mapa (`texto/`)

- [x] **Leitura do `.txt`**: UTF-8, sem tradução de quebra de linha (os arquivos não têm BOM nem `\r`).
- [x] **Delimitar o cabeçalho** (R34): bloco inicial (órgão, número dos autos, partes, relator, protocolo) até o
      primeiro parágrafo corrido → `corpo_inicio`. Heurística com critério claro e documentado.
- [x] **Normalização com mapa de offsets** (ADR-003), sem alterar o original:
  - [x] quebra de linha → espaço;
  - [x] `n°` / `No` / `n.` / `N.` → `nº`;
  - [x] travessões (`–`, `—`) → `-`;
  - [x] espaços/pontos/quebras **dentro** de números colapsados;
  - [x] troca letra→dígito **só dentro de token numérico** (`21737l8` → `2173718`);
  - [x] `5úmula` → `Súmula`.
  - Toda troca que muda o tamanho registra o deslocamento no `mapa` (posição normalizada → posição original).
- [x] `preparar(texto) -> TextoPreparado(original, corpo_inicio, normalizado, mapa)`.
- [x] Função utilitária `voltar_ao_original(t, ini_norm, fim_norm) -> (inicio, fim)` — **toda** saída de span
      passa por ela.

**Testes B1**

- [x] **Teste do mapa**: para cada um dos 192 trechos do gabarito, o span reconstruído pelo mapa bate com
      `texto[inicio:fim]` (R38).
- [x] Nenhum dos **43 números de cabeçalho** cai fora de `corpo_inicio` como candidato (R34).
- [x] Propriedade: normalizar e voltar ao original nunca produz offset fora do texto nem `inicio > fim`.
- [x] Casos de borda: texto vazio, sem cabeçalho detectável, citação colada ao fim do arquivo.

#### B2 — Regex das 4 formas e leitura de campos (`extracao/`)

Rodam sobre o **corpo normalizado** (ADR-005, R33).

- [x] **(a) `com_numero`**: `[cadeia de recursos] classe + nº? + número [+ /UF]` —
      `AgInt no AREsp nº 1.996.496/RJ`, `AgInt 7557430-50.2018.7.00.0000/DF`.
- [x] **(b) `sumula`**: `Súmula [Vinculante] + número [+ do tribunal]` — `Súmula 211 do STJ`.
- [x] **(c) `lei_artigo`**: `art.`/`artigo` + número [+ inciso/§/alínea] + `da`/`do` + identificador de lei —
      `art. 896, § 1º-A, da CLT`, `art. 93, IX, da Constituição da República`.
- [x] **(d) `sem_numero`**: (`julgado`/`precedente`/`acórdão` do TRIBUNAL | CLASSE [do TRIBUNAL]) + ano +
      (`relatoria de`/`Rel. Min.`) + nome — `julgado do STF proferido em 2024 pela relatoria de Dias Toffoli`.
- [x] **Delimitação do span**: o span deve cobrir exatamente o que o gabarito cobre (IoU ≥ 0,5 — R4). Estudar
      onde o gabarito começa e termina em cada forma (ex.: inclui `julgado do`? inclui `/UF`?).
- [x] **Resolução de sobreposição** (R3): IoU ≥ 0,5 entre candidatas → fica uma só (mais específica > presente
      nas duas fontes > mais longa; contida em outra → descartada). **O `kaggle_metric.py` rejeita a submissão
      inteira se houver duas citações com IoU ≥ 0,5.**
- [x] **Referência vaga desligada** (ADR-005): `extrair_referencia_vaga = false` por padrão; o detector existe
      atrás da chave de `configuracao.py`.
- [x] **Leitura de campos por regras** (`ler_campos`): tribunal, classe principal, cadeia de recursos, número
      (só dígitos; `correcao_ocr=True` se houve troca letra→dígito), UF, ano, relator normalizado, `lei_chave`,
      `artigo` (**sem** inciso/§/alínea — R36). Retorna `None` quando não consegue o que a forma exige →
      candidata vai para a fila de difíceis.
- [x] **Registrar `padrao`** (nome do padrão) em cada `Candidata` — alimenta o rastro e a análise de erro.
- [x] Documentar o que **fica fora** por decisão: artigo sem lei, súmula sem número, temas de repercussão
      geral, citações no plural (`arts. 489 e 1.022 do CPC` — sem decisão se viram 1 ou 2 spans; anotar como
      débito conhecido).

**Testes B2**

- [x] **Recall de spans**: para cada citação do gabarito existe um span emitido com IoU ≥ 0,5; reportar
      recall por forma e por nível.
- [x] **R4**: nenhum span emitido cruza citação do gabarito com IoU < 0,5.
- [x] **R3**: nenhum par de spans no mesmo documento com IoU ≥ 0,5.
- [x] **R33**: nenhuma referência vaga conhecida da amostra vira candidata.
- [x] **R36**: mesma classe e mesmo `artigo` com e sem inciso/§ (teste com pares).
- [x] Um teste por padrão regex, com exemplos positivos **e** negativos.

**Pronto quando:** os 192 trechos batem com `texto[inicio:fim]`, R3 e R4 passam na amostra, nenhum dos 43 números
de cabeçalho é extraído, e o recall de spans por IoU ≥ 0,5 está medido e registrado.

---

### Frente C — Avaliação, dados e saída (`avaliacao/`, `sintetico/`, `saida/`, `cli.py`)

**Responsável:** ____ · **Branch:** `frente-c-avaliacao` · **Depende de:** só de `contratos.py` e do
`kaggle_metric.py`
**Requisitos:** R15–R19, R26, R28, R31, R35, R38, R40–R43, R49 · ADR-009, ADR-012 · **Entrega:** `escrever_json`,
relatório comparativo, divisão ajuste/controle, gerador por código

**Status: ✅ concluída em 2026-09-18** (implementada na `main`, sem commit; 92 testes na entrega, 130 hoje). Onde ficou o código:
`saida/` (escrever + validar), `avaliacao/` (divisão, relatório, rastro, comparar, determinismo, solution),
`sintetico/` (ruído, verdade, moldes, citações, gerador, formato); `cli.py` ganhou `avaliar --conjunto`, `comparar`,
`gerar-sintetico` e `submeter --criar-tag`. Desvio do DESIGN: `avaliacao/` e `sintetico/` ficam **dentro** de
`src/verificador/` (para o pacote instalar no notebook). O rastro tem a máquina pronta, mas só é preenchido quando o
`rodar` real existir (Fase 2). O gerador mede hoje: recall de spans da extração de 85,7% (nível 1) e 81,3% (nível 2).

**Contexto.** Com 26 documentos e poucos moldes de frase, é fácil "decorar" a amostra e tirar ~1,1 no
leaderboard sem generalizar (ADR-009). Esta frente cria o **instrumento de medida honesto** e o material que
depois treina o encoder.

**Tarefas — saída e execução**

- [x] **`escrever_json(documento_id, list[CitacaoVerificada], pasta)`**: grava `<documento_id>.json` no contrato
      (R15): `inicio`/`fim` inteiros, `trecho == texto[inicio:fim]` (R38), `tipo` = `lei` só para forma (c)
      (R42), `resolucao.id_canonico` **só** em `real` (R13), `confianca` em [0,1] quando emitida.
- [x] **Validador de saída** (`saida/validar.py`): antes de converter, checa R3, R13, R38, R42 e levanta erro
      claro — evita gastar uma submissão à toa (o `kaggle_metric.py` rejeita a submissão inteira por R3).
- [x] **Rastro por citação** (`runs/<run_id>/rastro.jsonl`): `padrao`, `origem` (regex/encoder), `caminho`,
      `candidatos`, `fonte` dos campos, `correcao_ocr`. É o insumo da análise de erro.
- [x] **`submeter` completo** (R31): recusar árvore suja; registrar no manifesto commit, revisões dos modelos e
      versão do ambiente; **criar a tag `sub-NNN`** de verdade; recusar se duas execuções do mesmo comando não
      derem CSV idêntico (R49) — substitui o `TODO(R49)` que existe hoje em `cli.py`.

**Tarefas — avaliação**

- [x] **Divisão fixa da amostra** em *ajuste* e *controle*, estratificada por nível, gravada em arquivo
      **versionado** (`avaliacao/divisao.json`). Nunca embaralhar de novo depois de decidida (ADR-009).
- [x] **Relatório por execução** (R28): score, F1 por classe, τ e Brier, **por nível**, calculados pelo
      `kaggle_metric.py` (não reimplementar), separando *ajuste*, *controle* e sintético.
- [x] **Comparador de execuções**: `verificador comparar --run A --run B` → diferença de score/F1/τ, e lista de
      citações cujo resultado mudou.
- [x] **Lista de erros**: citações do gabarito não casadas (recall) e citações emitidas sem par (precisão), com
      trecho, caminho e classe esperada × obtida.
- [x] **Teste de determinismo**: rodar duas vezes, comparar byte a byte (R49).
- [x] **Teste de troca de nomes** (R41): renomear os `.txt`/`documento_id` e conferir que a saída é a mesma.
- [x] **Teste de literais** (R43): varrer `src/` e falhar se aparecer `id_canonico`, `documento_id` ou trecho de
      citação da amostra.

**Tarefas — gerador sintético por código (`sintetico/`, sem LLM ainda)**

- [x] Gerador com **semente fixa** que escolhe citações reais da base e produz o gabarito junto:
  - [x] `real`: citação correta de um registro da base;
  - [x] `inventada` por número inexistente;
  - [x] `inventada` por **número emprestado** (número existente com UF ou classe trocada) — exercita o caminho
        `numero_contradito` (R40), que **não ocorre na amostra**;
  - [x] `inventada` por artigo inexistente de lei conhecida;
  - [x] `incompleta` por forma (d), e por número que casa vários registros (R7, hoje só 1 caso na amostra).
- [x] **Ruído de OCR** controlado (letra↔dígito dentro de número, espaço/ponto/quebra dentro de número,
      variação de `nº` e travessão), gerando **pares limpo × ruidoso** (R35).
- [x] **Vários moldes de frase**, escritos por quem **não** escreveu os regex (ADR-012, mitigação) — combinar
      com a frente B para não haver viés de "gerador feito sob medida para o extrator".
- [x] Formato de saída idêntico ao do gabarito da amostra, para o `avaliar` consumir sem adaptação.
- [x] Reservar uma **fatia de controle** que nunca é usada em treino.

**Testes C**

- [x] `escrever_json` → `json_to_submission.py` → CSV → `avaliar` sem `ParticipantVisibleError` (teste fim a fim).
- [x] Validador rejeita: sobreposição IoU ≥ 0,5, `id_canonico` em não-`real`, `trecho` ≠ `texto[inicio:fim]`,
      `tipo` errado.
- [x] Gerador: mesma semente → mesmo dataset (byte a byte); gabarito sintético passa no `avaliar` com nota 1,0
      quando a "predição" é o próprio gabarito.

**Pronto quando:** toda execução gera manifesto, relatório (R28), rastro e erros; o gerador produz pares
limpo × ruidoso e números emprestados; `submeter` cumpre R31; testes R41, R43 e R49 existem.

---

### Frente D — Decisão, confiança e (depois) LLM (`decisao/`)

**Responsável:** ____ · **Branch:** `frente-d-decisao` · **Depende de:** só de `contratos.py` (usa `Campos` e
`RegistroIndice` **falsos** até A e B entregarem os reais)
**Requisitos:** R5–R9, R12–R14, R26, R36, R40, R47, R48 · ADR-006, ADR-007, ADR-008 · **Entrega:**
`decidir(campos, forma, indice) -> Resolucao`

**Status: ✅ concluída em 2026-09-18** (na `main`, sem commit). `decisao/` com os 10 caminhos + `campos_nao_lidos` (11º,
emitido só pela integração), filtro do ADR-007, guarda R14 e a conferência R48 do LLM (interface pronta, LLM não existe).
26 testes em `tests/test_decisao.py`. Decisões suas: classe do TST elimina como nas outras cortes; campo não lido → `incompleta`.

**Contexto.** É a lógica que separa `real` de `inventada`. O erro caro é classificar `inventada` como `real`
(penalidade τ, que corta a nota). Regra de ouro (ADR-006): **na dúvida, nunca `real`**.

**Tarefas**

- [x] **Etapa 1 — Candidatos**: formas (a)/(b) → registros com o mesmo número reduzido a dígitos (súmula:
      `S…`/`SV…`, de qualquer tribunal); forma (c) → mesma lei canônica e mesmo artigo.
- [x] **Etapa 2 — Consistentes**: candidatos que nenhum atributo **explícito** contradiz, na ordem tribunal, UF,
      classe principal, cadeia de recursos. **Atributo ausente ou lido com correção de OCR não elimina ninguém.**
- [x] **Tabela de 10 caminhos** — exaustiva e disjunta, cada um com nome estável (`DESIGN.md`, [4]):

  | Caminho | Condição | Classe | id |
  |---|---|---|---|
  | `sem_numero` | forma (d) | incompleta | — |
  | `numero_ausente` | (a)/(b), 0 candidatos | inventada | — |
  | `numero_contradito` | (a)/(b), candidatos, 0 consistentes | inventada | — |
  | `numero_unico` | (a)/(b), 1 candidato consistente | real | `id` |
  | `numero_desempatado` | (a)/(b), N candidatos, 1 consistente | real | `id` |
  | `numero_ambiguo` | (a)/(b), N consistentes | incompleta | — |
  | `lei_apelido_desconhecido` | (c), identificador fora da tabela | inventada | — |
  | `lei_ausente` | (c), 0 candidatos | inventada | — |
  | `lei_unica` | (c), 1 candidato | real | `id` |
  | `lei_ambigua` | (c), N candidatos | incompleta | — |

- [x] **`Resolucao`** com `classificacao`, `id_canonico` (só em `real` — R12/R13), `caminho`, `candidatos`
      (para o rastro), `confianca` (inicialmente `None`).
- [x] **Desempate por classe processual** (ADR-007): documentar exatamente como a classe principal e a cadeia
      de recursos eliminam candidatos.
- [x] **Independência da origem dos campos**: o caminho não muda se os campos vieram de regras ou LLM; a
      origem só é registrada (para a confiança).
- [x] **Confiança (ADR-008)**: `confianca = taxa_acerto[caminho, correcao_ocr, fonte]`, lida de tabela gerada
      pela avaliação no conjunto de controle; menos de 5 ocorrências → taxa média da classe. **Só implementar
      depois da linha de base** (Fase 5) — antes disso, `confianca = None`.
- [x] **Preparar o leitor LLM** (ADR-013) só como *interface*: `ler_campos_llm(fila, llm)` retornando `None`
      por enquanto, e a **conferência R48** já implementada e testada (número do LLM só é aceito se os dígitos
      saem do trecho normalizado por trocas da tabela de OCR). Isso deixa o LLM plugável depois sem mexer na
      decisão.

**Testes D**

- [x] **Um teste por caminho** da tabela (10 testes), com `Campos` e `RegistroIndice` fabricados à mão.
- [x] **R36**: mesmo resultado com e sem inciso/§/alínea.
- [x] **R12/R13/R14**: `real` sempre tem `id`; não-`real` nunca tem; número da citação = número próprio do
      registro resolvido.
- [x] **τ = 0** em cenários fabricados de número emprestado (nenhum vira `real`).
- [x] **R48**: número do LLM com dígito inventado é rejeitado; número corrigível por tabela de OCR é aceito.
- [x] Propriedade: dado o mesmo `Campos` e índice, `decidir` é determinística.

**Pronto quando:** existe um teste por caminho; R36 passa; τ = 0 na amostra e no controle (quando a
integração existir); R48 testada.

---

## Fase 2 — Integração (24–25/09) · quem integra: ____ (sugestão: Roberto/frente D)

**Status: ✅ concluída em 2026-09-18.** `pipeline.py` + `cmd_rodar` de verdade (índice uma vez, rastro, manifesto com hashes
e tempos). Amostra: **score_final 0,9885, τ = 0, 192/192 spans**; sintético (100 pares): 0,8864, τ = 0. 130 testes verdes.
Achados na integração e corrigidos em B: UF `/RO`/`/RR` lida como classe; `no` de "Interno" lido como `nº`.


Um dia dedicado. Sem ele, cada frente fica "pronta sozinha" e nunca fecha.

- [x] Fazer merge dos PRs das 4 frentes em `main`, na ordem: contratos/CLI → A → B → D → C.
- [x] **Ligar o `rodar` real** em `cli.py`: `indexar → (por documento) preparar → extrair → ler_campos →
      decidir → escrever_json → json_to_submission → CSV`. Substitui o JSON vazio do esqueleto.
- [x] Resolver incompatibilidades de contrato descobertas na integração (registrar como ADR curto ou nota se
      mudar algo).
- [x] `pytest` inteiro verde; teste fim a fim com a amostra.
- [x] `avaliar` reporta score na amostra (ajuste + controle). Meta inicial do MVP (`DEFINE.md`): **96 reais
      resolvem para o id certo, τ = 0, nenhuma submissão rejeitada pelo `kaggle_metric.py`**.
- [x] Rodar duas vezes e conferir CSV idêntico (R49).

## Fase 3 — Linha de base e análise de erro (25/09)

**Status: 🟡 parcial.** Linha de base e análise de erro feitas: `docs/analise_erros_baseline.md`. **Pendente:** commit,
tag `sub-001`, notebook no Kaggle, envio da 1ª submissão e comparação local × leaderboard (ações humanas / autorização).


- [ ] **Tag `sub-001`** no commit da versão só-regras (nunca `main` em execução oficial — `docs/guia_kaggle.md`).
      *2026-09-21:* `sub-001` (f04ee55) é a versão só-regras **sem** confiança nem causas 2/3 e já está no remoto; a submissão
      real sai da **`sub-002`** (calibrador recalibrado com sintético; notebook `notebooks/kaggle/02_sub-002.ipynb`).
- [ ] Trocar `VERSAO = "main"` do notebook para a tag e rodar no Kaggle, gerando `submission.csv` no ambiente
      fixado.
- [ ] **Primeira submissão real** (gasta uma do teto diário — decisão humana; `ação_humana_pendente.md`).
      Comparar o score do leaderboard com o local: **diferença indica erro de pipeline** e deve ser investigada
      *antes* de nova submissão (prática da equipe, ex-R29).
- [x] **Análise de erro** no conjunto de *ajuste*: classificar cada erro por causa (span mal delimitado, campo
      lido errado, tabela incompleta, regex ausente, cabeçalho). Priorizar por ganho de score.
- [x] Salvar esse relatório como **linha de base** de tudo que vem depois (encoder, LLM e confiança precisam
      *ganhar* dela no controle para entrar).
- [ ] Ciclo de correção: um ajuste por vez, sempre comparando `--run` novo × linha de base.

### 3.1 Próximos passos propostos após a linha de base (registrados em 2026-09-19, **não implementados**)

Resultado da linha de base e explicação das métricas em `resultado_primeira_rodada.md`; detalhe dos erros em
`docs/analise_erros_baseline.md`.

**(a) Antecipar a confiança calibrada (ADR-008) da Fase 5 para agora, antes da 1ª submissão.**

- *Por quê:* a nota máxima é 1,100 e os últimos 0,100 vêm só do bônus de calibração, que hoje não disputamos
  (`confianca = None` → `b = 0`). Na amostra, com confiança bem calibrada, a nota iria de ~0,99 para ~1,08. É o maior
  ganho disponível e **não depende de GPU, encoder nem LLM**: na ordem original ela vinha depois das Fases 4 e 5, que
  estão sob a regra de corte de 25/09, e seria cortada junto com elas.
- *O que já existe:* a linha de base e o `rastro.jsonl`, que grava o caminho de decisão de cada citação.
- [x] Gerar a tabela `taxa_acerto[caminho, correcao_ocr, fonte]` no **controle** (amostra-controle + sintético-controle);
      caminho com menos de 5 ocorrências usa a taxa média da classe. Tabela regenerada por código, nunca editada à mão.
- [x] Ligar a tabela no pipeline (`Resolucao.confianca`), com o hash dela no manifesto.
- [x] Conferir **R26**: o Brier no controle precisa ser menor que o de uma confiança constante; se não for, a
      confiança não é enviada.
- [ ] Quando o LLM entrar (Fase 5), só regenerar a tabela (ela já tem a dimensão `fonte`).

**(b) As 4 causas de perda de recall medidas no sintético** (173 de 994 citações não são achadas; na amostra, 0).
Todas são de **extração** (frente B): o que é achado é classificado sem erro. Tratar uma de cada vez, medindo em
`ajuste` + `sintético-treino` e só então conferindo no `controle` (ADR-009), sempre com `verificador comparar`.

| # | Causa | Citações perdidas | Ganho estimado | Onde | Risco |
|---|---|---|---|---|---|
| 1 | Forma (d) com moldes de frase novos (`julgado da Corte (TSE, 2015, Min. X)`, `decisão colegiada do STM em 2025, relatada pelo Ministro X`) | 36 por versão (72 nos pares) | +7,2 pts de recall | `extracao/padroes.py` ou **encoder NER** (Fase 4) | Alto com regex (falso positivo); é o caso de uso do encoder |
| 2 | Classe escrita só por sigla que a tabela não tem (`EIN`, `MS`, `ROE`, `CJ`, `SLS`, `CautInom`, `LT`, `DCG`, `AP`, `AC`) | 31 por versão | +6,2 pts | `tabelas/classes.json` | Baixo; `AC`/`AP`/`MS` colidem com UF (já protegido: a classe só é lida antes do número) |
| 3 | Súmula com `n.`/`nº` (`Súmula n. 83 do STJ`; a própria base escreve assim) | 10 por versão | +2,0 pts | `extracao/padroes.py` (`_compilar_sumula`) | Baixo |
| 4 | OCR no **primeiro** dígito de um grupo ou letra + espaço dentro do número (`art. l.239`, `Rcl n. 7I. 346/SP`) | 19 (só na versão ruidosa) | +3,8 pts no nível 2 | `texto/normalizacao.py` | Médio (mexe no mapa de offsets) |

- [x] Causa 3 (mais barata e mais confiável como problema real).
- [x] Causa 2.
- [x] **Resíduo da causa 2** (2026-09-21): a sigla solta `CorPar` ficara de fora da tabela (+6); o hífen como
      conector antes de número CNJ (`DCG-1340-…`, +2); e número curto com marcador `nº` obrigatório
      (`CautInom nº 87`, +2). Detalhe em `resultado_submissoes.md`.
- [x] **Causa 4** (2026-09-21, +19): implementada **em paralelo** pela Beatriz (`46edf70`) e pelo Roberto
      (`da571f1`); o merge ficou com a ordenação dela e a regra de grupo dele. Eram dois defeitos em
      `texto/normalizacao.py`. (1) A troca letra→dígito rodava **depois** da limpeza de espaço, que exige
      dígito dos dois lados — em `7I. 346` o `I` só virava `1` tarde demais; resolvido movendo o OCR para
      antes de colapsar hífen e espaço, o que também evita `21737l8 - SP` colar a UF no token. (2) A regra
      olhava o caractere colado, então o `l` de `l.239` (encostado no ponto) escapava; resolvido decidindo
      por **grupo** entre separadores, o que evita o erro oposto — em `1.111.222-GO` a UF não vira `90`.
      Medições: +14 spans de nível 2 (`sint-pre-c4` → `sint-c4`, score +0,010) e +19 no conjunto com os
      moldes de estresse; amostra e controle oficiais inalterados, 0 espúrios nos dois casos.
- [x] **Causa 1** (2026-09-21): resolvida **por regex ancorado, sem encoder**. O padrão da forma (d) transcrevia
      as quatro conjunções da amostra e cegava quando a ligação mudava; passou a ancorar nos invariantes das 31
      citações reais (gatilho, tribunal, ano, marcador de relator, nome), com preenchimento genérico entre elas e
      **proibição de literal de conjunção** — restrição auditável que impede decorar molde. `campos.py::_RELATOR`
      tinha o mesmo defeito e foi corrigido junto. Decisão em `ADR-015`, detalhe e números em
      `specs/forma_d_ancorada.md`. Sintético: recall 922/994 → **988/994**, score 1,0394 → **1,0957**, com 10
      moldes de estresse novos no gerador. Amostra intacta em 192/192.
- [ ] **Fase 4 / encoder — decisão informada:** pelo limiar do ADR-015 o resultado é o **desfecho A** (só regex).
      As âncoras cobrem 9 dos 10 moldes que nunca viram, mantendo precisão 1,0, sem GPU nem publicação de pesos.
      O encoder fica disponível como ADR-011 se aparecer evidência de ligação fora deste repertório.

> Ressalva: os moldes do gerador sintético foram escritos por quem implementou a análise; a frequência real dessas
> formas no conjunto final é desconhecida (ADR-012). A causa 3 é a mais segura; a causa 1 é a mais incerta.

---

### 3.2 Recuperar e ultrapassar o score, depois das correções de 21/09 (registrado em 2026-09-22)

**Por que esta seção existe.** A sequência de correções do dia 21 subiu a nota e depois devolveu parte
dela. O histórico, na amostra oficial:

| Momento | Commit | Amostra | Controle | O que mudou |
|---|---|---|---|---|
| Antes | `f8c885d` | 1,08603 | 1,07923 | — |
| `EDv` em `classes.json` | `7b3ea35` | **1,09648** | **1,10000** | fechou o `gen_n2_010` |
| Padrão solto do `EDv` removido | `acffa34` | 1,09648 | 1,10000 | neutro; tirou risco de falso positivo |
| **Parser do TST corrigido** | `c83159d` | **1,09272** ⬇ | 1,10000 | **−0,0038 na amostra** |

A queda do último passo é **deliberada e aceita**. O parser do TST tentava o rodapé `PROCESSO Nº TST-…`
antes da fórmula `estes autos de …`, e o rodapé aparece dentro de decisões transcritas: **20 dos 199
registros do TST reivindicavam número de processo que apenas citavam**. Corrigir isso deixou o
`gen_n2_005` sem o candidato espúrio que fazia a classe casar por acaso, e o R40 passou a devolver
`inventada`. Ou seja: a citação estava certa pelo motivo errado, e a nota da amostra pagou por isso.

O **controle continua em 1,10000** (teto exato) e o sintético em 1,09574 — o que sustenta a decisão:
o que conta é o conjunto cego, e lá cada registro mal numerado custa nos dois sentidos.

Contexto e números: `docs/gerais/limites_de_decisao.md` (seções 13 a 16), `specs/edv_padrao_solto.md`,
`ADR-005` (revisão de 21/09).

**O enquadramento desta fase.** Tudo que conseguimos medir está saturado — amostra 192/192, controle
no teto, sintético 988/994, precisão 1,0 e τ=0 em tudo. A pergunta deixou de ser "como melhorar o que
medimos" e passou a ser **"como aumentar o esperado num conjunto que não vemos"**. Isso se divide em
fechar lacunas que a organização documentou e construir um instrumento de medida honesto.

#### Tier 1 — lacunas com evidência direta na página Data

- [x] **OCR dentro de palavras (`m↔rn`).** A página lista o ruído do nível 2 como `0↔O, 1↔l, 5↔S,
      **m↔rn**`. Nossa tabela é **só letra→dígito dentro de número**; corrupção de palavra tem um único
      caso tratado, hardcoded (`5úmula → Súmula`). Se o cego trouxer `Reclarnação`, `Súrnula` ou
      `rninistro`, a citação se perde inteira — e o nível 2 pesa 2×. Zero ocorrências na amostra
      significa que nunca fomos testados nisso.
      **Projeto obrigatório:** `rn→m` cego é perigoso (`interno` viraria `intemo`, e `AgInt` é *Agravo
      **Interno***). Tem de ser **correção contra vocabulário fechado** — só troca se o resultado casar
      com termo conhecido (classe, `Súmula`, `Ministro`, `Tribunal`). Mesmo princípio do ADR-015:
      âncora, não vocabulário solto. **Custo baixo, é o item com ganho plausível mais direto.**
      *2026-09-22, feito pelo Caio* — `tabelas/vocabulario_ocr.json` (31 âncoras) + correção em
      `texto/normalizacao.py`, com o ruído `m↔rn` acrescentado ao gerador para tornar o item
      **mensurável** (não havia como medir: nenhum conjunto nosso continha esse ruído). Corpus de
      estresse: recall 0,9406 → **0,9940**, precisão 0,9936 → **1,0000**, score 1,04616 → **1,09574**
      (controle 1,03197 → **1,08530**). Amostra intacta em 1,092719 e 192/192; τ = 0; R49 verde;
      181 testes. Dois defeitos achados no caminho: o mapa de offsets truncava a cauda da palavra
      encurtada, e o vocabulário nascera sem `MS`, `RMS`, `CPM` e `consumidor` — agora há teste que
      acusa a lacuna sozinho. Detalhe em `docs/gerais/feat-verificar-ocr-caio.md`.
- [x] **Invariante a partir da garantia do organizador.** A página afirma: *"todo ruído aplicado a uma
      citação real é recuperável por normalização; um dígito nunca é trocado por outro dígito"*. Logo,
      **toda citação `real` do gabarito que caia em `numero_ausente` é bug nosso, sempre**. Vira teste.
      *2026-09-22, feito pelo Roberto* — dois testes de regressão em `tests/test_pipeline.py`
      (`test_amostra_toda_real_nunca_cai_em_numero_ausente`, `test_sintetico_toda_real_nunca_cai_em_numero_ausente`),
      cruzando o gabarito `real` (por IoU, via `_correspondencia_por_iou`) com o caminho gravado no
      `rastro.jsonl`. Registrado como `R50` em `specs/DESIGN.md`. Passou sem nenhuma correção de
      código: a garantia já era estrutural no gerador e na normalização (`tabelas/ocr.json` só mapeia
      letra→dígito, `_ocr_no_token` preserva todo dígito existente) — o valor do item é travar
      regressão futura e o conjunto cego, não corrigir nada hoje. Spec completa em
      `specs/invariante_real_nunca_numero_ausente.md`. 190 testes verdes.

#### Tier 2 — o instrumento de medida (pré-requisito do que é caro)

- [x] **LeNER-Br como sonda externa de recall.** Texto jurídico brasileiro real, público, com entidades
      `JURISPRUDENCIA`. Não é pontuável contra o nosso gabarito (convenção diferente), mas responde à
      única pergunta que importa: *em texto que ninguém da equipe escreveu, quantas referências a
      julgados nossos padrões deixam passar?* Barato, sem GPU, e é a **única evidência externa
      disponível**.
      *2026-09-22, feito pelo Roberto* — `tests/test_lener_br.py` + `tests/lener_br_helpers.py`
      (parser CoNLL/IOB próprio, alinha token→offset contra `raw_text/`, sem depender de nada do
      pacote `verificador` além do parser em si). Roda só `preparar()`+`extrair()` — extração de
      spans não depende de índice/base. **Resultado: recall de 47,4% (692/1461)** nas 70 entidades
      `JURISPRUDENCIA` do dataset — bem abaixo dos ~99% medidos na amostra/sintético, exatamente o
      tipo de sinal que a sonda deveria pegar. Investigado um dos piores casos (0/39,
      `ACORDAOTCU25052016`) pra descartar bug de parsing: é achado genuíno, não bug — são citações
      no formato do **TCU** (`"Acórdão nº 1.160/2016-TCU-Plenário"`, `"TC 001.396/97-8"`), tribunal
      fora do escopo do desafio (que cobre só STF/STJ/STM/TSE/TST), então nossos padrões nunca
      foram desenhados pra reconhecer. Não é regressão nem exige ação — é o retrato honesto do que
      "generalização" significa fora da nossa própria bolha de moldes. Dataset baixado local
      (`lener-br/`, `.gitignore`), licença registrada em `docs/gerais/conformidade_dados_externos.md`
      (achado 2 — MIT no repo, "unknown" no card do HF; uso como sonda interna é de baixo risco).
- [x] **LLM diversificando o sintético (ADR-012, item já previsto na Fase 4).** Não melhora o sistema,
      melhora a **medida**. Os moldes do sintético são nossos, então toda afirmação de generalização é
      circular — inclusive a de que as âncoras cobrem "9 de 10 moldes novos". **Precisa vir antes do
      encoder:** com recall em 99,4%, não há margem mensurável para o encoder mostrar ganho.
      *2026-09-22, notebook preparado pelo Roberto, não executado* — `notebooks/kaggle/05_llm_diversifica_sintetico.ipynb`,
      modelo **Qwen2.5-7B-Instruct** (Apache 2.0, ~15GB VRAM, decodificação determinística). Precisa
      rodar no Kaggle (GPU) e publicar no Hugging Face — nenhuma das duas coisas é possível neste
      ambiente. Ver `docs/gerais/conformidade_dados_externos.md` (achado 3, licenças consideradas).
      *2026-09-24, executado e publicado pelo Roberto* — a 1ª execução no Kaggle deu recall 974/994, mas
      a queda era artefato do notebook: o corte da sentença incluía o espaço anterior e o `strip()` da
      resposta colava as frases ("ponto.De acordo…", 864 vezes, e metade das perdas caía ali), e o Qwen
      respondeu em chinês em 18 documentos. Corrigido no commit `379714d` (célula 7: sentença sem as
      bordas, com teste de "LLM identidade" reproduzindo a base byte a byte; rejeição de escrita não
      latina) e executado de novo: **982/994 sentenças reescritas** (10 rejeitadas por marcador, 2 por
      escrita), 0 frases coladas, 0 chinês. **Resultado: score 1,0989, recall 992/994, precisão 1,0,
      τ = 0; controle 1,1000** (camada 1: 1,0957, 988/994). Reproduzido localmente, `submission` e
      `relatorio` idênticos aos do Kaggle. O LLM mudou as 3 palavras antes da citação em 95% dos casos,
      então a medida é forte: **o fraseado que o time não escreveu não derruba o recall**. Única perda:
      `Invoca-se, ainda, o disposto em ROT n° 7000804-…` (inventada, n1 e n2). Ressalva: a decodificação
      gulosa convergiu para 42 contextos de duas palavras antes da citação, então isto é uma segunda
      "voz", não qualquer redação. **Consequência:** com 992/994, a margem mensurável para o encoder
      mostrar ganho no sintético ficou ainda menor. Publicado em
      [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado)
      (MIT), com a camada 1 em `base/`. **Revisão fixa: `0209a853e6e59b263b138200963b579105baca24`.**

#### Tier 3 — opção, não melhoria

- [x] **Detector de referência vaga, implementado e desligado.** Valor esperado **zero** sozinho: é
      cara ou coroa, ~0,046 para cada lado. O `verificador.toml` já tem `extrair_referencia_vaga`, mas
      `extracao/__init__.py` **ignorava a flag** (`del cfg`), então não dava para ligar nem sabendo a
      resposta. Construí-lo desligado compra o direito de decidir na fase 2, com o leaderboard público
      de 40% como árbitro. **Seguro barato, não melhoria.** Ver `ADR-005`.
      *2026-09-23, feito pelo Roberto* — 5ª forma opcional (`referencia_vaga`), vocabulário fechado
      em `tabelas/referencia_vaga.json` (5 frases já validadas pelo teste R33 e pela página Data,
      ADR-015: âncora, não vocabulário solto), nunca consulta o índice, sempre `incompleta`
      (`decisao/decidir.py`, `decisao/caminhos.py` — novo caminho `REFERENCIA_VAGA`, 12º da tabela).
      `extracao/__init__.py:50-51` liga a forma só quando `cfg.extrair_referencia_vaga` for `True`;
      com a flag desligada (default), o comportamento é **byte-idêntico** ao de antes — confirmado
      rodando a amostra oficial (1,100000, sem mudança) e os 194 testes (`test_r33_...`,
      `test_forma_d_exige_ano_e_relator_...` inalterados). Dois testes novos em `test_extracao.py`
      confirmam o oposto com a flag ligada. **Medido, não só estimado:** ligar contra o gabarito
      distribuído hoje (192 citações, sem anotação de referência vaga) custa **11 espúrios e
      −0,049 de score** (1,100000 → 1,051146) — bate quase exato com a estimativa antiga de ~0,046.
      **Continua desligado por padrão.** A decisão de ligar ou não é da Fase 2, quando o leaderboard
      público (40% do conjunto cego) der sinal real de qual lado do ADR-005 é o certo — não decidir
      às cegas agora. Revisitar este item assim que esse sinal existir.

#### O que foi avaliado e descartado

| Ideia | Razão |
|---|---|
| Cross-encoder para desempate entre candidatos | A página diz que as duplicatas do acervo **não têm citação apontando para elas** |
| Auditar duplicatas do acervo | Mesma razão — restam 73 grupos indistinguíveis, todos inofensivos |
| Melhorar a calibração da confiança | `b` já está em 0,0999 de um teto de 0,10 |
| Perseguir o link do `gen_n2_005` | Evidência n=1; cai no ADR-009 |
| Leitor LLM de campos (ADR-013) | Zero casos de `ler_campos → None` hoje |

#### Ordem sugerida, com o prazo

Restam ~7 dias úteis (Fase 6 ocupa 29–30/09). Os três primeiros cabem folgados; o quarto e o quinto
dependem de quanto da semana se quer apostar.

1. OCR em palavras com vocabulário fechado  2. LeNER-Br como sonda  3. Detector desligado
4. LLM diversificando o sintético  5. Encoder — **só se o item 4 mostrar margem**

#### Ajustes pequenos registrados em 2026-09-24 — **não seguir por enquanto**

Decisão do Roberto: ficam anotados, sem execução, até a decisão sobre o encoder (Fase 4).

- [ ] **Perda residual do sintético diversificado:** `Invoca-se, ainda, o disposto em ROT n° 7000804-…`
      (inventada, n1 e n2), a única citação perdida em 992/994. Provável relação com o achado de 24/09
      de que `ROT`, `IRR` e `RRAG` só são extraídas no formato com hífen (`RRAG-…`); com espaço
      (`ROT n° …`, `IRR 243-51…`) não saem. São 26 acórdãos do TST no acervo. Só entra se amostra e
      controle não piorarem.
- [x] **Suavização da calibração** (`taxa = (acertos + α·m)/(n + α)`). Já estava feita depois da
      `sub-004`: `avaliacao/calibrar.py` com `ALFA = 7` e `PRIOR = 0.97`, R26 conferido por caminho.
      É a única diferença de saída entre `sub-004` e `sub-005` (confiança 1,0000 → 0,9993; spans,
      classes e ids idênticos na amostra).
- [ ] **Detector de referência vaga:** continua desligado. A decisão é da fase 2, com o sinal do
      leaderboard público (ver Tier 3).


      - essas alterações so fazem sentido se trouxerem um ganho real para o sistema, e nao ficarem so gastando espaço e poder computacional.

---

## Fase 4 — Encoder NER e sintético com LLM (25–28/09) · **Testar em cima dos docs de LeNER-BR pra testar ganho de recall que justifica o uso do encoder**

> **Risco de prazo.** É a etapa que mais pode estourar (GPU do Kaggle com cota compartilhada de ~30 h/semana
> por conta, treino, publicação). O sistema já prevê `usar_encoder=false` e `usar_llm=false`; se não der tempo,
> a submissão final é só-regras e continua válida. **Decidir em 25/09 se esta fase começa.**

**Responsável:** ____ (sugestão: frente C, que já tem o gerador) · **ADR:** 011, 012

### Decisão de 2026-09-24: encoder como rede de segurança, com prazo fixo e teste no LeNER-Br

**Status:** registrado, ainda não iniciado. Conversa Roberto × Claude em 24/09, depois da `sub-005`.

**Por que o encoder volta à mesa, apesar de amostra, controle e sintético saturados.** O 992/994 do
sintético diversificado só testou o **contexto em volta** da citação: o trecho ia ao LLM como marcador
e voltava byte a byte. **A superfície da citação nunca foi testada fora dos nossos moldes.** O
LeNER-Br, filtrado para o escopo do desafio, mostra que é aí que está o risco:

| LeNER-Br (todas as divisões) | Recall do regex |
|---|---|
| Fora do escopo (TCU, TJ, TRF, TRT) | 2% (esperado, não conta) |
| Citações com número de STF, STJ, TST, TSE e STM (457) | 57,5% achadas · 9,4% com borda diferente · 33% não detectadas |

Lacunas confirmadas direto no extrator, todas de superfície e não de frase nova:

| Lacuna | Exemplo que falha |
|---|---|
| Hífen entre classe e número | `MS-27350/DF`, `TST-RR-578.030/99.5` |
| Classes do acervo escritas com espaço | `ROT n° 7000804-…`, `IRR 243-51…` (o acervo tem **26 acórdãos RRAG, ROT e IRR**, que só saem no formato `RRAG-…`) |
| Formas de súmula | `Súmula n.º 691 do STF`, `Enunciado n° 279 da Súmula do STF`, `Súmulas 219 e 329 do TST` |
| Tribunal por extenso depois da súmula | `Súmula nº 83 do colendo Superior Tribunal de Justiça` sai só `Súmula nº 83`: IoU < 0,5 e o tribunal se perde |
| Classes fora do acervo | `EREsp`, `ARE` / `Recurso Extraordinário com Agravo` |

**Ressalva:** o LeNER-Br é texto real; o conjunto final é gerado pelo organizador com "o mesmo formato,
os mesmos níveis e distribuição de classes equivalente" (a amostra escreve o TST sempre como
`TST-RR-…`). O risco real fica entre os dois números.

**Por que o encoder não é "garantia máxima de recall".** Ele só acha o que os dados de treino ensinam.
O sintético usa o nosso vocabulário (o encoder tende a imitar o regex); o LeNER-Br tem 70 documentos e
outra convenção (marca "STF" sozinho, inclui TCU/TJ); a amostra é o que medimos. O ganho real é
generalizar pelo **formato** (`SIGLA nº 123.456/UF` em contexto de citação, mesmo com sigla nova). Os
custos são falso positivo nos distratores (autos, protocolo, OAB, fls.), classe desconhecida que o
`ler_campos` não lê, publicação dos pesos até 30/09 e determinismo (R49). Por isso: **rede de
segurança, não extrator principal**.

#### Modelos preferidos (licença conferida na API do HF em 24/09 — regra 6c exige OSI)

**Escolha registrada em 2026-09-24 (Roberto): BERTimbau-base é o principal.** A ordem anterior punha o
Legal-BERTimbau em 1º; ela mudou depois do levantamento abaixo.

| Ordem | Modelo | Licença | Nota |
|---|---|---|---|
| **principal** | **BERTimbau-base** (`neuralmind/bert-base-portuguese-cased` @ `94d69c95f98f7d5b2a8700c420230ae10def0baa`) | MIT | F1 0,889 ± 0,009 no LeNER-Br; distingue maiúsculas; 110M, leve em CPU |
| comparação | Legal-BERTimbau-base (`rufimelo/Legal-BERTimbau-base` @ `c75cd428bb28c620369823950fcca3a6f2c2611c`) | MIT | Mesmo tokenizador e arquitetura: treina no mesmo notebook trocando só o nome |
| reserva | BERTomelo-ModernBERT-Base (`unb-labia/BERTomelo-ModernBERT-Base-v1`) | Apache 2.0 | F1 0,899 ± 0,010, mas o tokenizador converte tudo para minúsculas |
| reserva | GLiNER multi v2.1 (`urchade/gliner_multi-v2.1`) | Apache 2.0 | Zero-shot, sem avaliação jurídica conhecida |
| descartado | BERTomelo-Large, BERTimbau-large, XLM-R | Apache/MIT | Large não ganha do Base no LeNER-Br (0,892) e custa ~3×; XLM-R funde número e pontuação num token só (`-27`, `9.5`) |
| **fora** | Albertina-900M | "other" | Licença não OSI na tag do HF |
| **fora** | RoBERTaLexPT, RoBERTaCrawlPT, `dominguesm/legal-bert-ner-base-cased-ptbr` | CC BY 4.0 | Não é licença OSI |
| **fora** | `pierreguillou/ner-bert-*-lenerbr` | sem licença | Não pode redistribuir |

F1 no LeNER-Br: tabela do card do BERTomelo, mesmo protocolo, várias sementes. O número cobre todas as
entidades, não só jurisprudência. É indicador, não previsão.

**Por que a ordem mudou:**
- **Legal-BERTimbau é jurídico de Portugal.** O pré-treino continuado usou frases do Supremo Tribunal de
  Justiça português (`rufimelo/PortugueseLegalSentences-v0`), não do Brasil. O card tem erros (diz que a
  base é o BERTimbau Large) e não publica resultado de NER. O ganho de domínio para `REsp …/SP` ou
  `TST-RR-…` é incerto.
- **BERTomelo perde maiúsculas.** `MS` vira `m s` e `STF` vira `stf`, e maiúscula é sinal forte de
  sigla de classe. A vantagem de F1 dele cabe em um desvio. A janela de 1024 tokens também não evita
  janela deslizante: 8 dos 26 documentos da amostra passam de 1024.
- **Detalhe do BERTimbau:** o `º` de `n.º` vira `[UNK]` (110 vezes nos 26 documentos). Os offsets
  continuam corretos, só perde o sinal do caractere.

**Como decidir entre principal e comparação:** pelo `dev` do LeNER-Br e pelos controles (sintético e
amostra), **nunca pelo `test`**. O `dev` tem só 31 citações no escopo: se empatar, fica o BERTimbau.

Detalhe das licenças: `docs/gerais/conformidade_dados_externos.md`, achado 4.

#### Atividades, em ordem

- [ ] **1. Reforço do regex (25/09, ~1 dia).** Atacar as lacunas da tabela acima: hífen entre classe e
      número, `ROT`/`IRR`/`RRAG` com espaço, formas de súmula (`n.º`, "Enunciado … da Súmula", plural) e
      tribunal por extenso depois da súmula. Criar um conjunto de "variantes" como teste. Só entra se
      amostra, controle e sintético não piorarem e a precisão seguir 1,0. **Guiar as correções só pelas
      divisões `train` e `dev` do LeNER-Br** (ver protocolo abaixo).
- [ ] **2. Encoder como rede de segurança (25–27/09).** BERTimbau-base (Legal-BERTimbau-base como
      comparação), marcação BIO.
      Treino: sintético base + diversificado (HF, revisão `0209a85…`) + amostra `ajuste` + LeNER-Br
      `train`, só entidades `JURISPRUDENCIA`/`LEGISLACAO` do escopo. Uma candidata do encoder **só entra** se: (a) o regex não
      achou nada sobreposto; (b) tem dígito e sigla, súmula, artigo ou tribunal; (c) passa pelo
      `ler_campos`. Senão, descartada. Inferência em **CPU** (determinismo, R49).
  - [x] **2a. Dataset de treino** (`src/verificador/treino/`, `tests/test_treino.py`).
        *2026-09-24* — Decisões do Roberto: LeNER-Br **entra** nos pesos publicados (a regra do desafio
        permite "qualquer dataset público"; o repositório declara MIT; e-mail aos autores em paralelo,
        ver `conformidade_dados_externos.md`, achado 2), e os **14 documentos de `ajuste`** da amostra
        entram no treino (os 12 de `controle`, nunca).
        Comando: `python -m verificador.treino.dataset --sintetico sintetico_hf --amostra
        desafio-jusbrasil-bracis-2026 --lener lener-br/leNER-Br` → `runs/encoder_dataset/`
        (`dataset.jsonl` + `manifesto.json`). O `sintetico_hf/` é o snapshot do HF na revisão
        `0209a85…` (a camada 1 em `base/` é idêntica ao `sintetico/` local, conferido com `diff`).
        - **Formato:** spans por caractere, sem depender de tokenizador; a tokenização e o BIO vão para
          o notebook (`treino/bio.py`). A ida e volta com o tokenizador do BERTimbau recupera **3435 de
          3435** spans exatamente, janela de 510 tokens com sobreposição de 128.
        - **Conversão do LeNER-Br para a convenção do desafio:** jurisprudência no escopo → `JUR`;
          fora do escopo (TCU, TJ…) → O; **número do próprio processo** e casos ambíguos → fora da perda;
          `LEGISLACAO` só vira `LEI` com "art." e dígito (o gabarito não tem lei sem artigo).
        - **Higiene por construção:** o `test` do LeNER-Br nem é lido; controle do sintético, controle
          da amostra e `dev` do LeNER-Br saem marcados e não vão para o treino (testado).
        - **Contagens:** treino = sintético 1244 JUR/324 LEI (320 docs), amostra 88/13 (14 docs),
          LeNER-Br 279/827 (50 docs). Em janelas: LeNER-Br 921 (281 só com O), sintético 355, amostra
          **37** — a fonte mais parecida com o conjunto final é só ~3% das janelas; a mistura do
          notebook precisa reforçá-la.
        - O `dataset.jsonl` contém texto da amostra (dados da competição): fica em `runs/`, **não se
          publica**. Publica-se os pesos e o código.
  - [ ] **2b. Notebook de treino no Kaggle** (T4): ver "Próximos passos do encoder" abaixo.
- [ ] **3. Decisão em 27/09, 22h (go/no-go).** Critérios na seção do protocolo. Se não passar, fica
      `usar_encoder=false` (ADR-011 já prevê) e os pesos não são publicados.
- [ ] *Opcional — camada 3 do sintético:* o LLM escreve a **própria citação** a partir de um registro do
      acervo; o gabarito é localizado pelos dígitos, e a citação é descartada se algum dígito mudar. Mede
      o ponto cego atual e dá treino variado ao encoder. Reaproveita o notebook 005.
- [ ] *Opcional — LLM como auditor de recall:* o Qwen lista toda referência a julgado, súmula ou lei num
      texto; o que só ele achou vira candidato a correção de regex, revisado por uma pessoa. Fora da
      execução da submissão, sem efeito no determinismo.

**Carga:** trabalho para duas pessoas em paralelo (1 e 2). Se for uma só, fazer o 1 e uma versão
mínima do 2.

#### Protocolo do teste no LeNER-Br (a régua do encoder)

Amostra, controle e sintético estão saturados: neles o encoder só consegue mostrar **perda**. A única
régua de **ganho** é a divisão `test` oficial do LeNER-Br, restrita ao escopo.

- **Filtro do escopo** (o mesmo da medição de 24/09): entidade `JURISPRUDENCIA` cujo trecho **não**
  cita TCU, TC, Tribunal de Contas, TRF, TJ*, TRT, TRE, Tribunal Regional, Tribunal de Justiça ou
  "Acórdão"; que menciona STF, STJ, TST, TSE, STM, Supremo, Superior Tribunal, Tribunal Superior ou
  Suprema Corte no trecho **ou** em até 40 caracteres em volta; que tem dígito e ao menos 6 caracteres.
  Sem distinção de maiúsculas. Implementado em `verificador.treino.lener.no_escopo`, com teste que
  trava as contagens (`tests/test_treino.py`).
- **Métrica:** recall por IoU ≥ 0,5 (mesmo critério da métrica oficial) e, à parte, qualquer sobreposição.
- **Linha de base do regex (commit `70ff324`, `sub-005`):**

  | Divisão | Docs | Citações no escopo | IoU ≥ 0,5 | Qualquer sobreposição |
  |---|---|---|---|---|
  | `train` | 50 | 352 | 222 (63,1%) | 250 (71,0%) |
  | `dev` | 10 | 35 | 3 (8,6%) | 3 (8,6%) |
  | **`test`** | 10 | **74** | **38 (51,4%)** | 53 (71,6%) |

  *2026-09-24* — ao reimplementar o filtro, `train` (222/352) e `test` (38/74) bateram exatamente;
  o `dev` deu **35**, não 31, com os mesmos 3 acertos. A contagem de 31 não foi reproduzida e fica
  corrigida para 35.

  **Número do próprio processo.** O LeNER-Br marca o número do processo do próprio documento
  (cabeçalho, ementa: `HC 110260 / SP` 19 vezes num só documento) como `JURISPRUDENCIA`. No desafio
  isso é distrator (R34), não citação. Identificado pelo `titulo` dos metadados:
  `train` **73 de 352**, `dev` 13 de 35, `test` **10 de 74**. A régua acima **não muda** (senão a
  comparação com a linha de base se perde), mas o relatório do go/no-go traz também a linha "sem
  número próprio" (`test`: 64 citações). No treino, esses spans ficam fora da perda.

- **Higiene:** o `test` não guia nenhuma correção de regex nem ajuste do encoder; `train` e `dev` sim.
  Atenção: a análise de 24/09 listou exemplos de todas as divisões, então alguns casos do `test` já
  foram vistos. Registrar quais regras vieram desses exemplos, para a comparação ser honesta.
- **O encoder entra se, e só se:**
  1. aumentar o recall no `test` do escopo acima do regex **reforçado** (atividade 1), não do regex de hoje;
  2. não perder nada em amostra (192/192), controle e sintético (988/994 e 992/994 no diversificado);
  3. não gerar **nenhum** falso positivo novo nos distratores da amostra (autos CNJ do cabeçalho,
     protocolo, OAB, fls., valor da causa). **Medido no `controle` da amostra (12 documentos)**: os 14
     de `ajuste` estão no treino e ali o número seria otimista. Reportar os dois, separados;
  4. manter precisão de spans 1,0 e τ = 0 em todos os conjuntos, e R49 verde.
- **Limite estatístico:** são só 74 citações no `test`. Um ganho de 1 ou 2 é ruído; registrar o número
  absoluto, não só a porcentagem.

#### Próximos passos do encoder (registrado em 2026-09-24, depois do dataset)

1. **Reforço do regex (atividade 1), em paralelo.** Continua pré-requisito do go/no-go: o critério 1
   compara com o regex *reforçado*. Guiado só por `train`/`dev` do LeNER-Br.
2. **Notebook de treino no Kaggle (T4)**, `notebooks/kaggle/07_treino_encoder.ipynb`:
   - clona o repo; baixa o sintético na revisão `0209a85…`; clona o LeNER-Br no commit
     `4999cb7f63191f1d6904206f312eeca8f5b45c5a`; usa a amostra dos dados da competição;
   - roda `python -m verificador.treino.dataset` e **confere o `sha256_dataset`** contra o do
     `manifesto.json` local (mesmo dataset dos dois lados);
   - tokeniza com `AutoTokenizer` na revisão fixa, janelas de `treino/bio.py`;
   - mistura: toda janela com citação; ~1/3 das janelas só-O do LeNER-Br; amostra `ajuste` repetida
     ~4×. Registrar a mistura no manifesto dos pesos;
   - mesmos hiperparâmetros para os dois modelos (semente 0, lr 5e-5, ~5 épocas, lote 16, fp16);
   - mede, por modelo: recall/precisão de `JUR` no `dev` do LeNER-Br (régua do escopo) e nos
     controles do sintético e da amostra. Escolhe pelo `dev` + controles; empate → BERTimbau.
3. **Integração** em `extracao/` atrás do `usar_encoder`: inferência em CPU por janelas
   (`dono_por_token` + `decodificar`), regras (a), (b) e (c), e descarte no cabeçalho. Exige `torch`
   (CPU) e `transformers` no ambiente, nas versões da imagem do Kaggle (ADR-014).
4. **Go/no-go em 27/09, 22h**, com o relatório: régua do `test` (74 e "sem número próprio", 64),
   controles, distratores no controle da amostra, precisão, τ e R49.
5. **Se passar: publicar os pesos** no HF com revisão fixa (R45, R46), card com o aviso MIT do
   modelo-base e as fontes de treino (link + revisão; a amostra só citada, não incluída).

- [x] **Camada LLM do gerador sintético** (Apache 2.0, ex.: Qwen3 8B ou Gemma 4 E4B; temperatura 0, semente
      fixa): reescreve o parecer em volta das citações com frases variadas **sem alterar os trechos**
      (verificar por código que cada trecho continua presente byte a byte).
      *2026-09-24* — feito com Qwen2.5-7B-Instruct (Gemma saiu pela licença, achado 3 de
      `conformidade_dados_externos.md`). O trecho vai ao LLM como marcador e volta byte a byte (`assert`
      por citação). Ver o item "LLM diversificando o sintético" no Tier 2.
- [x] Rodar a geração no Kaggle GPU (supervisionar: erro no meio da execução gasta cota).
      *2026-09-24* — ver o item "LLM diversificando o sintético" no Tier 2.
- [x] **Publicar o dataset sintético** no Hugging Face, revisão fixa, licença aberta (R46) — antes de
      30/09 23h59 BRT. Criar a conta HF do projeto se ainda não existir.
      *2026-09-24* — [`Roberto2799/jusbrasil-sintetico-diversificado`](https://huggingface.co/datasets/Roberto2799/jusbrasil-sintetico-diversificado),
      MIT, revisão `0209a853e6e59b263b138200963b579105baca24`. A camada 1 (idêntica ao `sintetico/` usado
      na calibração da `sub-002`) está em `base/`, e a camada 2 (Qwen) na raiz, com dataset card.
- [x] **Escolher o encoder** por medição e licença OSI (R21): RoBERTaLexPT, BERTimbau, Legal-BERTimbau (e
      modelos já ajustados no LeNER-Br). **Conferir a licença antes de treinar.**
      *2026-09-24* — licenças conferidas; RoBERTaLexPT e os modelos já ajustados no LeNER-Br ficam fora.
      Depois do levantamento de tokenizador e corpus de pré-treino, **escolhido BERTimbau-base**, com
      Legal-BERTimbau-base como comparação no mesmo treino (ver "Modelos preferidos" acima).
- [ ] **Treinar o NER** (marcação BIO) em `treino/`, com o sintético (+ opcionalmente LeNER-Br), tolerando ruído
      de OCR no corpo original (não na cópia normalizada).
- [ ] **Publicar os pesos** no Hugging Face com revisão fixa (R45, R46).
- [ ] **Integrar** em `extrair()` como **união** com o regex (ADR-011), com o **filtro das 4 formas** (o encoder
      não pode trazer "jurisprudência pacífica desta Corte" de volta — R33) e a resolução de sobreposição (R3).
- [ ] **Medir contra a linha de base** no controle. Entra na submissão **somente se ganhar**; senão fica
      desligado (`usar_encoder=false`) e os pesos são publicados mesmo assim se já foram usados em treino/medição.
- [ ] Conferir que encoder + (futuro) LLM cabem numa T4 de 16 GB (margem sobre os 24 GB do ambiente — R44).

## Fase 5 — Leitor LLM de campos difíceis e confiança (27–29/09) · **opcional**

**ADR:** 013, 008 · **Responsável:** ____ (frente D)

> **Proposta de 2026-09-19:** a parte de **confiança** desta fase foi proposta para ser antecipada (ver 3.1-a).
> Se aprovada, aqui fica só o leitor LLM e a regeneração da tabela de confiança com `fonte="llm"`.

- [ ] **Fila de difíceis**: candidatas em que `ler_campos` devolveu `None` (número ausente nas formas a/b;
      lei+artigo na c; tribunal/classe/ano/relator na d). Contar quantas há na amostra (estimativa ~20).
- [ ] **Leitor LLM em lote**: prompt fixo e versionado, JSON de campos, temperatura 0, semente registrada no
      manifesto (R47), modelo por link + revisão (R45). **O LLM nunca decide a classe.**
- [ ] **Conferência R48** já implementada na Fase 1 — ligar.
- [ ] Marcar `fonte="llm"` no rastro.
- [ ] **Medir contra sem-LLM** no controle. Só liga se melhorar o score; senão `usar_llm=false`.
- [ ] Verificar impacto em determinismo (R49) e em memória (R44).
- [ ] **Confiança calibrada** (R26, opcional): gerar a tabela `taxa_acerto[caminho, correcao_ocr, fonte]` no
      controle; comparar o **Brier** com o de uma confiança constante; **se não for menor, não enviar
      confiança.**
- [ ] Se for usar o skill `prompt-engineering` para o prompt do LLM, lembrar: testar contra casos adversariais
      antes de gravar a versão final.

---

## Fase 6 — Congelamento (29–30/09) · todos

- [ ] **Publicar artefatos finais** (pesos e dataset, se usados) no Hugging Face **antes de 30/09 23h59 BRT**;
      conferir os links e as revisões fixas (R45, R46). Se nada foi treinado, registrar isso no README.
- [ ] **README final**: como reproduzir, comando exato, versão do ambiente, links + revisões dos modelos.
- [ ] **`Dockerfile`**: tag fixa da imagem do Kaggle conferida contra a versão real vista no notebook (ADR-014);
      tentar `docker build` se houver espaço (imagem de vários GB); senão documentar como não testado.
- [ ] **`requirements.txt`**: todas as versões fixas; licenças OSI conferidas (R21).
- [ ] **Determinismo**: duas execuções → CSV idêntico (R49), no notebook do Kaggle.
- [ ] **Sem literais da amostra** e **sem dependência de nome de arquivo** (testes R41, R43 verdes).
- [ ] **`code-review`** do repositório inteiro (`/code-review high`), corrigir o que for relevante.
- [ ] **Escolher a submissão final** (decisão humana, até 30/09 23h59 BRT), com `submeter` criando a tag.
- [ ] Pacote reproduzível para a organização (se a equipe for finalista): repositório, README, links dos
      modelos com revisão, `Dockerfile`/`requirements`, comando exato.
- [ ] Confirmar elegibilidade dos integrantes e divisão de prêmio (se solicitado).

---

## Calendário resumido

| Data | Marco | Quem |
|---|---|---|
| 18–19/09 | Fase 0: contas, tokens, primeiro notebook, divisão das frentes, e-mail à organização | todos |
| 19–24/09 | Fase 1: frentes A, B, C, D em paralelo (PRs pequenos e frequentes) | cada frente |
| **24–25/09** | **Fase 2: integração** → primeira versão só-regras | integrador |
| 25/09 | Fase 3: tag `sub-001`, 1ª submissão, análise de erro, **decisão de seguir ou não com a Fase 4** | todos |
| 25–28/09 | Fase 4: sintético com LLM, encoder NER, publicação (opcional) | frente C (+B) |
| 27–29/09 | Fase 5: leitor LLM e confiança (opcional) | frente D |
| 29–30/09 | Fase 6: congelamento, publicação, determinismo, `code-review`, submissão final | todos |

**Regra de corte:** se a versão só-regras não estiver integrada e medida em **25/09**, as Fases 4 e 5 são
descartadas e o tempo restante vai para melhorar regras e tabelas com a análise de erro. Isso é aceitável
e já previsto.

---

## Riscos e pontos em aberto

| Risco / dúvida | Efeito | O que fazer |
|---|---|---|
| Referência vaga conta como `incompleta` no conjunto final? (`specs/scope.md`, ADR-005) | R33 pode custar recall de `incompleta` | E-mail à organização; manter o detector atrás da chave até a resposta |
| Teto diário de submissões desconhecido | Limita quantas iterações no leaderboard | Descobrir na página da competição; **não** usar o leaderboard como sinal de qualidade (ADR-009) |
| Overfitting à amostra (26 docs, poucos moldes) | Nota alta local, queda no conjunto cego | Divisão ajuste/controle + sintético + R41/R43 |
| Frente B atrasa | Bloqueia a integração | Dividir em B1/B2; cortar cedo formas raras (d) para depois |
| GPU do Kaggle (cota, T4 16 GB × ambiente de 24 GB) | Fase 4/5 pode não caber | Regra de corte de 25/09; modelo menor; modo sem LLM sempre disponível |
| Determinismo entre hardwares (T4 do Kaggle × GPU da organização) | R49 não garantido entre ambientes | Limitar o LLM a pontos com conferência (R48); regras determinísticas no restante |
| Tag `v170` do `Dockerfile` pode não bater com o ambiente real do notebook | Reprodução inconsistente | Conferir na primeira execução do notebook (Fase 0) |
| Citações no plural, artigo sem lei, súmula sem número | Recall menor em formas raras | Registrado como débito conhecido; tratar só se aparecer na análise de erro |
| Prazo de publicação de pesos/dataset (30/09 23h59) | Desclassificação | Publicar assim que estiverem estáveis, não no último dia |

---

## Checklist de "pronto para a submissão final"

- [ ] `pytest` verde, incluindo R35, R36, R41, R43, R48, R49
- [ ] Os 96 `real` da amostra resolvem para o `id_canonico` certo; τ = 0 na amostra e no controle
- [ ] `submission.csv` aceito pelo `kaggle_metric.py` (sem R3, sem `ParticipantVisibleError`)
- [ ] Duas execuções idênticas byte a byte
- [ ] Modelos e dataset publicados, com link e revisão fixa, antes do prazo
- [ ] Sem chamada de rede na execução; licenças OSI conferidas
- [ ] README, `Dockerfile` e `requirements.txt` com versões fixas
- [ ] Árvore git limpa, tag `sub-NNN` criada, manifesto com commit + revisões + versão do ambiente
- [ ] `code-review` feito
