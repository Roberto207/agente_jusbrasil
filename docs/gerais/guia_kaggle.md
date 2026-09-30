# Guia — do repositório git ao notebook do Kaggle

**Para quem:** qualquer integrante que precise rodar o projeto com GPU (geração sintética, treino do
encoder, execuções com modelos, submissões).
**Princípio:** o código vive no repositório privado do GitHub; o notebook do Kaggle só busca o código
numa versão fixa e roda os comandos do projeto. Nenhuma lógica fica escrita nas células.

**Imagem (ADR-014):** o `Dockerfile` de entrega parte de `gcr.io/kaggle-gpu-images/python:v170`
(release de 2026-06-29). No notebook, em *Settings → Environment*, fixar a imagem (não usar sempre
a mais recente). A correspondência exata notebook ↔ tag `v170` se confirma na primeira execução
olhando a versão impressa por `python -m verificador ambiente`.

> **Atualização de 25/09.**
> - **Notebooks atuais:** `08_sub-006.ipynb` gera a submissão (regex + encoder) e confere R49 e o hash;
>   `07_treino_encoder_enc-001.ipynb` treina o encoder. Os exemplos abaixo com `sub-001` são do início do
>   projeto: o fluxo é o mesmo, só a tag muda. Os notebooks `00`, `02`–`04` e `06` ficam como **históricos**
>   (situação de cada um em `notebooks/kaggle/README.md`).
> - **Imagem real:** o manifesto não confirma a tag `v170` (o texto é fixo no código). O que o Kaggle
>   expõe é o hash, em `KAGGLE_DOCKER_IMAGE`: na execução da `sub-006`,
>   `gcr.io/kaggle-gpu-images/python@sha256:37c64f7dd9c54116…`. É esse hash que o `Dockerfile` final
>   deve fixar.
> - **GPU:** a submissão **não precisa de GPU** (o encoder roda em CPU). Use **GPU T4 ×1** mesmo assim,
>   para a sessão rodar na imagem de GPU, a mesma do `Dockerfile`. Não use T4 ×2 (ADR-014 pede uma GPU).
> - **Secrets:** só o `GITHUB_TOKEN`. O `HF_TOKEN` não é mais necessário para a submissão: os pesos do
>   encoder são públicos. Ele só serve para **publicar** algo no HF.
> - **Manifesto:** desde 25/09 os tokens de sessão do Kaggle aparecem como `<oculto>`, e as versões de
>   torch/transformers são gravadas.

---

## Configuração única (uma vez por integrante)

### 1. Conta Kaggle pronta para GPU e internet

- Verificar o telefone na conta (sem isso, GPU e internet ficam desativadas nos notebooks).
- Entrar na competição (aceitar as regras) com a sua própria conta — uma conta por pessoa.

### 2. Token do GitHub só de leitura

No GitHub: *Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate
new token*.

- **Repository access:** *Only select repositories* → `Roberto207/agente_jusbrasil`.
- **Permissions → Repository permissions → Contents:** *Read-only*. Nada mais.
- **Expiration:** até depois do fim da competição (ex.: 31/10/2026).

Copie o token (ele só aparece uma vez).

### 3. Guardar o token no Kaggle

Num notebook do Kaggle: *Add-ons → Secrets → Add Secret*.

- **Label:** `GITHUB_TOKEN`
- **Value:** o token do passo 2.

O segredo fica na sua conta; em cada notebook novo é preciso **marcar o segredo como anexado** na
mesma tela.

---

## Configuração do notebook (uma vez por notebook)

Na barra lateral direita do editor (*Settings* / *Input*):

| Opção | Valor |
|---|---|
| Accelerator | **GPU T4 ×1** (a submissão roda em CPU, mas a sessão com GPU usa a imagem do `Dockerfile`); para treino do encoder, T4 |
| Internet | **On** |
| Environment | fixar o ambiente (opção de manter a imagem original em vez de sempre usar a mais recente) |
| Input | *Add Input → Competitions* → a competição do desafio. Os arquivos aparecem em `/kaggle/input/<nome-da-competição>/` |
| Secrets | `GITHUB_TOKEN` anexado |
| Compartilhamento | privado; se precisar, compartilhar só com integrantes da equipe |

Se a competição não aparecer como input, subir os dados oficiais como **Dataset privado** e anexar. Não
tornar público: os dados da competição são privados.

---

## As células do notebook

Os notebooks versionados ficam em `notebooks/kaggle/` no repositório. Todos seguem este esqueleto.

### Célula 1 — Buscar o código numa versão fixa

```python
import subprocess
from kaggle_secrets import UserSecretsClient

REPO = "Roberto207/agente_jusbrasil"
VERSAO = "sub-001"      # tag ou hash de commit; nunca "main" em execução oficial
DESTINO = "/kaggle/temp/agente_jusbrasil"

token = UserSecretsClient().get_secret("GITHUB_TOKEN")
subprocess.run(
    ["git", "clone", "--quiet", f"https://{token}@github.com/{REPO}.git", DESTINO],
    check=True,
)
subprocess.run(["git", "-C", DESTINO, "remote", "set-url", "origin",
                f"https://github.com/{REPO}.git"], check=True)   # tira o token do .git/config
subprocess.run(["git", "-C", DESTINO, "checkout", "--quiet", VERSAO], check=True)
del token
```

Cuidados:
- **Clonar fora de `/kaggle/working/`.** Tudo em `/kaggle/working/` vira saída do notebook; se o clone
  ficasse lá com o token no `.git/config`, o token iria junto com as saídas.
- **Nunca imprimir o token** nem deixá-lo numa variável exibida. Os notebooks de submissão (`06`, `08`)
  capturam a saída do `git` e troca o token por `***` se o comando falhar — senão o traceback do
  Kaggle mostra a URL com o secret. Se a pasta de destino já existir, eles atualizam em vez de clonar
  de novo.
- **Fixar a versão** (tag ou hash). Para testes rápidos dá para usar um branch; para submissões,
  sempre uma tag.

### Célula 2 — Instalar as dependências

```python
%cd /kaggle/temp/agente_jusbrasil
!pip install --quiet -r requirements.txt
!pip install --quiet --no-deps -e .
```

A imagem do Kaggle já traz muitas bibliotecas. O `requirements.txt` fixa as versões que importam para o
resultado (`torch`, `transformers`, `vllm`...). Se o pip avisar que é preciso reiniciar o kernel,
reiniciar e seguir a partir da célula 3.

### Célula 3 — Conferir o ambiente

```python
!python -m verificador ambiente
```

Comando do projeto que imprime e grava: commit, versão da imagem do Kaggle, GPU, driver, versões das
bibliotecas e memória disponível. Serve para o manifesto e para perceber cedo se algo mudou.

### Célula 4 — Rodar

Um dos comandos do projeto, conforme o objetivo do notebook:

```python
DADOS = "/kaggle/input/<nome-da-competição>"
SAIDA = "/kaggle/working/runs"

!python -m verificador indexar  --dados {DADOS}
!python -m verificador rodar    --entrada {DADOS}/txt --run sub-001 --saida {SAIDA}
!python -m verificador avaliar  --run sub-001 --saida {SAIDA}
```

Outros notebooks chamam `python -m sintetico.gerar ...` (geração de dados) ou
`python -m treino.encoder ...` (treino e publicação dos pesos). Pesos de modelos são baixados do
Hugging Face por link + revisão (internet ligada).

### Célula 5 — Saídas

Ficam em `/kaggle/working/runs/<run_id>/`: `submission.csv`, JSONs por documento, `manifesto.json`,
`relatorio.md`, `rastro.jsonl`, `erros.md`.

---

## Rodar sem ficar olhando

*Save Version → Save & Run All (Commit)* executa o notebook inteiro em segundo plano (até 12 h), gasta
cota de GPU só enquanto roda e guarda as saídas na aba *Output* da versão. É o modo recomendado para
treino, geração sintética e submissões — a sessão interativa cai após ~60 min ociosa.

## Submeter

- **Pelo site:** baixar o `submission.csv` da aba *Output* e enviar na página da competição.
- **Pelo CLI do Kaggle** (na máquina local, com `~/.kaggle/kaggle.json` configurado):

```bash
kaggle competitions submit -c <nome-da-competição> \
  -f runs/sub-001/submission.csv \
  -m "sub-001 · commit <hash> · notebook v<versão>"
```

A mensagem liga a submissão à tag e ao commit (R31).

## Alternativa sem internet no notebook

Se a internet do notebook não puder ser usada, publicar o código como **Dataset privado** a partir da
máquina local e anexá-lo como input:

```bash
git archive --format=zip -o /tmp/codigo.zip sub-001
# descompactar numa pasta com dataset-metadata.json e rodar:
kaggle datasets version -p <pasta> -m "sub-001"
```

Custo: um passo manual a cada versão, e os pesos dos modelos também precisam virar Dataset ou Model
anexado.

## Versionar o próprio notebook

Os `.ipynb` ficam em `notebooks/kaggle/` com um `kernel-metadata.json` e podem ser enviados com
`kaggle kernels push -p notebooks/kaggle/<nome>`. Atenção: **segredos anexados pela interface não são
herdados** num notebook criado por push — é preciso anexar o `GITHUB_TOKEN` de novo pela interface na
primeira vez.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| Opções de GPU ou internet cinza | Telefone não verificado |
| `git clone` pede senha ou dá 403/404 | Segredo não anexado ao notebook, token expirado ou sem acesso ao repositório |
| Erro de bfloat16 | T4 não suporta; a configuração do projeto usa float16 |
| vLLM falha ao iniciar | Acelerador é P100; trocar para T4 |
| Resultado diferente entre execuções | Versão diferente (usar tag), ambiente do notebook mudou (fixar), ou dependência sem versão fixa |

## Fontes

- [Kaggle: User Secrets](https://www.kaggle.com/product-feedback/114053) · [Kaggle: acessar repositório privado do GitHub](https://www.kaggle.com/questions-and-answers/537365) · [Kaggle: segredos em notebooks enviados por CLI](https://www.kaggle.com/product-feedback/666571)
- [Kaggle/docker-python — imagens oficiais](https://github.com/Kaggle/docker-python)
