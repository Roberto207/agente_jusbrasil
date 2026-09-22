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
- [x] **Causa 4** (2026-09-21, +19): eram dois defeitos em `texto/normalizacao.py`. (1) A troca letra→dígito
      rodava **depois** da limpeza de espaço, que exige dígito dos dois lados — em `7I. 346` o `I` só vira `1`
      tarde demais. (2) A regra olhava o caractere colado, então `l` em `l.239` (encostado no ponto) escapava.
      Agora o token numérico abrange o espaço após o separador, a decisão é por **grupo** entre separadores, e
      a correção roda antes da limpeza. A regra por grupo evita o erro oposto: em `1.111.222-GO` a UF não vira `90`.
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

## Fase 4 — Encoder NER e sintético com LLM (25–28/09) · **opcional: só se a Fase 3 estiver fechada**

> **Risco de prazo.** É a etapa que mais pode estourar (GPU do Kaggle com cota compartilhada de ~30 h/semana
> por conta, treino, publicação). O sistema já prevê `usar_encoder=false` e `usar_llm=false`; se não der tempo,
> a submissão final é só-regras e continua válida. **Decidir em 25/09 se esta fase começa.**

**Responsável:** ____ (sugestão: frente C, que já tem o gerador) · **ADR:** 011, 012

- [ ] **Camada LLM do gerador sintético** (Apache 2.0, ex.: Qwen3 8B ou Gemma 4 E4B; temperatura 0, semente
      fixa): reescreve o parecer em volta das citações com frases variadas **sem alterar os trechos**
      (verificar por código que cada trecho continua presente byte a byte).
- [ ] Rodar a geração no Kaggle GPU (supervisionar: erro no meio da execução gasta cota).
- [ ] **Publicar o dataset sintético** no Hugging Face, revisão fixa, licença aberta (R46) — antes de
      30/09 23h59 BRT. Criar a conta HF do projeto se ainda não existir.
- [ ] **Escolher o encoder** por medição e licença OSI (R21): RoBERTaLexPT, BERTimbau, Legal-BERTimbau (e
      modelos já ajustados no LeNER-Br). **Conferir a licença antes de treinar.**
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
