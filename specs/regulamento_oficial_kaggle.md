# Regulamento oficial — Jusbrasil × BRACIS 2026 (Kaggle)

**Origem:** texto colado pelo usuário a partir das abas Overview, Data e Rules da competição no
Kaggle.
**Data de captura:** 2026-09-22
**Natureza:** cópia de referência do texto oficial, para não depender de re-acessar o Kaggle.
`scope.md` e `explicação_jus_brasil.md` são as versões já destiladas/anotadas deste mesmo
material — leia lá primeiro para entender o desafio; este documento é o texto-fonte, útil para
conferir a formulação exata de uma regra específica (ex.: em disputa sobre uma penalidade) ou
para reproduzir trechos legais (Foundational Rules) que não estavam preservados em nenhum outro
lugar do projeto.

## ⚠️ Divergência de números — checada e resolvida (22/09/2026)

O texto oficial abaixo (seção Data → "Os documentos de entrada") traz números diferentes dos que
constam em `scope.md` e nos arquivos de dados já baixados neste projeto:

| Métrica | Texto oficial (esta captura, 22/09) | Dados locais / `scope.md` |
|---|---|---|
| Registros na base canônica | 1.016 | **1.014** (`select count(*) from documentos` no `.db` local) |
| Citações no gabarito (total) | 225 (Nível 1: 116, Nível 2: 109) | **192** (`goldenset_offsets.csv`, 192 linhas de dado) |
| Classes Nível 1 | real 52 · inventada 32 · incompleta 32 (=116) | não conferido linha a linha |
| Classes Nível 2 | real 44 · inventada 32 · incompleta 33 (=109) | não conferido linha a linha |

**Resultado da checagem:** re-baixamos os dados da aba Data no mesmo dia e os arquivos não
mudaram — `desafio1_bracis.db` e `goldenset_offsets.csv` continuam com 1.014 registros e 192
citações. A divergência é só na descrição textual da página do Kaggle (arredondamento ou erro de
digitação da organização), não no dataset em si. **Sem impacto na fase de treino.**

O risco que fica é a **fase de avaliação final**: quando o conjunto cego for ativado, não existe
gabarito local para comparar contagens, então uma divergência real (dataset diferente do
anunciado) passaria despercebida sem checagem manual. Repetir esta mesma verificação
(`SELECT COUNT(*)` / `wc -l` contra o que a página anunciar) assim que os dados da fase final
forem recebidos. Ver também `scope.md` → "Ainda em aberto".

---

## Overview

### Descrição

LLMs generativos já são usados para redigir pareceres, petições e memorandos jurídicos. Um dos
riscos mais documentados desses sistemas é a alucinação de fontes: o modelo cita jurisprudência
ou dispositivos legais que não existem, ou apresenta citações tão vagas que não podem ser
verificadas. Nos últimos anos, tribunais no Brasil e no exterior já sancionaram advogados por
protocolar peças com citações inventadas geradas por IA.

Neste desafio, você assume o papel de quem precisa construir o verificador automático que falta
nesse fluxo de trabalho: um sistema que lê um documento judicial, identifica todas as citações de
jurisprudência e de lei, e decide — para cada uma — se ela é real, inventada ou incompleta.

### A tarefa

Seu sistema recebe documentos judiciais em texto (`.txt`) e deve, para cada documento, identificar
todas as citações e classificar cada uma em três classes:

- **real** — a citação resolve a um único registro da base canônica do desafio: tem
  identificadores suficientes e a busca confirma sua existência. Exige entregar o `id_canonico`
  correto — acertar o rótulo sem o link não conta.
- **inventada** — identificadores suficientes para buscar, mas nenhum registro correspondente
  existe na cobertura congelada.
- **incompleta** — informação insuficiente para formular a consulta ("conforme jurisprudência
  pacífica do tribunal"), ou suficiente para buscar mas insuficiente para identificar um único
  registro.

A distinção entre `inventada` e `incompleta` importa em produção: a primeira é alucinação ativa (o
LLM inventou um número de acórdão); a segunda é evasiva. Sistemas reais tratam cada caso de forma
diferente — incompletas vão para revisão humana; inventadas devem ser bloqueadas.

O conjunto tem dois níveis de dificuldade: Nível 1 (formato padrão, peso 1×) e Nível 2 (ruído de
OCR e variação de superfície, peso 2×). Os detalhes de dados, base canônica e gabarito estão na
aba Data.

### Como participar

1. Monte sua equipe: participação individual ou em equipes de até 4 pessoas (mesclagem de equipes
   pelo próprio Kaggle), apenas estudantes, do Brasil — a elegibilidade é verificada pela
   organização (ver Rules).
2. Receba os dados: documentos de entrada (`txt/`), base canônica SQLite e gabarito da amostra de
   desenvolvimento estão na aba Data, junto com o conversor de submissão e o script da métrica.
3. Desenvolva sua solução — apenas modelos e ferramentas de pesos e código abertos (veja Rules).
   Qualquer dataset público pode ser usado no treino.
4. Submeta: sua solução produz um JSON por documento (contrato na aba Data); o conversor
   `json_to_submission.py` gera o `submission.csv` que você envia aqui. A métrica oficial roda no
   servidor e o leaderboard atualiza na hora.
5. Publique seu código: as soluções do topo do ranking passam por verificação de reprodutibilidade
   ao final — o repositório e o commit que produziram as saídas serão coletados junto aos
   finalistas.

### Organização

O desafio é uma realização do Jusbrasil — empresa de tecnologia que conecta milhões de
brasileiros à informação jurídica — em parceria com o BRACIS 2026 — 36ª Brazilian Conference on
Intelligent Systems, promovida pela Sociedade Brasileira de Computação.

Dúvidas sobre o desafio, a especificação técnica ou a logística: desafio-bracis@jusbrasil.com.br.

**Start:** 22 dias atrás (a partir da captura) · **Close:** 8 dias restantes (a partir da captura)

### Avaliação

A avaliação tem duas fases:

- **Fase de treino (agora)** — o material distribuído é a amostra de desenvolvimento, com
  gabarito aberto. O leaderboard roda sobre ela e é referencial: serve para validar seu pipeline
  de ponta a ponta, não define o resultado.
- **Fase de avaliação final** — o conjunto final, cego, está em construção pela organização.
  Quando for ativado, o leaderboard reinicia: passa a usar 40% dele (parte pública do
  leaderboard), e o ranking final é calculado sobre os 60% restantes, mantidos em sigilo até o
  encerramento — otimizar demais para o leaderboard não garante nada no resultado final.
  Submissões da fase de treino não contam para o ranking final.

O alinhamento entre suas citações e o gabarito é por sobreposição de spans com IoU ≥ 0,5
(matching 1-para-1 pelo maior IoU). Citação do gabarito sem par vira erro de recall; predição sem
par vira falso positivo. Sobre os pares casados, a nota de cada nível é montada em três passos:

**Passo 1 — macro-F1 das 3 classes.** F1 por classe (real, inventada, incompleta), com média
simples entre elas — assim a classe `inventada`, rara mas central ao desafio, pesa tanto quanto a
`real`. Para a classe `real`, só conta acerto se o `id_canonico` entregue for o `doc_id` esperado
no gabarito.

**Passo 2 — penalidade do erro grave.** O pior erro é carimbar uma alucinação como verificada:

```
τ = fração das citações `inventada` do gabarito preditas como `real`
s = macroF1 · (1 − 0,5 · τ)
```

Se todas as alucinações "vazarem" como real, a nota cai pela metade.

**Passo 3 — bônus de calibração (até 10%).** O campo `confianca` é opcional; se enviado,
medimos o Brier score sobre os pares casados e aplicamos `score = s · (1 + 0,10 · (1 − brier))`.
Confiança alta quando acerta e baixa quando erra aproxima o bônus de +10%. Quem não envia
confiança não ganha nem perde.

**Combinação dos níveis:**

```
score_final = (1 · score_Nível1 + 2 · score_Nível2) / 3
```

Uma submissão perfeita com `confianca = 1.0` pontua **1,1000**.

### Formato de submissão

Sua solução produz um JSON por documento (contrato schema 1.2, na aba Data); o conversor
`json_to_submission.py` (incluído no material) gera o `submission.csv` — uma linha por documento:

```
documento_id,citacoes
gen_n1_001,"469,498,incompleta,-,0.9|589,652,incompleta,-,0.8"
gen_n1_002,-
```

Cada citação é `inicio,fim,classe,id_canonico,confianca` (campos ausentes viram `-`), com
citações separadas por `|`. Documento sem citações leva `-` na célula — nunca deixe a célula
vazia, e todo `documento_id` do conjunto precisa estar presente.

Reproduza localmente: o script de avaliação (`kaggle_metric.py`, na aba Data) é o mesmo que roda
aqui — você reproduz na sua máquina exatamente o score do leaderboard, nível a nível, incluindo o
matching.

### Cronograma e Premiação

| Marco | Data |
|---|---|
| Abertura das inscrições | 18/08/2026 |
| Envio dos dados por e-mail aos inscritos | 25/08/2026 |
| Webinar de tira-dúvidas com a organização | 28/08/2026 |
| Período de submissões com leaderboard ao vivo | 01/09 a 30/09/2026 |
| Fechamento das submissões | 30/09/2026, 23h59 (BRT) |
| Apresentação das melhores soluções no BRACIS 2026 (Cuiabá-MT) | 19 a 22/10/2026 |

Todas as datas em horário de Brasília (BRT).

**Premiação e reconhecimento:**

- Apresentação técnica no BRACIS 2026: as 5 melhores soluções apresentam na sessão de
  encerramento da conferência, em Cuiabá-MT.
- Contribuição à comunidade: o desafio libera um benchmark público de NLP jurídico em português
  após a conferência; as soluções vencedoras entram como referência.

### FAQ

**Preciso estar inscrito no BRACIS para participar?** Não. Apenas as equipes vencedoras precisam
comparecer (ou enviar um representante) à sessão de encerramento da conferência.

**Posso usar APIs comerciais, como modelos de linguagem pagos?** Não. Este desafio aceita apenas
modelos e ferramentas de pesos e código abertos — a organização precisa conseguir executar sua
solução de ponta a ponta, sem chaves de API nem serviços pagos. Servir um modelo de pesos abertos
via API paga durante o desenvolvimento é permitido, desde que o mesmo modelo e revisão sejam
executáveis offline pela organização. Qualquer dataset público pode ser usado no treino.

**Como funciona o leaderboard? Meu score final pode mudar?** Em duas fases. Agora, na fase de
treino, o leaderboard pontua contra a amostra de desenvolvimento (gabarito aberto) e é
referencial — use-o para validar seu pipeline. Quando o conjunto de avaliação final for ativado,
o leaderboard reinicia e passa a usar a parte pública (40%) dele; o ranking final vem dos 60%
privados, mantidos em sigilo até o encerramento — a posição pública é um bom sinal, mas o
resultado final pode mudar.

**Quantas submissões posso fazer?** Múltiplas, com teto diário por equipe (configurado nesta
competição).

**O offset (inicio/fim) pontua?** Não por si só — ele é a chave de junção com o gabarito
(IoU ≥ 0,5). Acima do limiar, a borda exata é irrelevante; abaixo, a citação esperada fica sem
par (erro de recall) e a predição órfã vira falso positivo. Cuidado com a contagem: codepoints
Unicode sobre o texto exatamente como distribuído.

**O campo confianca é obrigatório?** Não, mas é recomendado: confiança bem calibrada (Brier
baixo) rende bônus de até 10% no score.

**Em que língua são os documentos?** Português brasileiro, com citações de jurisprudência e
legislação brasileiras.

---

## Data

### Dataset Description

**Arquivos:**

| Arquivo | O que é |
|---|---|
| `txt/` | Os 26 documentos de entrada (`.txt`, UTF-8) |
| `desafio1_bracis.db` | A base canônica SQLite (93 MB, 1.016 registros — *ver divergência no topo*) |
| `goldenset.csv` | O gabarito da amostra de desenvolvimento (225 citações — *ver divergência no topo*) |
| `json_to_submission.py` | Conversor: JSONs do contrato → `submission.csv` |
| `kaggle_metric.py` | O script de avaliação — o mesmo que roda neste leaderboard |

### A tarefa

Encontrar as citações num documento judicial e classificar cada uma em três classes.

A entrada é um `.txt` por documento. A saída é um JSON por documento, com uma entrada por
citação: o span em codepoints Unicode (`inicio`, `fim` exclusivo), o trecho literal, o tipo
(`lei` ou `jurisprudencia`) e a classe. Opcionalmente, a `confianca` (0–1) de que a classe — e o
link, se `real` — está correta: ela alimenta o bônus de calibração de até 10%, e quem não a envia
não ganha nem perde por isso.

Submissão no Kaggle: sua solução produz os JSONs e o conversor `json_to_submission.py` (incluído
aqui na aba Data) gera o `submission.csv` que você envia — uma linha por documento; documento sem
citações leva `-` na célula, nunca vazia. A métrica que roda no servidor é a cópia exata de
`kaggle_metric.py`, também nesta aba.

O alinhamento entre a predição e o gabarito é por sobreposição de spans com IoU ≥ 0,5 — não é
preciso acertar a borda exata, mas quem não entrega o span de uma citação não consegue
classificá-la, e isso conta como erro de recall.

| | real | inventada | incompleta |
|---|---|---|---|
| **Definição** | A citação resolve a um único registro da base canônica. Exige `id_canonico`: acertar o rótulo sem o `doc_id` correto não conta. | Identificadores suficientes para buscar, mas nenhum registro correspondente existe na cobertura congelada. | Informação insuficiente para formular a consulta, ou suficiente para buscar mas insuficiente para identificar um único registro. |

### Os documentos de entrada

Vinte e seis peças jurídicas sintéticas, divididas em dois níveis de dificuldade — pesos 1× e 2×
na nota.

Esta é a amostra de treino/desenvolvimento, distribuída com gabarito para as equipes construírem
e depurarem suas soluções — é sobre ela que o leaderboard roda na fase atual (referencial). O
conjunto de avaliação final — cego — está em construção pela organização: terá o mesmo formato,
os mesmos níveis e distribuição de classes equivalente, sem gabarito distribuído. Quando for
ativado, os `.txt` dele serão publicados nesta aba, as saídas do seu sistema sobre eles passam a
ser o que você submete, e é dele que saem o leaderboard (40% público) e o ranking final (60%
privado).

São petições, pareceres, decisões monocráticas e memoriais fictícios que citam acórdãos reais do
acervo. Cada documento tem uma matéria coerente — cível, penal, trabalhista, eleitoral ou militar
— que amarra o cabeçalho, os tribunais citados e as normas invocadas: um agravo cível não cita
apelação da Justiça Militar.

A nomenclatura dos arquivos já entrega o nível: `gen_n1_001 … gen_n1_013` são os documentos do
nível 1 e `gen_n2_001 … gen_n2_013`, os do nível 2. O nome do arquivo em `txt/` (sem a extensão) é
o `documento_id` usado no gabarito e na submissão.

| | Nível 1 — Formato padrão | Nível 2 — Ruído e variação |
|---|---|---|
| Peso na nota | 1× | 2× |
| Documentos | 13 | 13 |
| Citações | 116 *(ver divergência)* | 109 *(ver divergência)* |
| Tamanho médio | 3.372 chars | 3.276 chars |
| Classes | real 52 · inventada 32 · incompleta 32 | real 44 · inventada 32 · incompleta 33 |
| O que testa | Reconhecer a citação e resolver o `doc_id` na base canônica. | Normalização robusta antes de verificar: casar variantes de superfície ao mesmo identificador. |

**A mesma classe, escrita de dois jeitos.** As citações do nível 2 apontam para registros
igualmente válidos — o que muda é a superfície. Todas as amostras abaixo são `real`:

| Nível 1 | Nível 2 |
|---|---|
| AREsp nº 1.996.496/RJ | AgRg no Rec. Esp. n. 1.522.200 (SC) |
| Recurso em Habeas Corpus nº 57.763/PR | Recurso em Habeas Corpus nº 93967 - SC |
| RSE nº 7000592-58.2025.7.00.0000/DF | Rec. Esp. No 1.880.529 ⏎ - SP |
| Súmula Vinculante 10 | 5úmula 211 do STJ |

O ruído do nível 2 combina variantes de abreviação (REsp / R.Esp. / Recurso Especial),
formatação do número (1.741.784 / 1741784 / 1.741. 784), separador de UF (/PR, - PR, (PR)),
confusões de OCR (0↔O, 1↔l, 5↔S, m↔rn) e quebras de linha no meio do identificador.

> **Garantia do ruído:** um dígito nunca é trocado por outro dígito. Isso mudaria a identidade da
> citação e transformaria uma `real` ruidosa numa `inventada` de fato. Todo ruído aplicado a uma
> citação real é recuperável por normalização — que é exatamente o que o nível 2 mede.

**Distratores.** Os cabeçalhos trazem números que parecem citação e não são: número dos autos em
formato CNJ, protocolo, inscrição na OAB, fls. 234/567, valor da causa. Nenhum está no gabarito —
extraí-los conta como falso positivo.

Atenção à distinção no formato CNJ: o número dos autos do próprio documento, no cabeçalho, é
distrator; a referência a outro processo em formato CNJ, no corpo do texto, é citação (como o RSE
nº 7000592-58.2025.7.00.0000/DF do quadro acima).

### A base canônica

Um SQLite de 93 MB com os 1.016 registros que definem o universo do desafio *(dados locais:
1.014 — ver divergência no topo)*. É contra ele que uma citação é `real` ou `inventada`.

O banco é a cobertura congelada: um snapshot. Não se consulta base viva, e é isso que torna a
avaliação reproduzível. Se um acórdão existe no mundo mas não está aqui, para efeito do desafio
ele não existe — e, por construção, isso nunca prejudica ninguém: toda citação real dos
documentos resolve dentro da cobertura. O caso-limite "registro real fora da cobertura" não
ocorre neste dataset; se ocorresse, a citação seria excluída do scoring, não anotada como
inventada.

| Coluna | Tipo | Descrição |
|---|---|---|
| `documento_id` | TEXT | Chave primária e nome do `.txt`. `doc_0201` para acórdãos; o próprio `doc_id` para súmulas e leis. |
| `id` | INTEGER | O `doc_id` canônico do Jusbrasil. É este número que vai em `resolucao.id_canonico`. |
| `tribunal` | TEXT | STF, STJ, TSE, TST, STM. Nulo para dispositivos de lei. |
| `ano`, `relator` | INT, TEXT | Só os acórdãos têm. |
| `natureza` | TEXT | `acordao` · `sumula` · `dispositivo` |
| `tipo` | TEXT | `jurisprudencia` · `lei` — o enum do contrato. |
| `texto` | TEXT | Inteiro teor. Idêntico a `txt/<documento_id>.txt`. |
| `texto_len` | INTEGER | Comprimento em caracteres. |

`natureza` existe porque `tipo` sozinho não separa acórdão de súmula — os dois são
`jurisprudencia`.

| Natureza | Registros | O que são |
|---|---|---|
| `acordao` | 998 *(dados locais: 996)* | Acórdãos de STF, STJ, TSE, TST e STM. |
| `sumula` | 5 | Súmulas do STJ, STF e TST, incluindo vinculante. |
| `dispositivo` | 13 | Artigos de CPC, CC, CLT, CF/88, CPP, CPM, CDC, Código Eleitoral e LC 64/1990. |

Há ainda uma tabela virtual `documentos_fts` (FTS5, external content) indexando o texto integral
dos 1.016 registros. Ela não duplica o conteúdo — aponta para `documentos` pelo `rowid`.

### O gabarito

O `goldenset.csv` tem uma linha por citação esperada — 225 no total *(dados locais: 192 — ver
divergência no topo)*, nos 26 documentos.

É o gabarito da amostra de desenvolvimento. O gabarito do conjunto final tem o mesmo formato,
permanece com a organização e é usado exclusivamente na avaliação oficial.

| Coluna | Descrição |
|---|---|
| `nivel` | 1 ou 2 — define o peso na nota final. |
| `documento_id`, `citacao_id` | Identificam a citação. `gen_n1_004` + `g3` — o `n1`/`n2` no nome indica o nível do documento. |
| `inicio`, `fim` | Span em codepoints Unicode, fim exclusivo. Chave de junção com a predição. |
| `trecho` | Cópia literal de `texto[inicio:fim]`. Quebras de linha aparecem escapadas como `\n`. |
| `tipo` | `lei` ou `jurisprudencia`. |
| `classificacao` | A classe esperada. É o que se pontua. |
| `id_canonico` | O `doc_id` do registro que resolve a citação. Só nas `real`. |

### Como usar a base

O fluxo tem três passos, e a maior parte da dificuldade está no primeiro.

**1 · Normalizar o identificador antes de consultar.** O índice FTS usa o tokenizador
`unicode61`, que quebra em qualquer caractere não alfanumérico. `1.741.784` vira três tokens —
`1`, `741`, `784`. A consequência prática:

```sql
-- funciona: a busca por frase reproduz a sequência de tokens
SELECT d.documento_id, d.id, d.tribunal
  FROM documentos_fts JOIN documentos d ON d.rowid = documentos_fts.rowid
 WHERE documentos_fts MATCH '"1.741.784"';   -- 1 resultado

-- não funciona: sem os separadores, é um token só, que não existe no índice
 WHERE documentos_fts MATCH '1741784';        -- 0 resultados
```

Como o nível 2 entrega números sem pontuação com frequência, o pipeline precisa reconstruir a
forma canônica: extrair só os dígitos e reagrupá-los de três em três a partir da direita.
"1 741 784" como frase também casa, porque produz a mesma sequência de tokens.

Números no padrão CNJ — `0600216-46.2020.6.14.0022` — funcionam do mesmo jeito, com busca por
frase.

**2 · Separar o registro de quem apenas o cita.** Esta é a armadilha que mais custa precisão. O
FTS devolve qualquer documento que mencione o número, e acórdãos citam uns aos outros o tempo
todo. Uma busca por `"1.276.977"` devolve seis documentos do STF — e nenhum deles é o RE
1.276.977. Todos apenas o citam.

O sinal que separa os dois casos é a posição. No documento que é o processo, o número está no
cabeçalho, nas primeiras dezenas de caracteres. Nos que apenas citam, ele aparece no corpo:

| Documento | Posição | Contexto |
|---|---|---|
| `doc_0201` | 20 | RECURSO ESPECIAL Nº 1.741.784 - PR … — é o processo |
| `doc_0001` | 48 | AG.REG. NA RECLAMAÇÃO 76.532 RIO DE JANEIRO … — é o processo |
| `doc_0149` | 490 | menciona o RE 1.276.977 na ementa — apenas cita |
| `doc_0001` | 957 | também cita o RE 1.276.977, mais adiante |

Uma abordagem mais robusta que o limiar de posição é fazer o parsing do cabeçalho: classe
processual, número e UF vêm sempre nas primeiras linhas, num formato estável por tribunal. Vale
construir esse índice uma vez, offline, e consultar por chave em vez de varrer o FTS a cada
citação.

**3 · Contar os candidatos e decidir a classe.** Resolvida a consulta, a cardinalidade do
resultado dá a classe quase diretamente. Cada citação real do desafio resolve para exatamente um
registro da base — as duplicatas remanescentes do acervo não têm nenhuma citação apontando para
elas.

| Candidatos encontrados | Classe | Saída |
|---|---|---|
| exatamente 1 | real | `resolucao.id_canonico` = a coluna `id` do registro |
| 0 | inventada | `resolucao: null` |
| 2 ou mais candidatos distintos, sem critério de desempate | incompleta | `resolucao: null` |

Uma citação sem identificadores suficientes para sequer formular a consulta — "jurisprudência
pacífica desta Corte", "o dispositivo legal de regência" — é `incompleta` sem passar pelo banco.
E uma referência do tipo "acórdão do STF de 2024, relatado pelo Ministro Fulano" é buscável, mas
casa com dezenas de candidatos distintos: também `incompleta`, por falta de critério de
desempate.

```sql
-- a consulta por relator+ano que caracteriza a incompleta "buscável"
SELECT COUNT(*) FROM documentos
 WHERE natureza = 'acordao'
   AND tribunal = 'STF' AND ano = 2024
   AND relator LIKE '%Dino%';   -- dezenas de candidatos
```

**Leis e súmulas resolvem por registro próprio.** Buscar "Súmula 83 do STJ" no texto dos acórdãos
devolve dezenas de documentos que a mencionam — nenhum deles é a súmula. Os 18 registros de
natureza `sumula` e `dispositivo` existem para isso: são o alvo da resolução, não o texto que
cita.

```sql
-- todos os registros que não são acórdão, com o texto normativo
SELECT documento_id, id, natureza, tipo, substr(texto, 1, 80)
  FROM documentos
 WHERE natureza IN ('sumula', 'dispositivo')
 ORDER BY natureza, id;
```

Como são poucos, o caminho prático é carregá-los em memória e casar por texto normalizado do
dispositivo — `art. 373, I, do CPC` e `artigo 373, inciso I, do Código de Processo Civil` apontam
para o mesmo `id`.

> **Não confunda as duas colunas de ID:** `documento_id` é a chave interna do acervo e o nome do
> arquivo. `id` é o `doc_id` do Jusbrasil, e é ele que vai em `resolucao.id_canonico`. Entregar
> `doc_0201` onde se espera `2566535283` derruba a citação para erro, mesmo com a classe certa.

Cobertura congelada em 1.016 registros *(dados locais: 1.014)*. A métrica completa e o alinhamento
por IoU estão implementados no `kaggle_metric.py`, incluído nesta aba (ver Overview → Evaluation).

**Files:** 31 files · **Size:** 94.17 MB · **Type:** txt, py, csv + 1 other · **License:**
Subject to Competition Rules · Nome do dataset no Kaggle: `desafio1_bracis`

---

## Rules

### Competition Rules

**Kaggle Competition Foundational Rules (Non-editable)**

Competition participants must also agree to Kaggle's Foundational Competition Rules. These rules
will supersede the competition-specific rules in the event of any conflict.

The following Kaggle Competition Foundational Rules ("**Foundational Rules**") apply to every
competition regardless of whether the Sponsor creates competition-specific rules. Any
competition-specific rules provided by the Sponsor are in addition to these rules, and in the
case of any conflict or inconsistency, these Foundational Rules control and nullify contrary
competition-specific rules.

#### GENERAL COMPETITION RULES - BINDING AGREEMENT

**1. ELIGIBILITY**

a. To be eligible to enter the Competition, you must be:
- a registered account holder at Kaggle.com;
- the older of 18 years old or the age of majority in your jurisdiction of residence (unless
  otherwise agreed to by Competition Sponsor and appropriate parental/guardian consents have
  been obtained by Competition Sponsor);
- not a resident of Crimea, so-called Donetsk People's Republic (DNR) or Luhansk People's
  Republic (LNR), Cuba, Iran, or North Korea; and
- not a person or representative of an entity under U.S. export controls or sanctions (see:
  https://www.treasury.gov/resourcecenter/sanctions/Programs/Pages/Programs.aspx).

b. Competitions are open to residents of the United States and worldwide, except that if you are
a resident of Crimea, so-called Donetsk People's Republic (DNR) or Luhansk People's Republic
(LNR), Cuba, Iran, North Korea, or are subject to U.S. export controls or sanctions, you may not
enter the Competition. Other local rules and regulations may apply to you, so please check your
local laws to ensure that you are eligible to participate in skills-based competitions. The
Competition Host reserves the right to forego or award alternative Prizes where needed to comply
with local laws. If a winner is located in a country where prizes cannot be awarded, then they
are not eligible to receive a prize.

c. If you are entering as a representative of a company, educational institution or other legal
entity, or on behalf of your employer, these rules are binding on you, individually, and the
entity you represent or where you are an employee. If you are acting within the scope of your
employment, or as an agent of another party, you warrant that such party or your employer has
full knowledge of your actions and has consented thereto, including your potential receipt of a
Prize. You further warrant that your actions do not violate your employer's or entity's policies
and procedures.

d. The Competition Sponsor reserves the right to verify eligibility and to adjudicate on any
dispute at any time. If you provide any false information relating to the Competition concerning
your identity, residency, mailing address, telephone number, email address, ownership of right,
or information required for entering the Competition, you may be immediately disqualified from
the Competition.

**2. SPONSOR AND HOSTING PLATFORM**

a. The Competition is sponsored by Competition Sponsor named above. The Competition is hosted on
behalf of Competition Sponsor by Kaggle Inc. ("Kaggle"). Kaggle is an independent contractor of
Competition Sponsor, and is not a party to this or any agreement between you and Competition
Sponsor. You understand that Kaggle has no responsibility with respect to selecting the potential
Competition winner(s) or awarding any Prizes. Kaggle will perform certain administrative
functions relating to hosting the Competition, and you agree to abide by the provisions relating
to Kaggle under these Rules. As a Kaggle.com account holder and user of the Kaggle competition
platform, remember you have accepted and are subject to the Kaggle Terms of Service at
www.kaggle.com/terms in addition to these Rules.

**3. COMPETITION PERIOD**

a. For the purposes of Prizes, the Competition will run from the Start Date and time to the
Final Submission Deadline (such duration the "Competition Period"). The Competition Timeline is
subject to change, and Competition Sponsor may introduce additional hurdle deadlines during the
Competition Period. Any updated or additional deadlines will be publicized on the Competition
Website. It is your responsibility to check the Competition Website regularly to stay informed of
any deadline changes. YOU ARE RESPONSIBLE FOR DETERMINING THE CORRESPONDING TIME ZONE IN YOUR
LOCATION.

**4. COMPETITION ENTRY**

a. NO PURCHASE NECESSARY TO ENTER OR WIN. To enter the Competition, you must register on the
Competition Website prior to the Entry Deadline, and follow the instructions for developing and
entering your Submission through the Competition Website. Your Submissions must be made in the
manner and format, and in compliance with all other requirements, stated on the Competition
Website (the "Requirements"). Submissions must be received before any Submission deadlines stated
on the Competition Website. Submissions not received by the stated deadlines will not be
eligible to receive a Prize.
b. Submissions may not use or incorporate information from hand labeling or human prediction of
the validation dataset or test data records.
c. If the Competition is a multi-stage competition with temporally separate training and/or test
data, one or more valid Submissions may be required during each Competition stage in the manner
described on the Competition Website in order for the Submissions to be Prize eligible.
d. Submissions are void if they are in whole or part illegible, incomplete, damaged, altered,
counterfeit, obtained through fraud, or late. Competition Sponsor reserves the right to
disqualify any entrant who does not follow these Rules, including making a Submission that does
not meet the Requirements.

**5. INDIVIDUALS AND TEAMS**

a. **Individual Account.** You may make Submissions only under one, unique Kaggle.com account.
You will be disqualified if you make Submissions through more than one Kaggle account, or
attempt to falsify an account to act as your proxy. You may submit up to the maximum number of
Submissions per day as specified on the Competition Website.
b. **Teams.** If permitted under the Competition Website guidelines, multiple individuals may
collaborate as a Team; however, you may join or form only one Team. Each Team member must be a
single individual with a separate Kaggle account. You must register individually for the
Competition before joining a Team. You must confirm your Team membership to make it official by
responding to the Team notification message sent to your Kaggle account. Team membership may not
exceed the Maximum Team Size stated on the Competition Website.
c. **Team Merger.** Teams may request to merge via the Competition Website. Team mergers may be
allowed provided that: (i) the combined Team does not exceed the Maximum Team Size; (ii) the
number of Submissions made by the merging Teams does not exceed the number of Submissions
permissible for one Team at the date of the merger request; (iii) the merger is completed before
the earlier of: any merger deadline or the Competition deadline; and (iv) the proposed combined
Team otherwise meets all the requirements of these Rules.
d. **Private Sharing.** No private sharing outside of Teams. Privately sharing code or data
outside of Teams is not permitted. It's okay to share code if made available to all Participants
on the forums.

**6. SUBMISSION CODE REQUIREMENTS**

a. **Private Code Sharing.** Unless otherwise specifically permitted under the Competition
Website or Competition Specific Rules above, during the Competition Period, you are not allowed
to privately share source or executable code developed in connection with or based upon the
Competition Data or other source or executable code relevant to the Competition ("Competition
Code"). This prohibition includes sharing Competition Code between separate Teams, unless a Team
merger occurs. Any such sharing of Competition Code is a breach of these Competition Rules and
may result in disqualification.
b. **Public Code Sharing.** You are permitted to publicly share Competition Code, provided that
such public sharing does not violate the intellectual property rights of any third party. If you
do choose to share Competition Code or other such code, you are required to share it on
Kaggle.com on the discussion forum or notebooks associated specifically with the Competition for
the benefit of all competitors. By so sharing, you are deemed to have licensed the shared code
under an Open Source Initiative-approved license (see www.opensource.org) that in no event limits
commercial use of such Competition Code or model containing or depending on such Competition
Code.
c. **Use of Open Source.** Unless otherwise stated in the Specific Competition Rules above, if
open source code is used in the model to generate the Submission, then you must only use open
source code licensed under an Open Source Initiative-approved license (see www.opensource.org)
that in no event limits commercial use of such code or model containing or depending on such
code.

**7. DETERMINING WINNERS**

a. Each Submission will be scored and ranked by the evaluation metric stated on the Competition
Website. During the Competition Period, the current ranking will be visible on the Competition
Website's Public Leaderboard. The potential winner(s) are determined solely by the leaderboard
ranking on the Private Leaderboard, subject to compliance with these Rules. The Public
Leaderboard will be based on the public test set and the Private Leaderboard will be based on
the private test set.
b. In the event of a tie, the Submission that was entered first to the Competition will be the
winner. In the event a potential winner is disqualified for any reason, the Submission that
received the next highest score rank will be chosen as the potential winner.

**8. NOTIFICATION OF WINNERS & DISQUALIFICATION**

a. The potential winner(s) will be notified by email.
b. If a potential winner (i) does not respond to the notification attempt within one (1) week
from the first notification attempt or (ii) notifies Kaggle within one week after the Final
Submission Deadline that the potential winner does not want to be nominated as a winner or does
not want to receive a Prize, then, in each case (i) and (ii) such potential winner will not
receive any Prize, and an alternate potential winner will be selected from among all eligible
entries received based on the Competition's judging criteria.
c. In case (i) and (ii) above Kaggle may disqualify the Participant. However, in case (ii) above,
if requested by Kaggle, such potential winner may provide code and documentation to verify the
Participant's compliance with these Rules. If the potential winner provides code and
documentation to the satisfaction of Kaggle, the Participant will not be disqualified pursuant to
this paragraph.
d. Competition Sponsor reserves the right to disqualify any Participant from the Competition if
the Competition Sponsor reasonably believes that the Participant has attempted to undermine the
legitimate operation of the Competition by cheating, deception, or other unfair playing practices
or abuses, threatens or harasses any other Participants, Competition Sponsor or Kaggle.
e. A disqualified Participant may be removed from the Competition leaderboard, at Kaggle's sole
discretion. If a Participant is removed from the Competition Leaderboard, additional winning
features associated with the Kaggle competition platform, for example Kaggle points or medals,
may also not be awarded.
f. The final leaderboard list will be publicly displayed at Kaggle.com. Determinations of
Competition Sponsor are final and binding.

**9. PRIZES**

a. Prize(s) are as described on the Competition Website and are only available for winning
during the time period described on the Competition Website. The odds of winning any Prize
depends on the number of eligible Submissions received during the Competition Period and the
skill of the Participants.
b. All Prizes are subject to Competition Sponsor's review and verification of the Participant's
eligibility and compliance with these Rules, and the compliance of the winning Submissions with
the Submissions Requirements. In the event that the Submission demonstrates non-compliance with
these Competition Rules, Competition Sponsor may at its discretion take either of the following
actions: (i) disqualify the Submission(s); or (ii) require the potential winner to remediate
within one week after notice all issues identified in the Submission(s) (including, without
limitation, the resolution of license conflicts, the fulfillment of all obligations required by
software licenses, and the removal of any software that violates the software restrictions).
c. A potential winner may decline to be nominated as a Competition winner in accordance with
Section 3.8.
d. Potential winners must return all required Prize acceptance documents within two (2) weeks
following notification of such required documents, or such potential winner will be deemed to
have forfeited the prize and another potential winner will be selected. Prize(s) will be awarded
within approximately thirty (30) days after receipt by Competition Sponsor or Kaggle of the
required Prize acceptance documents. Transfer or assignment of a Prize is not allowed.
e. You are not eligible to receive any Prize if you do not meet the Eligibility requirements in
Section 2.7 and Section 3.1 above.
f. If a Team wins a monetary Prize, the Prize money will be allocated in even shares between the
eligible Team members, unless the Team unanimously opts for a different Prize split and notifies
Kaggle before Prizes are issued.

**10. TAXES**

a. ALL TAXES IMPOSED ON PRIZES ARE THE SOLE RESPONSIBILITY OF THE WINNERS. Payments to potential
winners are subject to the express requirement that they submit all documentation requested by
Competition Sponsor or Kaggle for compliance with applicable state, federal, local and foreign
(including provincial) tax reporting and withholding requirements. Prizes will be net of any
taxes that Competition Sponsor is required by law to withhold. If a potential winner fails to
provide any required documentation or comply with applicable laws, the Prize may be forfeited
and Competition Sponsor may select an alternative potential winner. Any winners who are U.S.
residents will receive an IRS Form-1099 in the amount of their Prize.

**11. GENERAL CONDITIONS**

a. All federal, state, provincial and local laws and regulations apply.

**12. PUBLICITY**

a. You agree that Competition Sponsor, Kaggle and its affiliates may use your name and likeness
for advertising and promotional purposes without additional compensation, unless prohibited by
law.

**13. PRIVACY**

a. You acknowledge and agree that Competition Sponsor and Kaggle may collect, store, share and
otherwise use personally identifiable information provided by you during the Kaggle account
registration process and the Competition, including but not limited to, name, mailing address,
phone number, and email address ("Personal Information"). Kaggle acts as an independent
controller with regard to its collection, storage, sharing, and other use of this Personal
Information, and will use this Personal Information in accordance with its Privacy Policy
<www.kaggle.com/privacy>, including for administering the Competition. As a Kaggle.com account
holder, you have the right to request access to, review, rectification, portability or deletion
of any personal data held by Kaggle about you by logging into your account and/or contacting
Kaggle Support at <www.kaggle.com/contact>.
b. As part of Competition Sponsor performing this contract between you and the Competition
Sponsor, Kaggle will transfer your Personal Information to Competition Sponsor, which acts as an
independent controller with regard to this Personal Information. As a controller of such Personal
Information, Competition Sponsor agrees to comply with all U.S. and foreign data protection
obligations with regard to your Personal Information. Kaggle will transfer your Personal
Information to Competition Sponsor in the country specified in the Competition Sponsor Address
listed above, which may be a country outside the country of your residence. Such country may not
have privacy laws and regulations similar to those of the country of your residence.

**14. WARRANTY, INDEMNITY AND RELEASE**

a. You warrant that your Submission is your own original work and, as such, you are the sole and
exclusive owner and rights holder of the Submission, and you have the right to make the
Submission and grant all required licenses. You agree not to make any Submission that: (i)
infringes any third party proprietary rights, intellectual property rights, industrial property
rights, personal or moral rights or any other rights, including without limitation, copyright,
trademark, patent, trade secret, privacy, publicity or confidentiality obligations, or defames
any person; or (ii) otherwise violates any applicable U.S. or foreign state or federal law.
b. To the maximum extent permitted by law, you indemnify and agree to keep indemnified
Competition Entities at all times from and against any liability, claims, demands, losses,
damages, costs and expenses resulting from any of your acts, defaults or omissions and/or a
breach of any warranty set forth herein. To the maximum extent permitted by law, you agree to
defend, indemnify and hold harmless the Competition Entities from and against any and all claims,
actions, suits or proceedings, as well as any and all losses, liabilities, damages, costs and
expenses (including reasonable attorneys fees) arising out of or accruing from: (a) your
Submission or other material uploaded or otherwise provided by you that infringes any third party
proprietary rights, intellectual property rights, industrial property rights, personal or moral
rights or any other rights, including without limitation, copyright, trademark, patent, trade
secret, privacy, publicity or confidentiality obligations, or defames any person; (b) any
misrepresentation made by you in connection with the Competition; (c) any non-compliance by you
with these Rules or any applicable U.S. or foreign state or federal law; (d) claims brought by
persons or entities other than the parties to these Rules arising from or related to your
involvement with the Competition; and (e) your acceptance, possession, misuse or use of any
Prize, or your participation in the Competition and any Competition-related activity.
c. You hereby release Competition Entities from any liability associated with: (a) any
malfunction or other problem with the Competition Website; (b) any error in the collection,
processing, or retention of any Submission; or (c) any typographical or other error in the
printing, offering or announcement of any Prize or winners.

**15. INTERNET**

a. Competition Entities are not responsible for any malfunction of the Competition Website or any
late, lost, damaged, misdirected, incomplete, illegible, undeliverable, or destroyed Submissions
or entry materials due to system errors, failed, incomplete or garbled computer or other
telecommunication transmission malfunctions, hardware or software failures of any kind, lost or
unavailable network connections, typographical or system/human errors and failures, technical
malfunction(s) of any telephone network or lines, cable connections, satellite transmissions,
servers or providers, or computer equipment, traffic congestion on the Internet or at the
Competition Website, or any combination thereof, which may limit a Participant's ability to
participate.

**16. RIGHT TO CANCEL, MODIFY OR DISQUALIFY**

a. If for any reason the Competition is not capable of running as planned, including infection by
computer virus, bugs, tampering, unauthorized intervention, fraud, technical failures, or any
other causes which corrupt or affect the administration, security, fairness, integrity, or proper
conduct of the Competition, Competition Sponsor reserves the right to cancel, terminate, modify
or suspend the Competition. Competition Sponsor further reserves the right to disqualify any
Participant who tampers with the submission process or any other part of the Competition or
Competition Website. Any attempt by a Participant to deliberately damage any website, including
the Competition Website, or undermine the legitimate operation of the Competition is a violation
of criminal and civil laws. Should such an attempt be made, Competition Sponsor and Kaggle each
reserves the right to seek damages from any such Participant to the fullest extent of the
applicable law.

**17. NOT AN OFFER OR CONTRACT OF EMPLOYMENT**

a. Under no circumstances will the entry of a Submission, the awarding of a Prize, or anything in
these Rules be construed as an offer or contract of employment with Competition Sponsor or any of
the Competition Entities. You acknowledge that you have submitted your Submission voluntarily and
not in confidence or in trust. You acknowledge that no confidential, fiduciary, agency,
employment or other similar relationship is created between you and Competition Sponsor or any of
the Competition Entities by your acceptance of these Rules or your entry of your Submission.

**18. DEFINITIONS**

a. "**Competition Data**" are the data or datasets available from the Competition Website for the
purpose of use in the Competition, including any prototype or executable code provided on the
Competition Website. The Competition Data will contain private and public test sets. Which data
belongs to which set will not be made available to Participants.
b. An "**Entry**" is when a Participant has joined, signed up, or accepted the rules of a
competition. Entry is required to make a Submission to a competition.
c. A "**Final Submission**" is the Submission selected by the user, or automatically selected by
Kaggle in the event not selected by the user, that is/are used for final placement on the
competition leaderboard.
d. A "**Participant**" or "**Participant User**" is an individual who participates in a
competition by entering the competition and making a Submission.
e. The "**Private Leaderboard**" is a ranked display of Participants' Submission scores against
the private test set. The Private Leaderboard determines the final standing in the competition.
f. The "**Public Leaderboard**" is a ranked display of Participants' Submission scores against a
representative sample of the test data. This leaderboard is visible throughout the competition.
g. A "**Sponsor**" is responsible for hosting the competition, which includes but is not limited
to providing the data for the competition, determining winners, and enforcing competition rules.
h. A "**Submission**" is anything provided by the Participant to the Sponsor to be evaluated for
competition purposes and determine leaderboard position. A Submission may be made as a model,
notebook, prediction file, or other format as determined by the Sponsor.
i. A "**Team**" is one or more Participants participating together in a Kaggle competition, by
officially merging together as a Team within the competition platform.

---

## Ver também

- `scope.md` — versão distilada em português, com as regras específicas do desafio (fora das
  Foundational Rules) organizadas por tema e com a tabela de efeito prático de cada seção das
  Foundational Rules sobre este projeto.
- `explicação_jus_brasil.md` — explicação didática de por que a métrica funciona assim, com
  exemplo numérico do IoU.
- `DEFINE.md` — requisitos internos de engenharia derivados destas regras.
