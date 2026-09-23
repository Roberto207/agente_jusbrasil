# Spec — invariante do organizador: `real` nunca cai em `numero_ausente`

**Data:** 2026-09-22 · **ADR:** 009 (protocolo anti-overfitting) · **Item:** `tarefas_equipe.md`,
seção 3.2, Tier 1, item 2
**Status:** **implementada em 2026-09-22.** O `git pull` do colaborador (commit `e679784`, Beatriz)
resolveu um item diferente (`numero_contradito`/família de classe, `gen_n2_005`) — este invariante
(`numero_ausente`) continuava aberto, então o desenho abaixo foi implementado como planejado. Dois
testes novos em `tests/test_pipeline.py`, `R50` registrado em `specs/DESIGN.md`. Passou sem tocar
em código de produção — a garantia já era estrutural (ver seção "Contexto").

## Objetivo

Transformar em teste automatizado a garantia que a organização do desafio dá por escrito: *"todo
ruído aplicado a uma citação real é recuperável por normalização; um dígito nunca é trocado por outro
dígito."* Consequência direta, já registrada em `tarefas_equipe.md:513-515`: **toda citação `real` do
gabarito que caia no caminho de decisão `numero_ausente` é sempre um bug nosso**, nunca uma citação
genuinamente sem correspondência. Hoje isso não é verificado automaticamente — só sabemos que vale
"por acaso", de olhar a matriz de confusão manualmente a cada rodada.

## Contexto

`numero_ausente` é atribuído em um único ponto do pipeline — `src/verificador/decisao/decidir.py:36-37`,
quando `buscar_candidatos()` (`decisao/candidatos.py:19-35`) devolve lista vazia para as formas
`com_numero`/`sumula` (regra R8, `specs/DESIGN.md:201-210`). `CLASSE_DO_CAMINHO`
(`decisao/caminhos.py:13-38`) mapeia esse caminho para `"inventada"` — uma linha `real` do gabarito que
caia ali sai classificada errada por construção, não porque a citação seja de fato inexistente.

Levantamento de código (dois agentes de exploração + leitura direta) confirmou que a garantia do
organizador já é estrutural nos dados que produzimos:

- `src/verificador/tabelas/ocr.json` só mapeia **letra→dígito** (`l/I→1, O/o→0, S/s→5, g/G→9`); não
  existe entrada dígito→dígito.
- `src/verificador/texto/normalizacao.py::_ocr_no_token` só troca caracteres alfabéticos
  (`ch.isalpha()`); todo dígito já presente é preservado.
- Nenhuma das 8 transformações de `src/verificador/sintetico/ruido.py::TRANSFORMACOES` (incluindo as
  novas `m_vira_rn`/`rn_vira_m` do commit `110de74`) troca dígito por dígito ou apaga número de forma
  não recuperável.

Rodando o pipeline no HEAD atual (amostra oficial + sintético/sintético-controle regenerado, que já
cobre `letra_no_lugar_de_digito` e `m↔rn`), **zero** citações `real` caem em `numero_ausente` hoje —
confirmado pela matriz de confusão (nenhuma linha `real` vira `inventada`/`incompleta`/`sem_span`,
exceto o caso conhecido `gen_n2_005` na amostra, que cai em `numero_contradito`, não em
`numero_ausente`, e já tem teste próprio: `test_amostra_so_perde_o_caso_conhecido`). Ou seja: o teste
proposto aqui é um **guard de regressão**, não uma correção — não é esperada mudança de nota.

### Por que não dá pra reaproveitar `erros.md`

`_erro()` (`src/verificador/avaliacao/relatorio.py:82-89`) monta a chave do erro com o span do
**gabarito** quando há par casado. Mas `rastro.jsonl` (`avaliacao/rastro.py:19-59`) é chaveado pelo
span **emitido pelo nosso pipeline**. Os dois só coincidem quando a predição bate byte a byte com o
gabarito — não é garantido sob ruído. O teste precisa casar gabarito↔predição por IoU e consultar o
rastro pela chave da **predição**.

## Desenho proposto

Dois testes novos em `tests/test_pipeline.py`, um helper compartilhado, e o invariante registrado como
`R50` (o maior número hoje no repo, confirmado por grep, é `R49`).

### Helper — `_correspondencia_por_iou`

```python
from tests.helpers import iou_offsets
from verificador.decisao.caminhos import NUMERO_AUSENTE

def _correspondencia_por_iou(jsons: Path, doc: str, gold: dict, limiar: float = 0.5) -> dict | None:
    """Citação prevista cujo span mais se aproxima do span do gabarito, por IoU.

    None quando nenhuma prevista alcança o limiar: é perda de recall, fora de escopo deste
    invariante (coberta por test_amostra_nunca_chama_inventada_de_real_e_acha_todos_os_spans /
    test_sintetico_recall_de_spans_tem_piso).
    """
    esperado = (int(gold["inicio"]), int(gold["fim"]))
    citacoes = json.loads((jsons / f"{doc}.json").read_text(encoding="utf-8"))["citacoes"]
    if not citacoes:
        return None
    melhor = max(citacoes, key=lambda c: iou_offsets(esperado, (c["inicio"], c["fim"])))
    return melhor if iou_offsets(esperado, (melhor["inicio"], melhor["fim"])) >= limiar else None
```

Usa `max(..., key=iou_offsets)` (melhor IoU), não "primeira que bate" — mesmo idioma de
`tests/test_integracao_ab.py:118`. Importa porque, embora o gabarito seja disjunto (prova em
`desafio-jusbrasil-bracis-2026/kaggle_metric.py:224-234`: com `IOU_MIN=0.5` e golds disjuntos uma
predição não casa com dois golds ao mesmo tempo), **nossas próprias predições não são garantidamente
disjuntas entre si** (R3, `saida/validar.py:56-63`, só proíbe pares de predições com IoU≥0,5 *entre
si*, mais fraco que disjunção) — em teoria uma linha do gabarito poderia ter IoU≥0,5 com mais de uma
predição nossa. `max()` resolve isso sem código defensivo extra.

### Teste 1 — amostra oficial

Logo após `test_toda_real_cumpre_r14_e_o_rastro_bate_com_o_json` (mesma seção, mesma fixture
`run_amostra`). Reaproveita a fixture `gabarito` já existente em `tests/conftest.py:32-35`
(`encoding="utf-8-sig"` — o CSV oficial tem BOM, confirmado com `file`):

```python
def test_amostra_toda_real_nunca_cai_em_numero_ausente(run_amostra, gabarito) -> None:
    """R50: a organização garante que todo ruído sobre uma citação real é recuperável por
    normalização — um dígito nunca é trocado por outro dígito. Logo nenhuma citação `real` do
    gabarito pode terminar em `numero_ausente`; se acontecer é sempre bug nosso.
    """
    rastro = carregar_rastro(run_amostra)
    jsons = run_amostra / "jsons"
    violadoras = []
    for linha in gabarito:
        if linha["classificacao"] != "real":
            continue
        pred = _correspondencia_por_iou(jsons, linha["documento_id"], linha)
        if pred is None:
            continue  # recall é outra métrica
        caminho = rastro[(linha["documento_id"], pred["inicio"], pred["fim"])]["caminho"]
        if caminho == NUMERO_AUSENTE:
            violadoras.append((linha["documento_id"], linha["inicio"], linha["fim"]))
    assert not violadoras, f"real do gabarito virou numero_ausente: {violadoras}"
```

### Teste 2 — sintético

Depois de `test_r35_par_limpo_e_ruidoso_concorda`, antes de `test_campos_nao_lidos_e_um_caminho_incompleta`.
O gabarito sintético é gerado por nós (sem BOM) — abrir com `encoding="utf-8"`, igual ao R35:

```python
def test_sintetico_toda_real_nunca_cai_em_numero_ausente(run_sintetico) -> None:
    """R50, versão sintética: cobre também os pares ruidosos (letra_no_lugar_de_digito, m↔rn etc.)."""
    dados = run_sintetico / "dados"
    jsons = run_sintetico / "runs" / "sint" / "jsons"
    rastro = carregar_rastro(run_sintetico / "runs" / "sint")
    with (dados / "goldenset_offsets.csv").open(encoding="utf-8", newline="") as fh:
        gold_reais = [l for l in csv.DictReader(fh) if l["classificacao"] == "real"]

    violadoras = []
    for linha in gold_reais:
        pred = _correspondencia_por_iou(jsons, linha["documento_id"], linha)
        if pred is None:
            continue
        caminho = rastro[(linha["documento_id"], pred["inicio"], pred["fim"])]["caminho"]
        if caminho == NUMERO_AUSENTE:
            violadoras.append((linha["documento_id"], linha["inicio"], linha["fim"]))
    assert not violadoras, f"real do gabarito virou numero_ausente: {violadoras}"
```

Este teste já exercita a parte "dígito↔letra" e "m↔rn" da garantia, porque o sintético aplica essas
transformações a citações `real`.

## O que NÃO foi feito, de propósito

**Nenhuma linha de código foi tocada nesta sessão.** Combinado com o usuário: outro colaborador
aparentemente já resolveu este item em paralelo; o plano acima fica registrado para comparar depois do
`git pull` — se a solução dele cobrir o mesmo invariante por outro caminho, esta spec vira só
documentação da análise; se não cobrir (ex.: só corrige um caso específico sem virar teste de
regressão), esta spec vira a base da implementação.

Também deixado de fora, por decisão já tomada durante o desenho (não é sobre "não fazer agora", é
"não fazer nunca sem medir"): trocar a lógica de casamento por IoU de `test_r35_par_limpo_e_ruidoso_concorda`
(hoje "primeira que bate", não "melhor IoU") pelo helper novo — mudaria a semântica de um teste que já
existe e passa (~0,96 de concordância), sem necessidade para este item.

## Verificação (planejada — a rodar depois da implementação, seja dela ou nossa)

```bash
source .venv/bin/activate
python -m pytest tests/test_pipeline.py -k numero_ausente -v   # só os 2 testes novos
python -m pytest tests/test_pipeline.py -v                      # arquivo inteiro
python -m pytest -q                                              # suíte completa: 181 → 183 verdes
```

Esperado: os dois testes novos passam sem qualquer mudança em código de produção — a garantia já é
estrutural no gerador e na normalização (seção "Contexto" acima). Se `violadoras` não vier vazio um
dia, o assert já lista `(documento_id, inicio, fim)` de cada linha do gabarito violada.

## Também a registrar, se esta spec for a que entra

- `specs/DESIGN.md:80` — tag list do `[7] Avaliação`: `R28, R41, R43, R49` → `R28, R41, R43, R49, R50`.
- `specs/DESIGN.md:234-235` — acrescentar à frase de testes metamórficos: *"Toda citação `real` do
  gabarito nunca cai no caminho `numero_ausente` (R50; a organização garante que ruído sobre citação
  real é sempre recuperável por normalização)."*
- `tarefas_equipe.md:513` — marcar `- [ ]` → `- [x]` com parágrafo de fechamento, no estilo do que o
  Caio deixou no commit `110de74`.
