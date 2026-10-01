# Registro de mudanças — adequação à entrega final (regras da Jusbrasil de 30/09)

Diário das mudanças feitas para cumprir `docs/gerais/regras_envio_final_jusbrasil.md` e a checklist da
Fase 7 de `tarefas_equipe.md`. Uma seção por mudança, na ordem em que foram feitas: o que mudou, por quê,
como foi verificado e o que ficou pendente. Prazo da entrega: **01/10/2026, 23h59 (BRT)**.

---

## 1. Ponto de entrada único: `run.sh` e `run_sem_encoder.sh` (30/09)

> **Corrigido na seção 4 (01/10).** A primeira versão desta mudança violava o `specs/DEFINE.md`:
> reimplementava o conversor (contra o **R16**, que exige o `json_to_submission.py` oficial sem modificação)
> e descartava os JSONs por documento e o manifesto (contra o **R15** e a "Identidade" do `DESIGN.md`). O
> `src/verificador/saida/submissao.py` descrito abaixo **não existe mais**. Os scripts, o `.gitattributes`
> e os testes de erro continuam valendo.

**Item da checklist:** "`run.sh <caminho_db> <pasta_txt> <arquivo_saida>` (com encoder) e
`run_sem_encoder.sh` (mesmos argumentos, só regex)". Para funcionar, ele exigiu também dois outros itens da
lista, feitos junto: **desacoplar o CLI do `desafio1_bracis.db`/pasta de dados** e **levar o conversor
JSON→CSV para dentro do repositório**.

### O problema

A organização roda **um comando** com um `.db` de nome livre e uma pasta de `.txt` em qualquer lugar. O
`verificador rodar` não servia para isso:

- `caminho_db()` (`cli.py`) fixa o nome `desafio1_bracis.db` dentro de uma "pasta de dados";
- `cmd_rodar` exige o `json_to_submission.py` **oficial** nessa mesma pasta — ele não vem no ambiente deles;
- `resolver_dados()` adivinha a pasta (variável `VERIFICADOR_DADOS`, pasta-pai da entrada, diretório atual);
- grava em `runs/<run_id>/` relativo ao diretório atual, com manifesto, rastro etc.

### O que foi feito

| Arquivo | Mudança |
|---|---|
| `src/verificador/saida/submissao.py` (novo) | Cópia da lógica do `json_to_submission.py` oficial (`codificar` = `encode`). `escrever_submission()` grava num `<saida>.parcial` e só então renomeia: falha no meio não deixa CSV parcial. |
| `src/verificador/cli.py` | Novo subcomando **`executar <db> <pasta_txt> <arquivo_saida> [--sem-encoder]`** (`cmd_executar`). Recebe os três caminhos por argumento, sem nome fixo; JSONs intermediários numa pasta temporária apagada no fim; só sai o CSV. Helper `_carregar_encoder`: qualquer falha ao carregar o encoder (sem `torch`, pesos fora do cache, rede bloqueada) vira erro que mostra o repositório@revisão dos pesos e **aponta o `run_sem_encoder.sh`**. Erros próprios para base ausente, base inválida (`sqlite3.Error`), pasta inexistente e pasta sem `.txt`. Todos saem com código ≠ 0 e mensagem `erro: …` no stderr. |
| `run.sh` (novo, raiz) | `bash run.sh <caminho_db> <pasta_txt> <arquivo_saida>`. Define `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1` (sem rede: falha na hora em vez de tentar baixar) e `PYTHONHASHSEED=0`; remove qualquer `VERIFICADOR_*` do ambiente e aponta `VERIFICADOR_CONFIG` para o `verificador.toml` do repositório (a configuração entregue é a que vale, inclusive a semente); põe `src/` no `PYTHONPATH` (funciona sem `pip install -e .`); aceita `PYTHON=…` para escolher o interpretador. Uso errado → código 2. |
| `run_sem_encoder.sh` (novo, raiz) | Chama o `run.sh` com `--sem-encoder` (flag interna). Mesmos argumentos, mesma saída, sem `torch` e sem pesos. |
| `.gitattributes` (novo) | `*.sh text eol=lf`: o repositório é editado no Windows; com CRLF o `bash` quebra no Linux da organização. Os dois scripts estão com o bit de execução no git (`100755`). |
| `tests/test_executar.py` (novo) | 4 testes: CSV do `executar` (base renomeada em outra pasta, `.txt` em outra pasta) **byte a byte igual** ao do caminho antigo com o conversor oficial; recusa base ausente; recusa pasta sem `.txt`; conversor não deixa CSV quando falha. |

O `verificador rodar` e os demais subcomandos **não mudaram**: continuam servindo ao fluxo de
desenvolvimento (avaliar, comparar, submeter).

### Verificação

- **Nomes e caminhos livres:** `.db` copiado como `base/outra_base.db` e `.txt` copiados para `docs/`, num
  diretório fora do repositório → `bash run_sem_encoder.sh base/outra_base.db docs out/sub.csv` → 26
  documentos, ~6 s, código 0.
- **Mesmo resultado:** `sha256` do CSV = **`4c6e3538…0f9ffb`**, idêntico ao do `verificador rodar` com o
  `json_to_submission.py` oficial e ao sha de referência da amostra registrado em `tarefas_equipe.md`.
- **Casos de erro** (todos com código ≠ 0 e **nenhum CSV gravado**):
  - `run.sh` (com encoder) num ambiente sem `torch` → mensagem com `Roberto2799/jusbrasil-encoder-citacoes@d91d0914…`
    e o comando sem encoder;
  - `.db` inexistente; arquivo que não é SQLite; pasta sem `.txt`; número errado de argumentos (código 2).
- **Configuração não sobrescrita:** com `VERIFICADOR_USAR_ENCODER=0` exportado, o `run.sh` ainda tentou o
  encoder — vale o `verificador.toml`.
- **Suíte:** `pytest` → 283 passaram, 5 pulados (os mesmos de antes), em ~100 s.

### Limitações e pendências (próximos itens da checklist)

- **O modo com encoder ainda não roda offline.** O `run.sh` já bloqueia a rede, mas o `encoder.py` ainda
  chama `from_pretrained` sem `local_files_only=True` e ninguém pôs os pesos no cache. Hoje, sem os pesos
  no cache, o `run.sh` padrão **falha** (com a mensagem certa). Próximo item: baixar os pesos no
  `docker build` e carregar do disco.
- **O modo com encoder não foi executado** nesta máquina (o `venv` local não tem `torch`). O sha acima é do
  modo só regex.
- **Docker:** o `ENTRYPOINT` do `Dockerfile` ainda é `python -m verificador`; tem que passar a chamar o
  `run.sh`.
- Testado em Git Bash no Windows; falta rodar em Linux (vai acontecer no teste do Docker).
- Nada foi commitado. Os arquivos novos estão marcados no índice do git (`git add -N`, para registrar o bit
  de execução dos `.sh`).

---

## 2. Pesos do encoder baixados para o cache local (30/09)

**Item da checklist:** pré-requisito de "Encoder sem rede". Esta etapa é só local: **nenhum arquivo do
repositório mudou**. Serve para poder testar o modo com encoder offline nesta máquina e para registrar
o que o `docker build` vai ter de baixar.

### O que foi feito

`snapshot_download` (`huggingface_hub` 2.0.0, já no `venv`) do repositório público
`Roberto2799/jusbrasil-encoder-citacoes` na revisão fixa do `verificador.toml`, **sem token**, para o cache
padrão do Hugging Face (`~/.cache/huggingface/hub/`). É lá que o `transformers` procura quando
`HF_HUB_OFFLINE=1`.

| Arquivo (revisão `d91d09142fdc2601cad04b8df1d509d87c5a1552`) | Bytes |
|---|---|
| `model.safetensors` | 433.368.868 |
| `tokenizer.json` | 677.790 |
| `manifesto_treino.json` | 2.383 |
| `.gitattributes` | 1.519 |
| `config.json` | 1.102 |
| `tokenizer_config.json` | 351 |

Os pesos estão em **safetensors**, não em pickle (`pytorch_model.bin`): o carregamento não executa código.

### Verificação

- `sha256(model.safetensors)` = **`4e52bfb66fe10ba9c1802a7205047d777f0766745a92992b0f8973091971a2bc`**,
  igual ao `sha256` LFS que o Hugging Face publica para essa revisão. É o valor que o `Dockerfile` deve
  conferir depois do download.
- Com `HF_HUB_OFFLINE=1`, `snapshot_download(..., local_files_only=True)` resolve o snapshot do cache sem
  rede.
- Download levou ~1 min; ~414 MB em disco.

### Limitações e pendências

- **O `run.sh` com encoder continua falhando nesta máquina**, agora só porque o `venv` não tem `torch` nem
  `transformers`. Para testar localmente: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
  e `pip install transformers` (fixar as versões do manifesto do Kaggle).
- `encoder.py` ainda chama `from_pretrained` sem `local_files_only=True`. Com `HF_HUB_OFFLINE=1` o
  `transformers` já não vai à rede, mas o carregamento explícito do disco deixa isso claro no código.
- No Docker o download tem que acontecer no `docker build` (opção A); este cache local não vai para a
  imagem.

---

## 3. `torch` e `transformers` no `venv` local; primeiro teste do modo com encoder offline (30/09)

**Item da checklist:** pré-requisito de "Encoder sem rede" e de "Teste de máquina limpa". De novo,
**nenhum arquivo do repositório mudou** — só o `venv` local (que não vai para o git).

### O que foi feito

```bash
venv/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
venv/Scripts/python.exe -m pip install transformers
```

Versões que entraram (Python 3.13.9, Windows):

| Pacote | Versão |
|---|---|
| `torch` | 2.14.1+cpu |
| `transformers` | 5.18.0 |
| `tokenizers` | 0.23.2 |
| `safetensors` | 0.8.0 |
| `huggingface_hub` | 1.33.0 (era 2.0.0; o `transformers` exigiu a troca) |

Não há registro no repositório das versões usadas no Kaggle (`v170`): nem o manifesto de treino do
encoder nem os manifestos em `runs/` as gravaram. Por isso entraram as versões atuais.

### Verificação

`bash run.sh base/outra_base.db docs out/encN.csv`: base renomeada, `.txt` em outra pasta, fora do
repositório, com `HF_HUB_OFFLINE=1` (o próprio `run.sh` define). Rodado duas vezes:

- **Funcionou sem rede**: pesos lidos do cache, código 0, 26 documentos.
- **`sha256` = `4c6e3538…0f9ffb` nas duas execuções**, idêntico ao modo só regex e ao da `sub-005`/`sub-006`.
  Na amostra o encoder não acrescenta nenhuma citação (o que já se sabia desde 25/09), então este teste
  prova que o caminho com encoder roda offline e é determinístico, **não** que as versões novas dão
  as mesmas previsões que as do Kaggle em textos onde o encoder age.
- Primeira execução de verdade do modo com encoder fora do Kaggle.

### Tempo (achado importante)

| Etapa | Tempo nesta máquina |
|---|---|
| `import torch, transformers` | 8,7 s (fixo) |
| Carregar o encoder | 6,3 s (fixo) |
| Inferência | **3,5 s por documento** (média; máx. 4,2 s), ~3.300 caracteres ≈ 930 tokens ≈ 3 janelas |
| `run.sh` completo, 26 documentos | ~2 min (só regex: ~6 s) |

Medido por janela de 512 tokens: **1,6 s com 4 threads** (o `Encoder` fixa `threads=4`), 1,0 s com 10.
`use_deterministic_algorithms(True)` não pesa (1,59 s vs 1,62 s). A lentidão é a CPU deste notebook
(BERT-base em CPU, 4 threads); numa máquina de servidor deve ser bem menor, mas **não foi medido lá**.
Extrapolando o pior caso (esta máquina): 1.000 documentos ≈ 1 hora.

Possíveis ganhos (nenhum aplicado; cada um pode mudar a saída e precisaria provar `sha256` igual):
- mais threads (`threads=os.cpu_count()`): ~1,6× aqui; a ordem das somas muda, o argmax quase nunca;
- usar a GPU que a organização oferece: ordem de grandeza mais rápido, mas sai do "inferência
  determinística em CPU" (R49) testado até aqui.

### Pendências

- Fixar no `requirements.txt` / `Dockerfile` as versões que vão ser entregues e repetir este teste com
  elas (dentro do Docker, em Linux).
- Decidir se o tempo exige alguma das otimizações acima e informar o tempo esperado no README.

---

## 4. Correção: `executar` volta a seguir as specs (R15, R16, "Identidade") (01/10)

**Por quê.** Ao conferir o item 1 contra o `specs/DEFINE.md` e o `specs/DESIGN.md`:

- **R16**: "O sistema DEVE gerar o `submission.csv` executando, **sem modificação**, o
  `json_to_submission.py` distribuído pela organização." O `submissao.py` era uma reimplementação: dava o
  mesmo CSV, mas não é o script deles.
- **R15**: "O sistema DEVE gravar, para cada documento, um arquivo `<documento_id>.json` numa mesma pasta."
  O `executar` gravava numa pasta temporária e apagava.
- **`DESIGN.md`, "Identidade"**: cada execução grava manifesto com commit, hashes (`.db`, tabelas,
  conversor), link + revisão do modelo e ambiente. O `executar` não gravava nenhum.

### O que foi feito

| Arquivo | Mudança |
|---|---|
| `src/verificador/saida/oficial/json_to_submission.py` (novo) | **Cópia byte a byte** do conversor da organização (sha256 `c6ec4963e884c7fc19939816d7398e512cc8f7d60af472fb1a3bd723f1fee05c`). Não é para editar: um teste trava o hash. |
| `src/verificador/saida/submissao.py` | **Removido.** |
| `src/verificador/cli.py` | `cmd_rodar` ganhou `db=` e `script=` opcionais: com os dois, não procura pasta de dados nem exige o nome `desafio1_bracis.db`; sem eles, o comportamento de antes não muda. O manifesto grava também `argumentos.db`. O carregamento do encoder no `rodar` passou a usar `_carregar_encoder` (mesma mensagem que aponta o `run_sem_encoder.sh`). `cmd_executar` virou uma camada fina: valida os argumentos, chama o `cmd_rodar` com o `.db` dado e o `CONVERSOR_OFICIAL`, grava os artefatos em `<arquivo_saida>_artefatos/execucao/` (apaga antes os da execução anterior com o mesmo nome, senão um JSON velho entraria no CSV) e copia o CSV para `<arquivo_saida>` por `.parcial` + `os.replace`. |
| `pyproject.toml` | `saida/oficial/*.py` como package-data (vai junto num `pip install`). |
| `tests/test_executar.py` | 6 testes: hash do conversor = oficial; conversor = o da pasta de dados (quando existe); CSV do `executar` byte a byte igual ao do `rodar` e com um JSON por documento + manifesto (R15); recusa base ausente; recusa pasta sem `.txt`; base inválida não deixa CSV. |
| `specs/DESIGN.md` | Árvore de arquivos e lista de comandos com `run.sh`, `run_sem_encoder.sh`, `executar` e `saida/oficial/`; registra que a execução cega não grava relatório (o R28 fala de amostra e controle, que precisam de gabarito). |

Saída de `bash run.sh base.db txts/ saida/sub.csv`:

```
saida/sub.csv                      ← o CSV de submissão
saida/sub_artefatos/execucao/
    jsons/<documento_id>.json      ← R15
    rastro.jsonl                   ← caminho de decisão por citação
    manifesto.json                 ← commit, hashes, encoder link+revisão, versões, tempos
    submission.csv                 ← o mesmo CSV (saída do conversor oficial)
```

### Verificação

- `pytest`: **285 passaram, 5 pulados**.
- `run_sem_encoder.sh` e `run.sh` (offline, com encoder), base renomeada e `.txt` fora do repositório: os
  dois com `sha256` **`4c6e3538…0f9ffb`**, o mesmo de antes e da `sub-005`/`sub-006`.
- Manifesto do modo com encoder: `usar_encoder: true`, revisão `d91d0914…`, hash do conversor `c6ec4963…`,
  `argumentos.db` com a base renomeada, `dados: null`.

### O que segue valendo do `DEFINE.md` e foi conferido nesta mudança

R2 (offsets: leitura com `newline=""`, inalterada), R15, R16, R17 (uma linha por `.txt`), R22 (`run.sh`
bloqueia rede), R30 (um comando faz indexação, carga do modelo, processamento e CSV), R41 (`documento_id` =
nome do arquivo, só como rótulo), R45 (link + revisão no toml e no manifesto), R49 (duas execuções
idênticas). `contratos.py` não foi tocado.

---

## 5. Encoder só do disco + `Dockerfile` enxuto, testado sem rede (01/10)

**Itens da checklist:** "Encoder sem rede" e "Docker declarado e funcionando". **Decisão do usuário
(01/10):** imagem enxuta (`python:3.13-slim`) em vez da imagem do Kaggle. Registrada como revisão de 01/10
do ADR-014, que em 17/09 tinha rejeitado o "`Dockerfile` enxuto".

### O que foi feito

| Arquivo | Mudança |
|---|---|
| `src/verificador/extracao/encoder.py` | `Encoder(..., local_files_only=False)`: com `True`, tokenizador e modelo só vêm do cache local; peso ausente vira erro, nunca download (R22). |
| `src/verificador/cli.py` | `cmd_rodar(..., offline=False)` repassa o `local_files_only`; o `executar` (avaliação final) chama com `offline=True` **sempre**, mesmo fora do `run.sh`. O `rodar` de desenvolvimento não muda. O manifesto passa a gravar em `imagem_docker` a variável `IMAGEM_DOCKER` (definida no `Dockerfile`); antes era o texto fixo `gcr.io/kaggle-gpu-images/python:v170`, que não correspondia a nada conferido (R31). Fora do container fica `null`. |
| `requirements.txt` | Versões exatas (`==`) do ambiente validado: `torch==2.14.1+cpu` (índice CPU do PyTorch), `transformers==5.18.0`, `tokenizers==0.23.2`, `safetensors==0.8.0`, `huggingface_hub==1.33.0`, `numpy==2.5.3`, `pandas==3.0.6`. Saiu o `pytest` (já está no extra `dev` do `pyproject.toml`). |
| `Dockerfile` | `python:3.13-slim@sha256:7c61056e…` (Python 3.13, o mesmo do `venv` validado) → `pip install -r requirements.txt` → **download dos pesos no build** (`snapshot_download` do link + revisão do `verificador.toml`), com **conferência do sha256** de `model.safetensors` (`4e52bfb6…`; se não bater, o build falha) → código → `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` → `ENTRYPOINT ["bash", "run.sh"]`. Exemplos de `docker build`/`docker run` no cabeçalho. |
| `.dockerignore` | Passa a excluir **`.env`** (tokens), `venv` (o nome real da pasta; antes só `.venv`), `sintetico*`, `lener-br`, `results*`, além do que já excluía. |
| `docs/decisions/ADR-014-…md` | Revisão de 01/10: por que a imagem enxuta, o custo aceito (versões ≠ das do Kaggle `v170`, nunca registradas) e a verificação. |
| `specs/DESIGN.md` | Linha "Ambiente (entrega)" e árvore de arquivos com o `Dockerfile` novo. |

### Verificação (Docker Desktop local: Linux, 2 CPUs, 4 GB de RAM)

- `docker build`: ok em **~6 min** (5 min reconstruindo a partir do cache). Imagem de **3,44 GB**. Conferência
  do sha256 dos pesos passou no build.
- `docker run --rm --network none -v <dados>:/dados:ro -v <saida>:/saida verificador:teste
  /dados/base/outra_base.db /dados/docs /saida/encN.csv` (`.db` renomeado, `.txt` montados de fora):

  | Execução | Tempo | sha256 |
  |---|---|---|
  | com encoder, 1ª | 106 s | `4c6e3538…0f9ffb` |
  | com encoder, 2ª | 103 s | `4c6e3538…0f9ffb` |
  | com encoder, depois do ajuste do manifesto | 105 s | `4c6e3538…0f9ffb` |
  | só regex (`--entrypoint bash … run_sem_encoder.sh`) | — | `4c6e3538…0f9ffb` |

  Igual ao da `sub-005`/`sub-006`: **R22 (sem rede), R30 (um comando), R49 (duas execuções idênticas) e R16
  (conversor oficial) conferidos em Linux, dentro do container.**
- Manifesto de dentro do container: `usar_encoder: true`, Python 3.13.15, as versões do `requirements.txt` e
  `imagem_docker: python:3.13-slim@sha256:7c61056e…`. Tempo quase todo na extração (82 s de encoder para 26
  documentos com 2 CPUs).
- `pytest` local: 285 passaram, 5 pulados.

### Limitações e pendências

- **O teste foi feito a partir desta cópia de trabalho, não de um clone limpo do commit.** Falta o teste de
  máquina limpa de verdade: `git clone` do commit final num diretório novo → `docker build` → `docker run
  --network none`. Depende de commitar estas mudanças.
- Tempo: ~4 s por documento com 2 CPUs. Na máquina da organização (~8 vCPUs pelo R44) o encoder ainda usa 4
  threads (`threads=4` no `Encoder`); não foi mexido para não arriscar a saída.
- README ainda descreve o fluxo antigo (próximo item).

---

## 6. Teste de máquina limpa — passou (01/10)

**Item da checklist:** "Teste de máquina limpa" (o "sem este teste não há entrega"). Nenhum arquivo do
repositório mudou nesta etapa.

### Como foi feito

1. `git clone --branch caio` do repositório local para um diretório novo, fora da pasta de trabalho, com
   `core.autocrlf=false` (arquivos exatamente como estão no git, como num Linux). Commit
   **`c2862f3d287841a93ceba28e2e685fc0f9a745a5`**. O clone não tem `venv`, `.env`, `runs/`, dados da amostra
   nem cache do Hugging Face; `git ls-files` não lista `.db`, gabarito, `.txt` nem `.env`.
2. `docker build --no-cache -t verificador:limpo .` — nada reaproveitado dos builds anteriores.
3. Dados copiados para outra pasta com outros nomes: `entrada/base_final.db` e `entrada/pareceres/*.txt`.
4. `docker run --rm --network none -v entrada:/dados:ro -v saida:/saida verificador:limpo
   /dados/base_final.db /dados/pareceres /saida/submission_N.csv`.

### Resultado

| Etapa | Resultado |
|---|---|
| Build sem cache | ok, **292 s**, imagem de **2,61 GB**; sha256 dos pesos conferido no build |
| Com encoder, 1ª execução | código 0, 114 s, sha256 `4c6e3538…0f9ffb` |
| Com encoder, 2ª execução | código 0, 118 s, sha256 `4c6e3538…0f9ffb` |
| Só regex (`run_sem_encoder.sh`) | código 0, 15 s, sha256 `4c6e3538…0f9ffb` |

O mesmo sha256 da `sub-005`/`sub-006` e de todos os testes anteriores. Manifesto: `usar_encoder: true`,
`imagem_docker: python:3.13-slim@sha256:7c61056e…`.

### Observações

- **`git.commit` sai `null` no manifesto de dentro do container**: a imagem não leva `.git` (está no
  `.dockerignore`) e a `slim` não tem o binário `git`. O commit que vale é o do e-mail de entrega.
  Não foi alterado: o R31 trata das submissões que **nós** geramos (`submeter`, tag `sub-NNN`).
- As dependências transitivas que não estão no `requirements.txt` (p. ex. `networkx`, `sympy`, usadas só
  pelo `torch` internamente) podem vir em versão mais nova num build futuro; neste build, `networkx` veio
  3.7 (no `venv`, 3.6.1) e a saída não mudou.
- Ambiente do teste: Docker Desktop no Windows (motor Linux), 2 CPUs e 4 GB de RAM.

---

## 7. README para o avaliador e literal da amostra fora do código (01/10)

**Itens da checklist:** "README para avaliador" e "Caminhos absolutos e nomes da amostra".

| Arquivo | Mudança |
|---|---|
| `README.md` | Reescrito para quem vai executar: comandos Docker (`build`, `run --network none`, modo só regras), execução sem Docker, o que sai (CSV + `_artefatos/` com JSONs, rastro e manifesto), abordagem em 5 etapas, o índice da base como o "enriquecimento do `.db`" (gerado do zero a partir do `.db` recebido, só leitura), pesos com link + revisão + sha256 e como chegam offline, ambiente/tempo/determinismo com os números medidos nas seções 5 e 6. Saíram "única chamada de rede", "`docker build` não foi testado" e o fluxo de dois comandos como forma de entrega. |
| `src/verificador/extracao/padroes.py` | Comentário citava um `documento_id` e um trecho de citação da amostra; o R43 proíbe os dois como literal no código-fonte. Reescrito de forma genérica, sem mudar código. `grep` por ids da amostra em `src/` agora não acha nada. |

`pytest`: 285 passaram, 5 pulados.
