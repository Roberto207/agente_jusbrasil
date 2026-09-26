# BUILD_PROMPT — Esqueleto andante do verificador de citações

> **Documento histórico (25/09).** Prompt do esqueleto andante de 18/09, já implementado. O estado
> atual do sistema está em `README.md`, `tarefas_equipe.md` e `docs/resultado_submissoes.md`.

**Uso:** este arquivo é autocontido — pode ser dado a um agente ou a uma pessoa sem mais contexto
que os documentos que ele referencia. É o prompt de início da Fase 4 (Build) da skill `sdd`, para a
primeira etapa da "Ordem de implementação" do `DESIGN.md` (itens 1 e 2).
**Não** implemente extração, decisão real, encoder ou LLM aqui — isso vem depois (ver "Próximas
etapas" no fim).

---

## Contexto (leia antes de codar)

Projeto: verificador automático de citações jurídicas para o desafio Jusbrasil × BRACIS 2026
(Kaggle). Dado um parecer `.txt`, o sistema encontra citações de jurisprudência/lei e classifica
cada uma em `real` (com o id do registro correspondente), `inventada` ou `incompleta`; o resultado
vira `submission.csv` no formato do Kaggle.

Documentos a ler, nesta ordem, antes de escrever qualquer linha de código:

1. `scope.md` — o que o desafio pede e as regras da competição.
2. `DEFINE.md` (v2.2) — os requisitos numerados (R#) citados abaixo são de lá; leia ao menos o
   glossário e as seções "Formato de saída" e "Reprodutibilidade".
3. `DESIGN.md` (v2.1) — a arquitetura completa; as seções "Contratos entre módulos", "Estrutura do
   repositório" e "Ordem de implementação" são o insumo direto deste prompt.
4. `docs/gerais/guia_kaggle.md` — como o notebook do Kaggle busca o código do repositório.
5. A pasta `desafio-jusbrasil-bracis-2026/` (fora do git, já presente na raiz do projeto): contém
   `txt/` (26 documentos), `desafio1_bracis.db`, `goldenset_offsets.csv`, `json_to_submission.py`,
   `kaggle_metric.py`, `sample_submission.csv`. **Leia `json_to_submission.py` e
   `kaggle_metric.py` por completo** — o formato exato do JSON e as regras de validação estão
   neles, não só descritos aqui.

## O que é "o esqueleto andante" (walking skeleton)

Não é um esboço nem um placeholder solto: é a **menor versão do pipeline completo que já funciona
de ponta a ponta**, da leitura dos `.txt` até uma nota calculada pelo `kaggle_metric.py` — só que
sem nenhuma citação real (cada documento sai com lista de citações vazia). O objetivo não é
qualidade de resultado, é provar que **a tubulação inteira** existe e se conecta: contratos →
CLI → conversão para CSV → script oficial de avaliação → notebook do Kaggle → submissão. Toda
lógica de extração, decisão, encoder e LLM entra depois, encaixando nessa tubulação já testada —
sem precisar redesenhar o encanamento no meio do caminho.

## Objetivo desta etapa

Implementar os itens 1 e 2 da "Ordem de implementação" do `DESIGN.md`:

1. `contratos.py`, `configuracao.py` e o esqueleto de `cli.py`.
2. O esqueleto andante propriamente dito: `rodar` gera um JSON vazio por documento, converte com o
   `json_to_submission.py` oficial, `avaliar` roda o `kaggle_metric.py`; `Dockerfile` mínimo a
   partir da imagem do Kaggle; primeiro notebook em `notebooks/kaggle/` clonando o repositório.

## Estrutura a criar

```
agente_jusbrasil/
├── src/verificador/
│   ├── __init__.py
│   ├── cli.py                # subcomandos: ambiente, indexar, rodar, avaliar, submeter
│   ├── contratos.py          # dataclasses/NamedTuples da seção "Contratos entre módulos"
│   └── configuracao.py       # chaves de configuração (ver abaixo)
├── tests/
│   └── test_esqueleto.py     # smoke test de ponta a ponta (ver "Critério de pronto")
├── notebooks/kaggle/
│   └── 00_esqueleto.ipynb    # clona o repo numa tag, instala requirements, roda `rodar`+`avaliar`
├── Dockerfile
├── requirements.txt
└── pyproject.toml            # ou setup.py — o que permitir `pip install -e .`
```

Não criar ainda: `base/`, `tabelas/`, `texto/`, `extracao/`, `decisao/`, `saida/`, `avaliacao/`,
`sintetico/`, `treino/` — essas pastas são das frentes A/B/C/D, na etapa seguinte. `cli.py` pode
importar delas via `try/except ImportError` ou apenas não referenciá-las ainda.

## Contratos (`contratos.py`)

Copiar exatamente as estruturas do `DESIGN.md`, seção "Contratos entre módulos" — `TextoPreparado`,
`Candidata`, `Campos`, `RegistroIndice`, `Resolucao`, `CitacaoVerificada` — como `@dataclass(frozen=True)`
ou `NamedTuple`. Nesta etapa elas só precisam existir com os tipos certos; nada as instancia de
verdade ainda (o esqueleto não gera candidatas nem resoluções reais).

## `configuracao.py`

Uma estrutura simples (dataclass) com pelo menos:

```python
usar_encoder: bool = False
usar_llm: bool = False
extrair_referencia_vaga: bool = False   # ADR-005, desligado por padrão
semente: int = 0
dtype: str = "float16"
```

Lida de variáveis de ambiente ou de um YAML/TOML — a decisão de formato fica livre, mas precisa ser
versionada (o hash dela entra no manifesto, ver abaixo).

## `cli.py` — subcomandos

Usar `argparse` ou `click` (escolha livre, documentar no README). Comportamento de cada um **nesta
etapa**:

- **`ambiente`** — imprime e grava em `runs/<run_id>/manifesto.json` (ou um arquivo à parte, se
  chamado fora de uma rodada): commit git atual (`git rev-parse HEAD`), se a árvore está suja
  (`git status --porcelain`), versão do Python, SO, GPU e driver se disponíveis (`nvidia-smi`, com
  fallback gracioso se não houver GPU), hash do `requirements.txt`.
- **`indexar --dados <pasta>`** — nesta etapa, só confere que `<pasta>/desafio1_bracis.db` existe e
  abre com `sqlite3` (conexão de leitura). Não precisa montar o índice de verdade ainda (isso é da
  frente A, próxima etapa) — pode imprimir a contagem de linhas de `documentos` como prova de que
  leu.
- **`rodar --entrada <pasta de .txt> --run <run_id> [--saida <pasta>]`** — para cada arquivo `.txt`
  em `<entrada>`, grava `runs/<run_id>/jsons/<documento_id>.json` com:
  ```json
  {"documento_id": "gen_n1_001", "citacoes": []}
  ```
  (`documento_id` = nome do arquivo sem `.txt`). Depois **chama**
  `desafio-jusbrasil-bracis-2026/json_to_submission.py` (via `subprocess` ou importando a função
  `encode`/`main` dele — não reimplementar a lógica, R16) sobre `runs/<run_id>/jsons/` e grava
  `runs/<run_id>/submission.csv`. Por fim grava `runs/<run_id>/manifesto.json` (reaproveitando a
  lógica de `ambiente`, mais `run_id`, timestamp, argumentos usados, config).
- **`avaliar --run <run_id> [--gabarito <caminho>]`** — monta o `solution` que
  `kaggle_metric.py:avaliar()` espera (colunas `documento_id, nivel, citacoes, [Usage]`) a partir de
  `goldenset_offsets.csv` (que tem uma linha por citação — é preciso agrupar por documento e montar
  a célula `inicio,fim,classe,doc_ids` conforme o formato descrito no cabeçalho de
  `kaggle_metric.py`) e o `submission` a partir de `runs/<run_id>/submission.csv`. Chama
  `avaliar(solution, submission)` (importar de `kaggle_metric.py`, não reimplementar) e grava
  `runs/<run_id>/relatorio.md` com o resultado (`score_final`, e por nível: `macro_f1`, `f1_por_classe`,
  `tau`, `s`, `b`, `score`).
- **`submeter --run <run_id>`** — nesta etapa, implementar só a parte que **não depende de conteúdo
  real**: falhar se a árvore git estiver suja; falhar se `runs/<run_id>/submission.csv` não existir;
  senão, imprimir o que faria (criar tag `sub-NNN`) sem de fato criar — deixar um `TODO` claro
  apontando para quando a lógica de decisão existir (a comparação de duas execuções idênticas, R49,
  só faz sentido testar quando houver algo não trivial a comparar).

## `Dockerfile`

```dockerfile
FROM gcr.io/kaggle-gpu-images/python:<TAG-FIXA-A-DEFINIR>
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install --no-cache-dir --no-deps -e .
ENTRYPOINT ["python", "-m", "verificador"]
```

Escolher e fixar `<TAG-FIXA-A-DEFINIR>` (não usar `latest`) — checar as tags disponíveis em
[Kaggle/docker-python](https://github.com/Kaggle/docker-python) e registrar a escolhida também em
`docs/gerais/guia_kaggle.md` (ela deve ser a mesma versão fixada no notebook, ver ADR-014). Se a imagem for
grande demais para testar localmente, documentar isso no README e seguir — o `Dockerfile` é para a
entrega, não para o dia a dia da equipe.

## `notebooks/kaggle/00_esqueleto.ipynb`

Seguir exatamente as 5 células descritas em `docs/gerais/guia_kaggle.md` (clonar com token dos Secrets numa
tag fixa → instalar `requirements.txt` → `verificador ambiente` → `verificador indexar` +
`verificador rodar` + `verificador avaliar` apontando para o input da competição → mostrar onde
ficaram as saídas em `/kaggle/working/`). Não é preciso já existir uma tag `sub-001` real — usar o
branch de desenvolvimento nesta etapa e trocar por tag quando a primeira submissão de verdade for
gerada.

## Critério de pronto (rode antes de considerar terminado)

1. `pip install -e .` funciona numa venv limpa.
2. `python -m verificador ambiente` roda sem erro e grava um JSON legível.
3. `python -m verificador indexar --dados desafio-jusbrasil-bracis-2026` roda sem erro e mostra a
   contagem de registros (1014).
4. `python -m verificador rodar --entrada desafio-jusbrasil-bracis-2026/txt --run smoke` produz
   `runs/smoke/submission.csv` com 26 linhas, todas `documento_id,-` (célula vazia = `-`, nunca em
   branco — conferir contra `sample_submission.csv` como referência de formato).
5. `python -m verificador avaliar --run smoke` roda **sem lançar `ParticipantVisibleError`** e grava
   um relatório com `score_final` (vai ser baixo, perto de 0 — é esperado, não há citação nenhuma
   ainda; o teste é que o cálculo *funciona*, não que o número seja bom).
6. Um teste em `tests/test_esqueleto.py` automatiza os passos 3–5 (pode chamar as funções
   diretamente, sem passar pelo `argparse`) e roda em CI local com `pytest`.
7. `docker build .` completa sem erro (se der para testar localmente; senão, documentar como não
   testado e por quê).
8. `git status` limpo, tudo commitado — este é o commit que qualquer submissão futura vai referenciar
   como ponto de partida (ver R31).

## Requisitos do `DEFINE.md` que esta etapa precisa satisfazer

R15, R16, R17, R18, R19, R38, R42 (formato de saída e uso do conversor oficial), R28 (avaliação via
`kaggle_metric.py`), R30 (um único comando/fluxo, dentro do ambiente declarado). **Fora do escopo
desta etapa** (vêm depois, quando houver lógica real para testar): R1–R14, R21, R22, R26, R31 (parte
de tag/comparação), R44–R49.

## Não fazer nesta etapa

- Nenhuma extração de citação real (regex, encoder ou LLM).
- Nenhuma lógica de decisão/consulta à base além de abrir a conexão e contar linhas.
- Nenhuma chamada de rede, GPU ou modelo.
- Não reimplementar `json_to_submission.py` nem `kaggle_metric.py` — importar/chamar os originais.
- Não criar as pastas `base/`, `texto/`, `extracao/`, `decisao/`, `saida/` etc. — isso é da etapa
  seguinte, por frente.

---

## Próximas etapas (depois deste prompt, na ordem do `DESIGN.md`)

3. **Frentes em paralelo, contra os contratos já existentes:**
   - **Frente A** — `base/`: parser de número próprio por tribunal (STJ/STF/STM/TSE/TST), súmulas,
     dispositivos de lei; tabelas de apelidos de lei/classes/UFs/confusões de OCR; índice real
     (implementa `indexar()` de verdade). Critério de pronto: os 96 `real` do gabarito resolvem para
     o `id_canonico` certo.
   - **Frente B** — `texto/` + `extracao/`: delimitação de cabeçalho, normalização com mapa de
     offsets, os quatro padrões de regex (formas a/b/c/d), leitura de campos. Critério: os 192
     trechos do gabarito batem com `texto[inicio:fim]`; recall de spans por IoU ≥ 0,5.
   - **Frente C** — `sintetico/` (gerador por código, sem LLM ainda) + `avaliacao/` (relatório
     comparando execuções, divisão fixa da amostra em ajuste/medida).
   - **Frente D** — `decisao/`: a tabela de caminhos do `DESIGN.md` (`sem_numero`, `numero_ausente`,
     `numero_unico`...), implementada sobre `Campos` e `RegistroIndice` falsos até A/B entregarem os
     reais.
4. **Primeira versão só-regras integrada** (A+B+D ligados, sem encoder/LLM) → gerar uma submissão de
   verdade → analisar os erros contra o gabarito. Essa é a linha de base de tudo que vem depois.
5. Gerador sintético com LLM (GPU do Kaggle) → treino do encoder NER → publicação dos pesos
   (Hugging Face, revisão fixa, licença OSI) → encoder integrado e medido contra a linha de base.
6. Leitor LLM de campos difíceis (fila de casos que as regras não leem), medido contra a versão sem
   LLM — só entra se melhorar o score no conjunto de controle.
7. Confiança calibrada por caminho de decisão (tabela medida no conjunto de controle).
8. Congelamento: publicação final de pesos e dataset sintético (antes de 30/09 23h59 BRT), README,
   `Dockerfile` e notebook com versões fixas conferidas, verificação de determinismo (duas execuções
   → CSV idêntico), `code-review`.

Cada uma dessas etapas tem seu próprio critério de pronto detalhado na tabela "Frentes de trabalho"
do `DESIGN.md` — vale reler antes de começar cada uma.
