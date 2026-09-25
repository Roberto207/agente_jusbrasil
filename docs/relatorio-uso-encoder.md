# Relatório — usar ou não o encoder na submissão

**Data:** 25/09/2026 (seções 9 a 11 acrescentadas no mesmo dia, depois do go/no-go formal) · **Para:** decisão em equipe · **Prazo final do desafio:** 30/09, 23h59 (BRT)

Este documento junta o que medimos sobre o encoder para a equipe decidir se ele entra na
submissão. Os detalhes técnicos estão em `tarefas_equipe.md` (Fase 4). Aqui a ideia é explicar
em linguagem simples.

---

## 1. Para que o encoder serviria

O sistema acha as citações com **regex**, regras escritas à mão que reconhecem formatos como
`REsp 1.234.567/SP` ou `Súmula 83 do STJ`. O regex é rápido, preciso e sempre dá a mesma
resposta, mas **só acha o formato que alguém previu**. Se o conjunto final escrever uma citação de
um jeito que nunca vimos, o regex não a acha e perdemos pontos.

O **encoder** é um modelo de linguagem pequeno (BERTimbau, 110 milhões de parâmetros), treinado
por nós para marcar trechos de citação num texto. Ele aprende o "jeito" de uma citação, não um
formato fixo, e por isso pode achar variações que o regex não conhece.

Ele foi desenhado como **rede de segurança**, não como substituto:

- ele só **acrescenta** citações onde o regex não achou nada. O que o regex já acha nunca muda;
- cada trecho que ele marca passa por filtros: precisa ter número, precisa ter cara de citação
  (súmula, classe processual, artigo com a lei nomeada) e as regras precisam conseguir ler os
  campos dele;
- ele só **encontra** a citação. Quem decide se ela é real, inventada ou incompleta continua
  sendo o sistema de regras mais a base do desafio, igual a hoje.

## 2. A nota do sistema hoje, sem o encoder

| Conjunto | O que é | Nota / resultado |
|---|---|---|
| **Amostra oficial** (26 docs, 192 citações) | O que o leaderboard da fase 1 usa | **1,1000** (o teto); 192/192 citações achadas, zero espúrias, zero erro grave |
| Sintético da equipe, versão por código (200 docs, 994 citações) | Documentos que geramos, com ruído de OCR | **1,1000** |
| Sintético reescrito por LLM (200 docs, 994 citações) | Os mesmos, com a frase em volta reescrita pelo Qwen | **1,1000** |
| LeNER-Br `test`, jurisprudência | Texto jurídico **real**, que ninguém do time escreveu | **58 de 74** citações (78%); 51 de 64 sem contar o número do próprio processo |
| LeNER-Br `dev`, jurisprudência | Idem, outra parte | 19 de 35 |
| LeNER-Br `dev`, artigos de lei | Idem | 59 de 127 |

A última nota registrada no leaderboard foi a da `sub-002`: 1,08604, 20º lugar em 21/09. As
correções de depois levaram a nota local a 1,1000. O salto no LeNER-Br (de 38 para 58 no `test`)
veio do **reforço do regex** de 24/09, feito sem o encoder.

## 3. A nota do sistema com o encoder

| Conjunto | Sem encoder | Com encoder |
|---|---|---|
| Amostra oficial | 1,1000 | **1,1000** (saída idêntica, byte a byte) |
| Sintéticos (os dois) | 1,1000 | **1,1000** (idêntica) |
| LeNER-Br `dev`, **jurisprudência** | 19 de 35 | **19 de 35** (nenhuma a mais) |
| LeNER-Br `dev`, **artigos de lei** | 59 de 127 | **99 de 127** (+40; 39 dos 41 extras corretos) |
| LeNER-Br `test`, jurisprudência | 58 de 74 | **64 de 74** (+6; ver seção 9) |
| LeNER-Br `test`, artigos de lei | 115 de 202 | **173 de 202** (+58; ver seção 9) |

Em resumo:

- nos dados da organização e nos nossos sintéticos, **o encoder não ganha nem perde**. Já
  estávamos no teto;
- em **jurisprudência**, que é a maior parte do desafio, ele não acrescentou nada no `dev`: o
  reforço do regex já cobriu o que ele acharia;
- em **artigos de lei**, ele acrescentou bastante no texto real, quase sempre acertando.

## 4. Sobre o ganho em leis

**Lei conta na nota.** O desafio pede "citações de jurisprudência **e de lei**", e na amostra 28
das 192 citações (15%) são de lei. Simulamos com a métrica oficial quanto a nota cai se perdermos
citações de lei:

| Citações de lei perdidas (de 28) | Nota |
|---|---|
| 0 (hoje) | 1,1000 |
| 1 | ~1,098 |
| 3 | ~1,093 |
| 5 | ~1,089 |
| todas as 28 | 1,024 |

A nota não cai "15% de 1,1": cada citação perdida custa entre **0,001 e 0,003**. Mas isso já é
muito. Em 21/09, a distância entre o 20º e o 11º lugar era de 0,014, uns 5 a 10 citações. **Uma
citação a mais ou a menos pode mudar várias posições.**

**Onde o ganho aparece.** Na amostra oficial, o regex já acha as 28 leis (28/28), porque a
organização escreve lei de um jeito simples (`art. 373, I, do CPC`). O ganho do encoder apareceu
no **texto real** do LeNER-Br, em formas como `Lei Federal 9.717/98` (ano com 2 dígitos),
`Lei nº 9.717, de 1998`, `Emenda Constitucional nº 41`, `Carta da República` e `do CP`.

**E na fase 2 (conjunto final)?** A organização diz que o conjunto final terá "o mesmo formato, os
mesmos níveis e distribuição de classes equivalente" à amostra, mas é **cego** e pode variar o
jeito de escrever. Duas leituras:

- **Se variar a escrita das leis**, o encoder tende a salvar citações que o regex perderia, e
  cada uma vale 0,001 a 0,003;
- **se escrever igual à amostra**, o ganho é zero, mas também não há perda.

**Pelo critério proposto pelo Roberto** (melhora em algum ponto, sem perda, e cabe na máquina dos
avaliadores), **o encoder se qualifica**: não perdeu nada em nenhum conjunto medido, ganhou em lei
no texto real e cabe na máquina com folga (seção 5). O que não sabemos é **o tamanho** do ganho no
conjunto final. Pode ser zero.

**Os dois caminhos não se excluem.** Dá para ensinar ao regex parte das formas de lei que o
encoder revelou (ano com 2 dígitos, `, de 1998`). Isso pega parte do ganho sem modelo, e o encoder
continua cobrindo o que ninguém previu.

## 5. Quanto o encoder pesa na máquina dos avaliadores

A máquina da avaliação, pelas regras, tem **1 GPU de 24 GB, ~8 vCPUs e 32 GB de RAM**. Solução
que não cabe nela é desclassificada.

Medido na amostra (26 documentos), nesta máquina de desenvolvimento:

| Configuração | Tempo | RAM de pico | GPU |
|---|---|---|---|
| Só regex (hoje) | ~1 s | ~210 MB | não usa |
| Regex + encoder (em CPU) | ~25 s (~1 s por documento) | ~1 GB | não usa |
| Treino do encoder (feito, no Kaggle) | 3 min por modelo | — | 5 GB |

O encoder roda **em CPU de propósito**. Na CPU a resposta sai sempre igual, e isso é exigido na
reprodução (regra de determinismo). Na GPU seria mais rápido, mas pode variar entre máquinas.

**Estimativa para a fase final** (o tamanho do conjunto final é desconhecido; supondo 10× a
amostra, uns 260 documentos):

| Cenário | Tempo estimado | RAM | GPU |
|---|---|---|---|
| Só regex | segundos | < 1 GB | 0 |
| Regex + encoder | ~5 min | ~1 GB | 0 |
| Regex + encoder + LLM da Fase 5 (Qwen2.5-7B, se entrar) | o LLM domina (dezenas de minutos) | alguns GB | ~15 GB de 24 |
| Regex + LLM, sem encoder | quase o mesmo do anterior | alguns GB | ~15 GB de 24 |

Conclusão: **o encoder cabe com folga**, mesmo com o LLM. Ele usa CPU e RAM, e o LLM usaria a
GPU, então os dois não disputam o mesmo recurso.

## 6. Outros pontos para a decisão

1. **Os pesos precisam ser publicados de qualquer jeito.** Nossa regra R46 diz que todo modelo
   treinado pela equipe tem que estar publicado até 30/09, e o encoder já foi usado em medição.
   *Correção:* na conversa de 25/09 foi dito que, sem o encoder, não seria preciso publicar. Pela
   R46 isso estava errado. Mas o próprio `tarefas_equipe.md` se contradiz: a Fase 4 diz "os pesos
   são publicados mesmo assim se já foram usados em treino/medição", e o item "3. Decisão" diz
   "se não passar, os pesos não são publicados". A regra do **desafio** só exige publicar o que a
   solução usa; a R46 é uma regra **nossa**, mais rígida. **A equipe precisa escolher uma das
   duas** e corrigir o outro trecho.
2. **Licença do LeNER-Br.** O encoder treinou com o LeNER-Br. O repositório dele diz MIT, mas o
   card no Hugging Face diz "unknown". Registramos que mandaríamos um e-mail aos autores antes de
   publicar pesos treinados com ele. Isso vale com ou sem o encoder na submissão, se publicarmos.
3. **Determinismo entre máquinas.** Duas execuções na mesma máquina deram saída idêntica. Entre
   máquinas diferentes (nossa, Kaggle, avaliadores), contas em ponto flutuante podem diferir no
   último dígito e, raramente, mudar uma decisão do modelo. Com só regex, esse risco não existe.
   Precisaria ser conferido no Kaggle antes de submeter.
4. **Mais dependências e mais trabalho até 30/09.** O encoder exige `torch` e `transformers` no
   ambiente, no `requirements.txt` e no `Dockerfile`, além do card do modelo e do README. Não é
   difícil, mas é tempo que sai da Fase 5 ou da Fase 6.
5. **Falso positivo no conjunto final não é mensurável agora.** Nos conjuntos que temos, o encoder
   gerou zero citação falsa, e os filtros existem para isso. Mas o conjunto final é cego.
6. **O encoder viu parte da amostra no treino** (os 14 documentos de "ajuste"). Por isso o número
   honesto dele na amostra é o dos 12 documentos de "controle", que também ficou em 100%.
7. **Um detalhe de reprodutibilidade.** Os pesos-base do BERTimbau vieram de uma revisão de
   conversão do Hugging Face, não da revisão que fixamos. O conteúdo é o mesmo. Isso só precisa
   ir escrito no card do modelo.

## 7. Próximos passos

**Com o encoder:**

1. Rodar o go/no-go formal (seção 8), incluindo a régua de lei.
2. Conferir no Kaggle que a saída com encoder é idêntica à local.
3. Publicar os pesos no Hugging Face com revisão fixa e card: licença MIT do modelo-base, fontes
   de treino e a nota do item 7 da seção 6.
4. Pôr `torch` e `transformers` no `requirements.txt` e no `Dockerfile`; `usar_encoder = true` no
   `verificador.toml`, apontando para o repositório e a revisão publicados.
5. Gerar a `sub-006` com o encoder e comparar com a última só-regex.

**Sem o encoder:**

1. Registrar a decisão (no-go) e manter `usar_encoder = false`.
2. Publicar os pesos mesmo assim (regra R46), ou decidir explicitamente não seguir a R46 neste caso.
3. Opcional: ensinar ao regex as formas de lei que o encoder revelou, com teste para cada uma.
4. Gerar a `sub-006` só-regex e seguir para a Fase 5 (LLM, opcional) e a Fase 6 (congelamento).

**Nos dois casos:** o e-mail aos autores do LeNER-Br, se os pesos forem publicados, e a
publicação até 30/09, 23h59.

## 8. O critério go/no-go formal

É a "prova final" que combinamos em 24/09 para não decidir no achismo. A ideia é que o encoder só
entra se provar ganho num texto que **ninguém usou para ajustar nada**: a parte `test` do
LeNER-Br (74 citações de jurisprudência do escopo). O `test` é aberto **uma única vez**, com todas
as regras congeladas, justamente para ninguém ajustar o sistema para ele.

O encoder entra **se, e só se**, as quatro condições valerem:

1. **Ganho real:** o regex + encoder acha **mais** citações no `test` do que o regex reforçado
   sozinho (hoje, 58 de 74). Como são poucas citações, um ganho de 1 ou 2 é considerado ruído.
2. **Nenhuma perda:** a amostra continua 192/192, e os sintéticos continuam sem perda.
3. **Nenhum falso positivo novo** nos "distratores" da amostra (número de autos no cabeçalho,
   protocolo, OAB, folhas, valor da causa), medido nos 12 documentos de controle.
4. **Nada mais piora:** precisão continua 1,0, erro grave (τ) continua zero e duas execuções dão a
   mesma saída.

**O que o critério não previa:** ele só mede **jurisprudência**, porque em 24/09 pensávamos no
encoder para ela. O ganho apareceu em **lei**. Proposta: acrescentar uma régua de lei no mesmo
formato (o `test` de lei do LeNER-Br, também aberto uma única vez) e decidir com as duas.

Pelo que o `dev` já mostra, a expectativa honesta é: **em jurisprudência, o encoder não deve
passar no critério 1**; **em lei, deve passar**. A decisão fica mais simples se a equipe
concordar, antes de abrir o `test`, com esta regra: *"entra se ganhar em pelo menos uma das duas
réguas e não perder em nada"*.

---

## 9. Resultado do go/no-go formal (25/09)

Regras congeladas no commit `d0e264b` antes de abrir o `test`. A régua de lei foi fixada no commit
`77b0764`, também antes de o `test` de lei ser medido pela primeira vez. Os arquivos brutos estão
em `runs/gonogo/` (fora do git).

| Critério | Resultado | Passa? |
|---|---|---|
| 1. Ganho no `test`, jurisprudência | 58 → **64** de 74 (sem nº próprio: 51 → 57 de 64). +6, acima do ruído de 1–2 | **sim** |
| 1'. Ganho no `test`, lei (régua proposta) | 115 → **173** de 202 (+58) | **sim** |
| 2. Nenhuma perda | Amostra 192/192, nada sumiu nem mudou de classe. Sintéticos: sem perda (ver nota) | **sim** |
| 3. Nenhum falso positivo novo nos distratores | Controle da amostra: 0 espúrios | **sim** |
| 4. Precisão 1,0, τ = 0, mesma saída em duas execuções | Precisão 1,0, τ = 0, saída idêntica (mesma máquina) | **sim** |

**Pela letra do protocolo, o resultado é GO.**

*Nota sobre os sintéticos:* a rodada formal foi interrompida por tempo (a máquina estava lenta, com
swap). Ela é redundante: as portas finais só **descartam** candidatas do encoder, nunca do regex, e
na rodada de 24/09, com portas mais frouxas, o encoder não acrescentou nada aos sintéticos (nada
sumiu, nada apareceu, zero espúrios). Com portas mais restritas, o resultado não pode mudar.

### O que está por trás dos números (a parte que importa)

**Jurisprudência (+6): o ganho é frágil.** Das 6, **5 estão num único documento** e são a mesma
Orientação Jurisprudencial repetida (`OJ Transitória 75 da SBDI-1`, mais uma `OJ SDI-I n° 336`). A
sexta é um número do TST no formato antigo (`TST-AIRR-581/2006-079-03-40.0`). Nenhuma dessas formas
existe no acervo do desafio, e no `dev` o ganho foi zero. Passa no critério, mas **eu não contaria
com esse ganho no conjunto final**.

**Lei (+58): o ganho é sólido e relevante para o desafio.** Classificando cada extra pela lei:

- **30 dos 58 são de leis que estão no acervo** (CLT, CPC, CPP, CF, CC);
- **11 são artigos exatos do acervo** (seriam `real` no desafio), por exemplo
  `art. 896, § 1.º-A, I, da CLT` e `art. 312, p.u do CPP`;
- o regex perde esses casos por **complementos comuns na escrita jurídica** que ele não conhece:
  `caput`, `parágrafo único` / `p.u`, alíneas (`"a" e "c"`), `§ 1.º-A`, `e seguintes`;
- os outros 28 são leis fora do acervo (Lei Orgânica do TCU, decretos, regimentos). No desafio
  valeriam como citação `inventada`, se aparecerem;
- nenhum falso positivo de verdade: os 5 extras sem anotação correspondente são trechos que se
  sobrepõem a uma anotação, só com a borda diferente.

Isso responde à dúvida da seção 4: **o ganho em lei não é só "texto real que o desafio não usa"**.
`art. 37, caput, da Constituição Federal` ou `art. 896, parágrafo 6º, da CLT` são formas
perfeitamente plausíveis no conjunto final, e cada uma vale 0,001 a 0,003.

## 10. Minha opinião

**Eu seguiria com o encoder (GO), com duas condições.**

1. **Ele passa em tudo o que a equipe definiu como prova**, e o critério de Roberto (melhora sem
   perda, cabendo na máquina) também: nenhuma perda em nenhum conjunto, nenhum espúrio, ~1 GB de
   RAM, sem GPU.
2. **O ganho que importa é o de lei, e ele é concreto:** artigos do acervo escritos com `caput`,
   `parágrafo único` ou alíneas. O conjunto final é gerado a partir do acervo, e esses complementos
   são o jeito comum de escrever lei no Brasil.
3. **O ganho em jurisprudência eu não levaria em conta.** É real no LeNER-Br, mas vem de uma forma
   (OJ) que o acervo não tem.

**Condições:**

- **Conferir no Kaggle que a saída com encoder é idêntica à local** (determinismo entre máquinas).
  Se não for, o encoder sai, porque solução não reproduzível é desclassificada.
- **Também ensinar ao regex os complementos de lei** (`caput`, `parágrafo único`, `p.u`, alíneas,
  `§§`, `e seguintes`), com evidência do `train`/`dev` (o `dev` já tem `caput` e `§§`). O regex
  continua sendo a camada principal, e o encoder fica como rede para o que ninguém previu. Atenção:
  essas formas também foram **vistas agora no `test`**. Isso precisa ficar registrado, e o `test`
  deixa de medir essa correção de forma limpa.

**Se a equipe preferir não assumir o risco operacional** (dependência de torch, publicar pesos,
conferência entre máquinas a menos de 5 dias do prazo), o caminho B também é defensável: só o
reforço do regex de lei. Ele captura a maior parte desse ganho de forma determinística. O que se
perde é a rede para formas que ninguém previu.

## 11. Publicar os pesos mesmo no no-go? O que as regras dizem

**O que o desafio exige:**

- "Fine-tuning é permitido, desde que os pesos resultantes sejam **publicados e referenciados**"
  (`specs/scope.md`, regras da aba Rules).
- O pacote reproduzível pede a "referência dos **modelos** (link + revisão)" e o comando que
  reproduz **as saídas submetidas**.
- O FAQ explica o motivo: "a organização precisa conseguir **executar sua solução** de ponta a
  ponta".

Ou seja, a obrigação está amarrada a **reproduzir a solução submetida**. Um modelo que a solução
não carrega não precisa ser publicado pelo desafio.

**O que a nossa regra diz:** a R46 (`specs/DEFINE.md`) é mais rígida, é uma regra **nossa**: "os
pesos de todo modelo treinado ou ajustado pela equipe [...] DEVEM estar publicados". Ela foi
escrita a partir da regra do desafio, mas ampliou o alcance.

**O que pesa contra publicar sem necessidade:**

- **Regras do Kaggle sobre compartilhamento** (Foundational 5d e 6): nada de compartilhar código
  ou dados fora da equipe em privado, e código público só no fórum do Kaggle. Pesos não são código,
  mas o modelo treinou com 14 documentos da amostra (dados da competição). Quando o desafio
  **exige** publicar, isso está coberto. Sem a exigência, é risco sem benefício.
- **Licença do LeNER-Br** ainda não confirmada pelos autores.
- Ajuda outras equipes sem nos dar nada em troca.

**Minha opinião:**

- **Se GO:** publicar é obrigatório. No HF, público, com revisão fixa, antes de 30/09, com card
  (licença MIT do modelo-base, fontes de treino, a nota sobre a revisão dos pesos-base).
- **Se no-go:** **não publicar agora.** Corrigir a R46 para "todo modelo **usado na execução que
  gera as saídas submetidas**", que é o que o desafio pede, e alinhar o `tarefas_equipe.md` (o item
  "3. Decisão" já diz isso). Guardar os pesos em privado (`runs/encoder/`). Depois do encerramento,
  se a equipe quiser (artigo no BRACIS, benchmark), publicar com a licença do LeNER-Br confirmada.
- **Nos dois casos,** o dataset sintético continua publicado: ele é usado na calibração da solução
  só-regex, então a exigência vale para ele.
