# Ação humana pendente

Lista do que só um humano consegue fazer — login em conta de terceiro (GitHub, Kaggle, Hugging
Face), clicar em telas, decidir por gente, ou gastar uma submissão do teto diário. Não é lista de
tarefas de código (essas estão no `BUILD_PROMPT.md` e no `DESIGN.md`, seção "Frentes de trabalho").
Organizado na mesma ordem das etapas do build. Marque o que for concluindo.

---

## Já feito

- [x] Tornar o repositório GitHub privado. (Confirmado: `api.github.com/repos/Roberto207/agente_jusbrasil`
  hoje responde 404 sem login, ou seja, não é mais público.)

## Antes do esqueleto

- [ ] **Revisar e aprovar os documentos ainda não commitados** (`scope.md`, `DEFINE.md`, `DESIGN.md`,
  `docs/`, `sistema_explicado.md`, `BUILD_PROMPT.md`). Hoje só existe um commit no repositório
  ("first commit - define, explicacao e scope") — tudo depois disso está só no disco. *Por que é
  humano: só você decide se o conteúdo está pronto para virar histórico; depois de aprovar, é só
  pedir para eu commitar.*
- [ ] **Confirmar que os convites de colaborador no GitHub foram aceitos** pelos outros 3 integrantes
  (`Settings → Collaborators` do repositório). *Por que é humano: é tela do GitHub, sem API que eu
  tenha acesso aqui.*
- [ ] **Cada integrante entra na competição no Kaggle com a própria conta** (uma conta por pessoa,
  aceitar as regras da competição). *Regra do Kaggle: conta é individual, ninguém pode entrar pela
  conta de outro.*
- [ ] **Cada integrante verifica o telefone na conta Kaggle.** Sem isso, GPU e internet no notebook
  ficam bloqueadas.
- [ ] **Criar o token de acesso do GitHub** (fine-grained, só leitura, só para o repositório
  `agente_jusbrasil`) — cada integrante que for rodar notebook cria o seu. Passo a passo em
  `docs/guia_kaggle.md`.
- [ ] **Guardar esse token no cofre de Secrets do Kaggle** (`Add-ons → Secrets`, nome
  `GITHUB_TOKEN`), e **anexá-lo a cada notebook novo** (não é automático entre notebooks).
- [ ] **Anexar a competição como Input** no(s) notebook(s) (`Add Input → Competitions`), ou, se não
  aparecer, subir os dados como Dataset privado.
- [ ] **Escolher e fixar a tag da imagem `gcr.io/kaggle-gpu-images/python`** que o `Dockerfile` vai
  usar — precisa ser a mesma versão de ambiente fixada no notebook. *Por que é humano: exige abrir o
  notebook, ver qual versão de ambiente está rodando de fato (`Settings → Environment`), e escolher a
  tag correspondente — decisão amarrada ao que está rodando na tela, não só pesquisa.*
- [ ] **Rodar o primeiro notebook (`00_esqueleto.ipynb`) manualmente pela primeira vez**, uma célula
  de cada vez, conferindo que o clone com token funciona e que as saídas aparecem em
  `/kaggle/working/`. *É o próprio teste do mecanismo descrito em `docs/guia_kaggle.md` — precisa de
  alguém olhando a tela do Kaggle.*

## Durante as frentes (A/B/C/D)

- [ ] **Distribuir as 4 frentes entre os integrantes da equipe** (índice/base, texto+extração,
  avaliação+dados sintéticos, decisão+confiança) — ver critérios de pronto de cada uma no `DESIGN.md`.
  *Decisão de gestão do time, não técnica.*
- [ ] **Decidir e enviar o e-mail para `desafio-bracis@jusbrasil.com.br`** perguntando se referências
  vagas ("jurisprudência pacífica do tribunal") contam como `incompleta` no conjunto final — a
  divergência está registrada em `scope.md` e no ADR-005. *Por que é humano: é comunicação oficial
  com a organização, em nome da equipe.*
- [ ] **Acompanhar a resposta e decidir** se liga o detector de referência vaga (hoje desligado por
  padrão, ADR-005).

## Treino e publicação (encoder e LLM)

- [ ] **Criar conta no Hugging Face** (se a equipe ainda não tiver uma para o projeto), para publicar
  os pesos do encoder e o dataset sintético.
- [ ] **Acompanhar a primeira geração sintética e o primeiro treino do encoder no Kaggle** — não é
  para deixar rodando sozinho sem supervisão: são horas de cota de GPU compartilhada entre a equipe
  (~30h/semana por conta), vale ficar de olho em erro de meio de execução.
- [ ] **Publicar os pesos do encoder e o dataset sintético no Hugging Face**, com link e revisão
  fixa, antes do fim do prazo (regra da competição: pesos de fine-tuning e dados usados no treino
  precisam ser públicos).

## Submissão

- [ ] **Baixar o `submission.csv` de cada rodada e enviar na página da competição** (pelo site ou
  pelo CLI do Kaggle com `kaggle.json` configurado localmente). *Por que é humano: gasta uma
  submissão do teto diário da equipe — decisão de quando vale a pena usar uma.*
- [ ] **Escolher a submissão final** antes de 30/09/2026, 23h59 (BRT).

## No fechamento (se a equipe for finalista)

- [ ] **Montar e entregar o pacote reproduzível** (repositório, README, link+revisão dos modelos,
  `Dockerfile`/`requirements`, comando exato) pedido pela organização.
- [ ] **Confirmar a elegibilidade dos integrantes** junto à organização, se solicitado (só estudantes
  do Brasil).
- [ ] **Decidir a divisão do prêmio**, se houver, e comunicar ao Kaggle antes de os prêmios serem
  emitidos (regra padrão: dividido em partes iguais, a menos que o time decida diferente por
  unanimidade).

---

Itens novos de ação humana que surgirem durante o build entram aqui, na seção correspondente à etapa
do `BUILD_PROMPT.md`/`DESIGN.md` em que apareceram.
