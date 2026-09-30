# Regras de envio da solução final — mensagem da Jusbrasil (recebida em 30/09/2026)

> Este documento **substitui** o que `specs/scope.md`, `specs/DEFINE.md` e `tarefas_equipe.md` diziam sobre
> prazo, forma de avaliação e entrega. Onde houver conflito, vale este. A mensagem está transcrita abaixo
> (seção 1); a leitura da equipe e o cotejo com o código estão nas seções 2 e 3; as tarefas saem em
> `tarefas_equipe.md`, "Fase 7".

## 1. Mensagem da organização (transcrição resumida, sem perder regra)

**Prazo.** Submissões fecham em **01/10/2026, 23h59 (Brasília)** — *um dia depois* do que estava em
`scope.md` (30/09). Até lá o repositório com a versão final precisa estar disponível para a organização.

**Avaliação final.**
- Usa um **novo `.db` e um novo conjunto de documentos**, no mesmo formato da amostra de desenvolvimento.
- A equipe **não tem acesso** a esse conjunto. **A organização executa o código submetido** sobre ele.
- A nota oficial vem **da execução deles**, com a mesma métrica e os mesmos scripts de avaliação. **Não há
  comparação entre CSVs; o leaderboard do Kaggle não entra no ranking final.**
- Pequenas diferenças numéricas em `confianca` por hardware não são problema. Recomendam **fixar seeds** e
  **evitar amostragem não determinística**.

**O que enviar** para `desafio-bracis@jusbrasil.com.br`:
1. Nome da equipe e integrantes.
2. Link do repositório — **público**, ou **privado com leitura concedida** a: `dvianna`, `guardiaum`,
   `marinaramalhete`, `resendeacm`, `vickyaires` (todos em github.com).
3. **Hash do commit** da versão final.

**O repositório deve conter:**
- código completo da solução;
- README com a abordagem e o passo a passo;
- **ambiente declarado (Docker)**;
- **pesos dos modelos incluídos ou referenciados em revisão fixa, disponíveis para download *antes* da
  execução**;
- **ponto de entrada único** que recebe o caminho do `.db` e da pasta com os `.txt` e gera a saída no mesmo
  formato das submissões. Sugestão deles: `bash run.sh <caminho_db> <pasta_txt> <arquivo_saida>`.

**Regras de execução.**
- **GPU** com até 24 GB de VRAM.
- **Offline:** a execução **não pode depender de internet nem de APIs externas.**
- **Do zero, em máquina limpa:** sem caminhos absolutos, sem passos manuais, sem arquivos que só existam na
  máquina da equipe.
- **Enriquecimento do `.db`** (variáveis, índices, metadados) é permitido, mas como o `.db` da avaliação é
  outro, **enviar o código que gera o enriquecimento a partir de um `.db` no formato original**; ele roda
  sobre a base nova e obedece às mesmas regras.
- Modelos usados **só no desenvolvimento** (dados sintéticos, anotação) podem passar do limite de hardware,
  desde que não participem da execução.
- Disco: sem limite; referência de ~100 GB.

**Datas.** 01/10 23h59 fecha; **01–10/10** execução no conjunto final, reprodutibilidade e ranking;
**19–22/10** BRACIS 2026 em Cuiabá-MT, com apresentação técnica das melhores soluções.

## 2. O que muda em relação ao que a equipe vinha planejando

| Antes | Agora | Consequência |
|---|---|---|
| Prazo 30/09 23h59 | **01/10 23h59** | +1 dia de folga. Não é motivo para mexer no modelo; é folga para o empacotamento. |
| Nota = leaderboard do Kaggle (e notebook) | **Nota = execução da organização no conjunto novo**; Kaggle não conta | O `sub-NNN`/notebook deixam de ser o entregável. O entregável é **repositório + commit + `run.sh`**. |
| Fase 2 (conjunto cego) era conferida pelo Kaggle | Ninguém confere por nós | O **teste de máquina limpa** (Docker, sem internet, `.db` e pasta novos) passa a ser a validação principal. |
| Foco em calibração/`confianca` | Diferenças numéricas pequenas são aceitas | Calibração adicional não compensa (já estava pausada). |
| Encoder baixava pesos do HF na execução (aceito no DESIGN) | **Execução offline** | Precisa ser corrigido — ver 3.2. |
| Entrada por `python -m verificador indexar` + `rodar`, com `--dados` | **Um comando**: `.db`, pasta de `.txt`, arquivo de saída | Precisa de `run.sh` — ver 3.1. |
| Repositório privado "combinar a entrega" | Privado com **acesso de leitura a 5 usuários**, ou público | Tarefa concreta — ver 3.6. |

## 3. Cotejo com o código (verificado em 30/09, sem executar nada)

### 3.1 Não há ponto de entrada único
`run.sh` não existe. Hoje são dois comandos (`indexar`, `rodar`) com `--entrada`, `--run`, `--saida`,
`--dados`. Além disso, `cmd_rodar` (`src/verificador/cli.py:264-270`) exige **uma pasta de dados** contendo
`json_to_submission.py` **e** um `.db` **com o nome fixo `desafio1_bracis.db`** (`caminho_db`, linha 169). A
organização passa `<caminho_db>` livre (nome qualquer) e uma pasta de `.txt` que pode não estar ao lado do
`.db`. O `json_to_submission.py` oficial pode não estar no ambiente deles: **a solução precisa trazer a sua
própria cópia** do conversor (ou gerar o CSV sem ele) — e conferir que o formato de saída é idêntico ao do
oficial. Além disso, `resolver_dados` tenta `VERIFICADOR_DADOS`, pasta-pai da entrada e uma pasta relativa ao
diretório atual: nada disso é confiável na máquina deles.

### 3.2 O encoder viola "offline"
`src/verificador/extracao/encoder.py:100-101` faz `from_pretrained(link, revision=revisao)`: baixa ~420 MB do
Hugging Face na primeira execução. O README diz isso como "única chamada de rede". **Pelas regras novas isso
não pode acontecer na execução.** Opções (a decidir — ver "Decisões" na Fase 7):
- **(A) Pesos dentro da imagem Docker**, baixados no `docker build` (`snapshot_download` com a revisão fixa)
  e carregados com `local_files_only=True`. Cumpre "referenciados em revisão fixa, disponíveis antes da
  execução". Só funciona se a organização **construir** a imagem com rede.
- **(B) Pesos no próprio repositório** (~420 MB; exige Git LFS ou release do GitHub) e carregados por caminho
  relativo. Independe de rede em qualquer momento; ocupa espaço no repositório.
- **(C) Os dois:** pesos no repo/LFS e `run.sh` que aceita cache do HF. Mais robusto, mais trabalho.
**Decidido em 30/09: (A)**, com repositório público. Não usar Git LFS (cota de banda do GitHub). No lugar de fallback automático, dois comandos: `run.sh` (com encoder) e `run_sem_encoder.sh`; o erro do primeiro aponta o segundo. Ver `tarefas_equipe.md`, Fase 7.

Recomendação original (superada): Em qualquer caso, definir
`HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1` no `run.sh`, para a falha ser alta e imediata em vez de
silenciosa, e **testar sem rede**.

### 3.3 O que já está de acordo
- Determinismo: `semente = 0` no `verificador.toml`, que desde 30/09 alimenta o `torch.manual_seed` do
  encoder (antes era um 0 fixo no código); duas execuções idênticas (R49, `sub-006`). O `run.sh` deve usar
  o toml do repositório e não sobrescrever `VERIFICADOR_SEMENTE`.
- Encoder em CPU: cabe folgado no limite de 24 GB (a GPU nem é usada). Sem LLM na execução: o código do LLM
  saiu na limpeza de 30/09 (não existe mais a chave `usar_llm`).
- Índice por regras e base: **é o "enriquecimento do `.db`"** — `construir_indice(db)` roda a partir de
  qualquer `.db` no formato original e não grava nada no `.db` (abre em modo leitura). Só falta declarar isso
  no README como o passo de enriquecimento e conferir que **não** depende de arquivo pré-gerado local
  (`runs/`, `tabelas/` geradas etc.).
- Modelos só de desenvolvimento (LLM do sintético) ficam fora da execução: OK.
- Pesos e dataset públicos no HF com revisão fixa (R45, R46).

### 3.4 Riscos específicos do conjunto novo
- **Tamanho da base.** A amostra tem 1.014 (ou 1.016, ver `divergencia-dados-kaggle-220926`). A base nova pode
  ter outro tamanho e outros formatos de número. Conferir que nada assume 1.014 registros e que
  `tabelas/` não tem literais da amostra (R41, R43).
- **Nome e caminho do `.db`** e da pasta de `.txt` livres (3.1).
- **`.txt` com `\r\n` e offsets exatos** (R2): já tratado (`newline=""`).
- **Tempo de execução.** A organização executa num conjunto possivelmente maior; medir o tempo por
  documento e garantir um teto razoável em CPU (encoder) sem estourar.
- **Reprodutibilidade em máquina limpa** é agora *o* critério. O Kaggle T4 já provou o determinismo, mas não
  provou "do zero, sem rede, fora do nosso diretório".

### 3.5 Higiene do repositório antes de entregar
- Segredos: o `.env` está no `.gitignore`, mas a lista de 25/09 registra o **token do HF e um
  `github_pat_…` que apareceram numa sessão**. Revogar e regerar antes de conceder acesso ao repositório
  (Fase 6 já listava; agora é bloqueante para a entrega).
- Auditar o histórico do git por credenciais (`git log -p -S`), pois o histórico vai junto.
- Dados oficiais do desafio (`desafio-jusbrasil-bracis-2026/`, `.db`, `txt/`) estão no `.gitignore` — **manter
  fora de repositório público**. Se o repo for público, conferir também `results(1)/`, `sintetico_hf/`,
  `lener-br` (licença). (`submission_feita_kaggle.csv` já saiu na limpeza de 30/09.)
- Caminhos absolutos: procurar `/home/`, `C:\`, `/kaggle/` no código, nos testes e no README.

### 3.6 Entrega por e-mail
A mensagem não pede o `submission.csv`. Pede **nome da equipe, integrantes, link do repositório e hash do
commit**. Se o repositório for privado, os 5 usuários acima precisam de acesso de leitura *antes* do envio.
Confirmar o hash com `git rev-parse HEAD` do commit exato que passou no teste de máquina limpa (não de outro
mais novo).
