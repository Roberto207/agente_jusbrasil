# Auditoria de código — relatório para decisão

**Data:** 2026-09-24 · **HEAD auditado:** `1e744a7` · **Spec:** `specs/auditoria_codigo_multiagente.md`
**Revalidado em:** 2026-09-25, contra `10e3801` (depois do reforço do regex, do encoder ligado e da Fase 5
deixada de lado) — ver a seção **0**, que manda sobre o status dos itens abaixo.
**Status:** **aplicado em 30/09** no branch `limpeza-auditoria` (5 commits, `b241284`..`d5f4758`) — ver
"Aplicação de 30/09" logo abaixo. Os `[x]` das seções 1–5 marcam o que entrou.

## Aplicação de 30/09 — o que entrou e a checagem

| Commit | Itens |
|---|---|
| `b241284` chore | F1, F2, N2 (notebook `05` fixado em `379714d`, commit que gerou o dataset publicado). N1 foi revertido em seguida: os notebooks voltaram como **históricos** (`notebooks/kaggle/README.md`) |
| `60373c4` refactor | A1–A6, A8, A19 |
| `ac46790` refactor | B1, B4, B7, B10 (+ A7), B16; testes B2, B9 |
| `20b9d69` refactor | remoção do LLM (A16 e a parte LLM de A15/A18), `dtype`; `semente` passa a ser usada pelo encoder |
| `d5f4758` docs | A9–A13 |

**Fora, de propósito:** B3/B11 (NFKD×NFD, a base nova é desconhecida), A14/B18 e A15 do encoder (uso
real), A17 (referência vaga fica desligada, decisão de 30/09), B8, marginais B5/B6/B12–B15, B17 (vai para a
Fase 7, junto do desacoplamento do `.db`), C1–C11.

**Checagem mecânica** depois de **cada** commit, contra a linha de base em `574ae15` (encoder ligado,
pesos da revisão `d91d0914` do cache, sem rede):

| Artefato | Resultado |
|---|---|
| `submission.csv`, `rastro.jsonl`, `jsons/` — amostra, sintético base, diversificado | idênticos (amostra: sha256 `4c6e3538…`) |
| `avaliar` (amostra/ajuste/controle, sintético e diversificado com treino/controle) | 1,100000 em todos, idêntico |
| régua do LeNER-Br **com encoder** (`train`/`dev`, jurisprudência e lei) | idêntica (`dev`: jur 19/35, lei 99/127) |
| índice (1.014 registros, dump completo), `gerar-sintetico --pares 100 --semente 0`, `taxa_acerto.json` | idênticos |
| manifesto | só a `config` muda no commit do LLM (sem `usar_llm`, `dtype`, `llm_*`), como previsto |
| `pytest` | 289 → **283** (−6: casos do R48, removido com o LLM); R41/R43 verdes |
| R49 | duas execuções da amostra, mesmo sha256 `4c6e3538…` |
| Linhas | `src/` 5.672 → **5.457 (−215)** · `tests/` 2.860 → **2.785 (−75)** |

Achado de passagem (não é da limpeza): `gerar-sintetico` no código atual já não reproduz o `sintetico/` do
disco (gerado em 22/09, antes do reforço do regex de 24/09, que mudou tabelas). A comparação foi feita entre
execuções do gerador, antes × depois.

## 0. Revalidação de 25/09 — o que mudou

**Como:** (1) cada achado relocalizado no código atual; (2) arquivos que mudaram desde `1e744a7`
separados dos intocados; (3) `vulture` de novo em `src/`; (4) `coverage` de produção no código atual —
`rodar`/`avaliar` na amostra **com o encoder ligado** e no sintético base, mais `ambiente`, `indexar`,
`comparar`. `vulture`/`coverage` só no venv de trabalho (`runs/`), nada no `requirements.txt`.

**O que não foi refeito:** a checagem mecânica (aplicar as remoções numa cópia e comparar CSVs). Ela
valeu para `1e744a7`; no código atual ela é refeita **depois da aprovação**, no branch de limpeza, como a
spec manda (Etapa 3). Os itens de arquivos intocados devem continuar idênticos; os de arquivos que
mudaram precisam dela obrigatoriamente.

### Status atual por item

| ID | Onde está hoje | Status | Observação |
|---|---|---|---|
| A1 | `cli.py:184` + `import sqlite3` (`:13`) | **válido** | `vulture` confirma; arquivo mudou → reconferir na checagem mecânica |
| A2, A3 | `sobreposicao.py:54`, `:40` | **válido** | arquivo intocado |
| A4 | `campos.py:233` | **válido** | arquivo mudou (lei/súmula), trecho não |
| A5 | `campos.py:134` | **válido** | idem |
| A6 | `numero_proprio.py:224` | **válido** (opcional) | intocado; ressalva do despachante público mantida |
| A7 | `calibrar.py:199` | **válido** | intocado; some junto com B10 |
| A8 | `sintetico/citacoes.py:21` | **válido** | `.forma` de `Fabricada` segue sem leitura |
| B1 | `campos.py` (7 blocos) + `pipeline._campos_vazios` | **válido** | o ramo de súmula ganhou OJ; o bloco `Campos(...)` é o mesmo |
| B3, B11 | 4× `_sem_acento`, 2× `normalizar_relator` | **válido, mas adiar** | risco NFKD×NFD com a base da fase 2 (1.016 × 1.014 registros) — não fazer antes da submissão final |
| B4 | `campos.py:90` × `atributos.py:136` | **válido e mais necessário** | agora `extracao/encoder.py:26` importa a função **privada** `_classes_no_texto` de outro módulo; torná-la pública resolve as duas coisas |
| B7 | sha256 em `cli`, `determinismo`, `confianca` (+ `treino/` usa inline) | **válido** | `treino/` fica de fora (código de treino, não de execução) |
| B10 | `cli.py:342,359` × `calibrar.py:193` | **válido** | |
| B16 | `campos.py:76`, `:307` | **válido** | |
| B18, A14 | `extracao/__init__._FORMAS`, `Candidata.padrao` | **manter (mudou)** | o encoder agora grava `padrao="encoder"`: o gancho virou uso real |
| A15 | flags e config do **encoder** | **manter (mudou)** | encoder ligado; `--sem-encoder` passou a ter uso real |
| A15/A16/A18 | tudo do **LLM**: `decisao/llm.py` (56), exportações em `decisao/__init__`, `usar_llm`/`llm_link`/`llm_revisao` + overlay de env em `configuracao.py`, `--sem-llm` e a trava em `cli.py:273`, `FonteCampos="llm"` em `contratos.py:11`, teste R48 em `test_decisao.py`, `configuracao.semente`/`dtype` (ninguém lê) | **morto (mudou)** | Fase 5 deixada de lado (25/09). ~−90 linhas. `contratos.py` pede aviso à equipe (regra 1); muda `hash_configuracao` e o manifesto (tag nova de qualquer jeito). R48 no `DEFINE.md` vira "não aplicável" |
| A17 | referência vaga | **dormente** | decisão continua marcada para a fase 2 |
| A9–A12 | textos | **válido** | A11 (`campos.py:286`, "Fase 4" para o LLM) some com a remoção do LLM |
| A13 | textos "quando existirem" | **parcial** | `pipeline.py` já corrigido em 25/09; falta `cli.py` (help/docstring) |
| **A19 (novo)** | `extracao/encoder.py:98` `self._torch` | **morto** | atributo gravado e nunca lido (`vulture`); −1 linha |
| N1, N2, F1, F2 | notebooks e arquivos soltos | **válido** | N1 agora inclui `00` e `02`–`04`; `06`/`07`/`08` ficam (`07` reproduz os pesos, `08` é o da submissão atual) |
| D1 | links quebrados | **corrigido em 25/09** | `docs/guia_kaggle.md`, `docs/ia_no_pipeline.md`, `docs/analise_erros_baseline.md` → `docs/gerais/…` |
| D2 | docs superados | **marcado histórico em 25/09** | `BUILD_PROMPT.md`, `resultado_primeira_rodada.md`, `analise_erros_baseline.md` ganharam aviso no topo |
| C1–C11 | overfitting | sem mudança | C4 (famílias): a família RE/ARE (25/09) veio do acervo (8 acórdãos), não de um caso da amostra |

**Código novo desde a auditoria (não entra no corte):** `treino/` (~900 linhas) reproduz os pesos
publicados — faz parte do pacote reproduzível; `extracao/encoder.py` — linhas 68–82 não rodam na amostra
(o encoder não acrescenta nada lá), mas rodam no LeNER-Br: é **generalização**, não código morto.

**Cobertura de produção agora:** `extracao/` e `decisao/` entre 71% e 100%; o que não roda na amostra é
guarda de invariante ou generalização, como em 24/09. (`sintetico/`, `calibrar`, `determinismo` aparecem
com 0% só porque esta passada não rodou `gerar-sintetico`/`calibrar`/`submeter`.)

### O que eu recomendo aprovar para o branch de limpeza (antes da tag final)

Baixo risco, saída idêntica esperada: **A1–A8, A19, B1, B4, B7, B10, B16, remoção do LLM (A16 e
correlatos), textos A9–A13, N1, N2, F1, F2.** Adiar: **B3/B11** (base da fase 2), **A17** (decisão da
fase 2), marginais B5/B6 (mexem na CLI que os notebooks chamam). Depois: checagem mecânica nos quatro
conjuntos + `pytest` + R49, e `/code-review high` no branch.

## Como foi feito

- **Etapa 0 (dossiê, sem LLM):** `coverage` em duas passadas: (a) produção — `rodar`/`avaliar` na amostra
  (26 docs) e no sintético (200 docs), mais `ambiente`, `indexar`, `gerar-sintetico`, `calibrar`, `comparar`,
  `submeter`; (b) `pytest` (194 passed). `vulture` em `src/`. Mapa de chamadores em src/tests/notebooks.
  `coverage`/`vulture` instalados só no scratchpad — nada no `requirements.txt`.
- **Etapa 1:** três lentes em paralelo — A (morto/vestigial), B (enxugamento), C (overfitting). A lente D
  (bugs) ficou de fora: o `/code-review high` já está na Fase 6 (`tarefas_equipe.md:801`).
- **Etapa 2:** verificador adversarial tentou refutar cada achado e aplicou os de código numa **cópia**.
- **Não coberto:** o sintético diversificado (só no HF, não está no disco).

**Cobertura de `src/`:** 2.320 instruções — 2.098 produção executa · 86 só teste · 136 nunca (quase tudo
guarda de invariante ou generalização; ver "Mantidos").

### Checagem mecânica (cópia com A1–A8, B1, B3, B4, B7, B10, B11, B16, B18 + testes B2, B8, B9)

| Artefato | Resultado |
|---|---|
| `submission.csv`, `rastro.jsonl`, `jsons/` — amostra e sintético | idênticos byte a byte |
| índice (1.014 registros, dump completo) | idêntico |
| `avaliar` (score 1,100000 amostra · 1,098949 sintético) | idêntico |
| `gerar-sintetico --pares 100 --semente 0` | `diff -r` vazio contra `sintetico/` |
| `calibrar` → `taxa_acerto.json` | idêntico |
| manifesto (config, hashes, `hash_configuracao`) | idêntico (só `git` difere: cópia fora do repo) |
| `pytest` (testes adaptados) | 194 passed, incl. `test_r41_*`/`test_r43_*` |
| R49 (duas execuções) | mesmo sha256 `4c6e3538…` |
| Linhas | `src/` 4.549 → **4.395 (−154)** · `tests/` 2.506 → **2.431 (−75)** |

---

## 1. Remoção de código morto — validado, saída idêntica

| ✔ | ID | Local | O que é | Linhas |
|---|---|---|---|---|
| [x] | A1 | `cli.py:157-163` + `import sqlite3` (`:12`) | `contar_documentos` sem chamador (src, tests, notebooks, docs, Dockerfile) | −10 |
| [x] | A2 | `extracao/sobreposicao.py:54-55` | `if _chave(cand) > _chave(outra)` inalcançável por construção (lista já ordenada desc.) | −3 |
| [x] | A3 | `extracao/sobreposicao.py:40-41` | `if not candidatas: return []` redundante | −2 |
| [x] | A4 | `extracao/campos.py:221-222` | `artigo.endswith(".")` — o grupo `(\d+(?:\.\d+)?)` nunca termina em ponto | −2 |
| [x] | A5 | `extracao/campos.py:127-128` | `if not numero` no ramo Tema — `\d+` nunca dá vazio (verificado em todos os code points) | −2 |
| [x] | A6 | `base/numero_proprio.py:224-225` | ramo `"dispositivo"`; o único chamador já desvia antes. **Ressalva:** documentado como despachante público (`mudancas_caio_fase_1_a.md:175`) — opcional | −2 |
| [x] | A7 | `avaliacao/calibrar.py:199-200` | ramo `amostra/sintetico → None` sem chamador. Some junto com B10 | −2 |
| [x] | A8 | `sintetico/citacoes.py:21` | campo `Fabricada.forma` escrito e nunca lido | −1 |

## 2. Enxugamento — validado, saída idêntica

| ✔ | ID | Local | Proposta | Linhas | Ressalva |
|---|---|---|---|---|---|
| [x] | B1 | `extracao/campos.py` (7 blocos de 13 linhas) + `pipeline._campos_vazios` | constante `CAMPOS_VAZIOS` + `replace(...)`; fica em `campos.py`, sem tocar `contratos.py` | −76 | — |
| [ ] | B3 | `_sem_acento` 4× (`atributos.py:50`, `numero_proprio.py:35`, `campos.py:47`, `cabecalho.py:25`) + `tabelas._so_ascii` | uma `sem_acento` NFD em `tabelas/__init__.py` | −18 | **Lado do documento idêntico por construção; lado da base verificado só na base atual.** NFKD×NFD divergem em 4.952 code points (º, ª, ﬁ, NBSP…). Se a base da fase 2 mudar (Kaggle citou 1.016 registros), refazer o dump do índice. Alternativa sem risco: deduplicar só em pares (NFKD base / NFD documento) |
| [x] | B4 | `campos._classes_no_texto` = `atributos._siglas_no_texto` | uma `classes_no_texto` em `tabelas` (manter alias usado por `test_extracao.py:272`) | −18 | — |
| [x] | B7 | sha256 3× (`cli.hash_arquivo`, `determinismo.hash_csv`, `confianca.hash_tabela`) + caminho da taxa 2× | um `hash_arquivo` em `determinismo.py`; `confianca` usa `calibrar.destino_padrao` | −15 | — |
| [x] | B10 | `cli._conjuntos_disponiveis/_documentos_do_conjunto` × `calibrar._docs_do_conjunto` | função única em `avaliacao/divisao.py` | −10 (líquido) | ajustar `tests/test_pipeline.py:157` (importa a função antiga) |
| [ ] | B11 | `normalizar_relator` em `atributos.py:55` e `campos.py:52` | uma só (depende de B3) | −9 | mesma ressalva de B3 |
| [x] | B16 | `campos._numero_com_ocr` devolve flag de OCR sempre sobrescrita em `ler_campos` (`:294-296`) | devolver só o número | −4 | ajustar `tests/test_campos.py:175` |
| [ ] | B18 | `extracao/__init__._FORMAS` — 4ª coluna sempre = 2ª | tirar a coluna; `Candidata.padrao` continua recebendo `forma` | −3 | decidir junto com A14 (gancho do encoder) — **sugiro depois de 27/09** |
| [x] | B2 | `tests/test_esqueleto.py` repete conftest e roda de novo a amostra | **mover** as asserções únicas (índice ==1014, cabeçalho do CSV, `relatorio.md`) para a fixture `run_amostra` | −25 (tests) | não apagar: único teste de `cmd_indexar` |
| [ ] | B8 | `tests/test_integracao_ab.py:55-68` `_milhar`/`_cnj` | importar de `sintetico/citacoes` | −13 (tests) | o oráculo do teste passa a depender do formatador de produção |
| [x] | B9 | fixture `indice` 4× nos testes | uma só, escopo `session`, no `conftest.py` | −10 (tests) | — |

### Marginais (não aplicados na cópia; ganho pequeno)

| ✔ | ID | O que é | Linhas | Ressalva |
|---|---|---|---|---|
| [ ] | B5 | imports locais repetidos nas `cmd_*` → topo do `cli.py` | −18 | deixar `pandas` lazy (+0,32 s em todo comando se subir) |
| [ ] | B6 | `main()` com 46 linhas de `if/elif` → `set_defaults(func=...)` | −18 | `main()` sem teste; mexe na interface que os notebooks chamam |
| [ ] | B12 | overlay de env 5× em `configuracao.carregar` → laço | −8 | maioria é gancho dormente |
| [ ] | B13 | gravar JSON 4× | −6 | os 4 **não** são iguais (`sort_keys`, `ensure_ascii`) — helper precisa dos parâmetros |
| [ ] | B14 | IoU 3× | −6 | unificar só `sobreposicao`/`comparar`; manter `tests/helpers.iou_offsets` como oráculo |
| [ ] | B15 | filtro de docs repetido em `relatorio.py:22/29` | −5 | — |
| [ ] | B17 | `TABELA_DOCUMENTOS`=`indice.TABELA`, `"desafio1_bracis.db"` e `kaggle_metric` repetidos; `gerador` importa `caminho_db` da CLI | −3 | corrige inversão de camada |

## 3. Textos vestigiais (0 linhas, só texto)

| ✔ | ID | Local | Correção |
|---|---|---|---|
| [x] | A9 | `cli.py:1`, `:571`, `:574` | docstring cita só 5 comandos; help de `rodar` diz "JSON vazio por documento"; help de `indexar` desatualizado |
| [x] | A10 | `extracao/campos.py:22-31` | dois parágrafos repetem o mesmo comentário sobre `_RELATOR` (−4) |
| [x] | A11 | `extracao/campos.py:274` | diz "Fase 4" para o LLM — **está errado**, é a Fase 5 |
| [x] | A12 | `tabelas/__init__.py:1` | "provisórias da frente B" |
| [x] | A13 | `pipeline.py:3-4,36`, `extracao/__init__.py:52`, `cli.py:247` | "quando existirem" / "Fases 4 e 5" — **só depois de 27/09**, conforme o go/no-go |

## 4. Dormente — decisão humana amarrada ao go/no-go (27/09) — não mexer agora

| ID | O que é | Se o encoder/LLM cair |
|---|---|---|
| A14 | `contratos.py:31` `Candidata.padrao` (= `forma` sempre). **Refutado como morto:** `DESIGN.md:255` o define como "nome do padrão ou `encoder`" — gancho do ADR-011; muda `rastro.jsonl`; regra 1 da convivência | simplificar junto com B18 |
| A15 | `usar_encoder`/`usar_llm`, `dtype`, `encoder_*`/`llm_*`, `com_flags`, `--sem-encoder`/`--sem-llm` (hoje não fazem nada: padrão já é `False`, `True` aborta), parâmetro `encoder` de `extrair`, `OrigemCandidata="encoder"` | ~−25; muda `hash_configuracao`/manifesto |
| A16 | `decisao/llm.py` inteiro (`ler_campos_llm` sem chamador; `numero_do_llm_valido` só em teste) + `FonteCampos="llm"` | ~−60 se a Fase 5 não acontecer |
| A17 | forma referência vaga (`extrair_referencia_vaga=false`) — depende do ADR-005 (`tarefas_equipe.md:573-581`), não do encoder | ~−40 se abandonada |
| A18 | `configuracao.semente` — ninguém lê `cfg.semente` | −3, junto com A15 |

## 5. Fora do código

| ✔ | ID | O que é | Proposta |
|---|---|---|---|
| [ ] | N1 | notebooks `00`, `02`, `03`, `04` — mesmo template do `06`, diferem só em `VERSAO`/título | remover (ficam no git/tags). Reapontar `README.md:48-52`, `guia_kaggle.md:75,92`, `resultado_submissoes.md:72`, `tarefas_equipe.md:393`. Obs.: o `06` não está em nenhuma tag (cada notebook é commitado depois da própria tag) |
| [x] | N2 | notebook `05` com `VERSAO = "main"` e texto dizendo que usa `cmd_gerar_sintetico` (não usa) | fixar tag + corrigir texto (ADR-010) |
| [x] | F1 | `submission_feita_kaggle.csv` na raiz (sub-001, sem referência) | `git rm` (recuperável em `a85b329`) |
| [x] | F2 | `.claude/agent-memory/criar-estudo/` versionado — memória de estudo do Obsidian, sem relação com o projeto | `git rm --cached` + `.gitignore` |
| [ ] | D1 | links quebrados: `docs/guia_kaggle.md` (16×), `docs/ia_no_pipeline.md` (5×), `docs/analise_erros_baseline.md` (4×) — os arquivos foram para `docs/gerais/`; `tarefas_equipe.md:581` aponta linha velha | corrigir caminhos |
| [ ] | D2 | `BUILD_PROMPT.md`, `resultado_primeira_rodada.md`, `analise_erros_baseline.md` superados. **Refutado em parte:** ainda são citados (`resultado_submissoes.md:4,41`, `limites_de_decisao.md:39`, `tarefas_equipe.md:4,8`, `README.md:5` — que ainda diz "≈ 0,99") | **arquivar/marcar histórico**, não apagar |

## 6. Overfitting (lente C) — não é limpeza; vira spec própria ou teste novo

Nenhum de severidade alta. Nenhum muda o código agora.

| ✔ | ID | Sev. | O que é | Ação sugerida |
|---|---|---|---|---|
| [ ] | C3 | média | caminho `numero_desempatado` (`caminhos.py:70-75`) validado por **1** citação (gen_n2_010); o sintético nunca gera caso desempatável; célula n=1 na `taxa_acerto` | molde sintético com desempate |
| [ ] | C4 | média | relaxação por família de classe (`familias_classe.json`) nasceu de 1 caso (gen_n2_005 ARR×AIRR); o sintético que a exercita foi escrito para ela; o lado "emprestado da mesma família" não é medido | spec própria + molde "emprestada da mesma família" |
| [ ] | C5 | média | ruído OCR do sintético inverte `tabelas.ocr()` → cobertura 8/8 **circular**; amostra sustenta 5/8 letras com 1 doc cada; B→8, Z→2 invisíveis | ruído com confusões fora da tabela, medidas à parte |
| [ ] | C1 | baixa | `leis.json:5-6` "constituição fedcral" e `padroes.py:123` `fed[ce]ral` — OCR de uma letra copiado de 1 citação | generalizar e↔c ou aceitar e registrar |
| [ ] | C2 | baixa | abreviações de classe só da amostra: `arespel`, `eds`, `\bed\b`, `recl\.?`, `\brp\b`, `rec\.?\s*esp` (1–4 docs, 0 sintético, 0 base) | manter; gerador sintético passar a produzi-las |
| [ ] | C6 | baixa | `_HIFEN_PONTO`, `_HIFENS_DUPLOS`, `_ORDINAL` (até "quarto"), `Súm.` sem exemplo no sintético | manter; incluir em `ruido.py`/`moldes.py` |
| [ ] | C7 | baixa | teste R43 (`test_frente_c.py:274-288`) só varre `.py` e só igualdade exata — não pega tabelas JSON nem C1/C2 | estender R43 a `tabelas/*.json` |
| [ ] | C8 | baixa | R41 ok; o teste só renomeia sem permutar | teste opcional de permutação de nomes |
| [ ] | C9 | baixa | `ALFA=7`, `PRIOR=0.97` à mão (documentados); 12/12 células `usou_constante`; parte sintética do controle é circular (C5) | manter |
| [ ] | C10 | baixa | limites de regex (`_ENCHE{0,25}`, `{0,7}`, `{0,15}`; cabeçalho 3/120/40) sem origem documentada | manter; teste de propriedade nos limites |
| — | C11 | info | apelidos de lei "lei nº N/AAAA" nunca alcançados (`_LEI_COM_BARRA` resolve antes) | redundância, não overfitting |

**Casamentos por tabela (informativo — entrada sem casamento é generalização, não corte):** classes 84 pares
(34 amostra / 44 sintético / 31 em nenhum, 21 destas casam na base) · leis 55 (23/22/31) · tst 19 (5/11/7) ·
ufs 27 (17/23/2) · ocr 8 (5/8 circular) · vocabulario_ocr 31 (1/17/14) · referencia_vaga 5 (flag off) ·
familias_classe 5 (1/4/1).

## 7. Mantidos — não são achados

- **Falsos positivos do vulture:** 8 métodos de `sintetico/citacoes.py` (despacho por `getattr`, `:251`);
  `indice.py:42 text_factory` (atributo do sqlite).
- **Generalização (G1):** `pipeline.py:21-22,46-48`, fallback de `confianca.py`, `sobreposicao.py:51-60`,
  `relatorio.py:50,59-65`, `decidir.py:37` — não rodam na amostra, mas o conjunto cego pode exercitar.
- **Invariantes (G2):** `decidir.py:53-54` (R14), `validar.py`, `normalizacao.py:215-229` — guardas de
  R14/R38 que derrubam a submissão inteira se violadas.
- **`gerar_divisao` (G3):** só-teste, mas é a proveniência do `divisao.json` (ADR-009).
- **`sintetico/verdade.consistentes`:** cópia intencional — oráculo independente.

## Totais

| Grupo | Linhas |
|---|---|
| Seções 1 + 2 (validados) | `src/` −154 · `tests/` −75 |
| Marginais | até ~−64 |
| Dormentes (só se encoder/LLM/ref. vaga caírem) | até ~−130 |

**Próximo passo após a aprovação:** branch `limpeza-auditoria`, um commit por categoria, e a checagem
mecânica de novo (CSV idêntico nos conjuntos + `pytest` + R49), depois `/code-review high` (ou ultra) no
branch.
