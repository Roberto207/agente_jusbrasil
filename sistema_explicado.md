# Sistema explicado — como o verificador de citações funciona

Este documento conta, do começo ao fim, o que acontece com um parecer jurídico quando ele passa pelo
nosso sistema. É para ser lido por gente: sem jargão desnecessário, com exemplos. As decisões
técnicas e os requisitos formais estão em `DESIGN.md`, `DEFINE.md` e `docs/decisions/`; aqui o
objetivo é entender a ideia.

---

## Para que serve

Um parecer escrito com ajuda de IA pode citar jurisprudência e leis. Algumas citações são
verdadeiras, outras foram inventadas pelo modelo, e outras são tão vagas que não dá para conferir.
O sistema lê o parecer, encontra cada citação e dá um veredito para cada uma:

- **real** — a citação existe na base de referência do desafio, e o sistema aponta qual registro é;
- **inventada** — a citação traz um número de processo ou um artigo de lei, mas nada disso existe
  na base;
- **incompleta** — a citação não traz informação suficiente para apontar um registro só.

## A ideia central, numa comparação

Pense em alguém conferindo se um CPF existe num cadastro. A pessoa não precisa saber nada sobre o
dono do CPF: basta procurar o número. O trabalho difícil não é procurar, é **ler o número** quando
ele está borrado, escrito à mão ou com um dígito trocado.

O nosso sistema funciona igual. Para saber se uma citação é real, não é preciso "entender" o
parecer; basta procurar o número do processo (ou a lei e o artigo) na base. O difícil é ler números
sujos, como `21737l8` (um "1" que virou "l") ou `5úmula` (um "S" que virou "5").

Por isso o sistema tem duas metades:

- **uma metade que lê** — encontra as citações e extrai delas as informações. Aqui usamos regras
  e também inteligência artificial, porque ler linguagem é o que esses modelos fazem bem;
- **uma metade que decide** — procura na base e dá o veredito. Aqui **não** usamos IA, porque um
  modelo de linguagem não sabe o que existe na base e tende a dizer "parece real" para qualquer coisa
  bem escrita. Dizer "real" para uma citação inventada é o erro mais caro do desafio.

---

## O caminho em uma página

1. **Organizar a base** — uma vez só, antes de tudo.
2. **Carregar os modelos** — o modelo que ajuda a achar citações e, se ligado, o que ajuda a ler as
   difíceis.
3. **Preparar o texto** de cada parecer.
4. **Encontrar as citações.**
5. **Ler as informações** de cada citação.
6. **Decidir** o veredito consultando a base.
7. **Dizer quanto confiar** em cada veredito.
8. **Entregar** no formato exigido.
9. **Conferir** o resultado.

---

## O exemplo que vamos acompanhar

Um trecho de parecer, do tipo mais difícil (com ruído de escaneamento):

> ...conforme o **AgInt no RESP 21737l8 - SP**, e nos termos do **art. 93, IX, da Constituição da
> República**. Aliás, o **julgado do STF proferido em 2024 pela relatoria de Dias Toffoli** e a
> **Rcl 88.178/RS** reforçam a tese. A jurisprudência pacífica desta Corte caminha no mesmo sentido.

Há quatro citações em negrito e uma frase vaga no final. Vamos ver o que acontece com cada uma.

---

## Passo 1 — Organizar a base (uma vez só)

A organização do desafio entrega uma base com 1.014 registros: acórdãos de cinco tribunais
superiores (STF, STJ, STM, TSE e TST), algumas súmulas e alguns artigos de lei. É contra essa base
que toda citação é conferida.

O problema é que a base não tem uma coluna "número do processo". O número está escrito dentro do
texto de cada acórdão, e cada tribunal escreve de um jeito:

- o STJ escreve `AgRg no AGRAVO EM RECURSO ESPECIAL Nº 1.327.863 - PR`;
- o STF escreve `AG.REG. NA RECLAMAÇÃO 76.532 RIO DE JANEIRO`, com o estado por extenso;
- o STM e o TSE usam o número padrão do CNJ, longo, como `7000075-58.2022.7.00.0000`;
- o TST põe o número confiável no rodapé das páginas, não no começo.

Então, antes de tudo, o sistema lê os 1.014 registros e monta uma **ficha organizada** de cada um:
número do processo, tipo de processo, estado, tribunal, ano, relator e o identificador do registro.
Para os artigos de lei, a ficha guarda qual lei e qual artigo.

**Por que não procurar o número direto no texto da base?** Porque um acórdão cita outros acórdãos
no meio do texto. Se procurássemos o número em qualquer lugar, uma citação inventada poderia "achar"
um registro só porque aquele número aparece citado dentro dele. Testamos isso na amostra: essa busca
simples faria 2 de 40 citações inventadas parecerem reais. A ficha organizada, que guarda só o número
**do próprio registro**, não cai nessa armadilha.

Junto com a ficha, o sistema usa algumas tabelas mantidas pela equipe:

- **apelidos de leis** — `CPC`, `Código de Processo Civil` e `Lei nº 13.105/2015` são a mesma lei;
  `Constituição da República` e `Constituição Federal` também;
- **tipos de processo** — `RESP`, `Rec. Esp.`, `R.Esp.` e `Recurso Especial` são todos o mesmo
  "Recurso Especial";
- **estados** — `SP` e `São Paulo`;
- **trocas comuns de escaneamento** — `l` no lugar de `1`, `O` no lugar de `0`, `S` no lugar de `5`,
  `g` no lugar de `9`.

## Passo 2 — Carregar os modelos (uma vez por rodada)

O sistema usa dois modelos de inteligência artificial, ambos abertos e publicados:

- **o localizador de citações** — um modelo de linguagem compacto, do tipo usado para marcar trechos
  em textos (candidatos: RoBERTaLexPT ou BERTimbau, dois modelos treinados especificamente em texto
  jurídico brasileiro), treinado pela equipe para reconhecer citações jurídicas mesmo com erros de
  escaneamento. É leve, rápido, roda até em computador sem GPU e sempre dá a mesma resposta para o
  mesmo texto;
- **o leitor de casos difíceis (opcional)** — um modelo de linguagem maior, do tipo que conversa e
  escreve (candidatos: Qwen3 ou Gemma 4), usado só para as poucas citações que as regras não
  conseguem ler. Ele só entra no sistema se os testes mostrarem que ajuda.

Os dois são carregados uma vez no começo da rodada e usados para todos os pareceres.

Um critério pesa na escolha de qualquer modelo: a licença precisa ser **realmente aberta** — sem
restrição de uso comercial, aprovada por uma entidade independente (a OSI). Essa exigência, que vem
das regras da competição, já descartou candidatos que pareciam bons à primeira vista: o Gemma 3 e o
GAIA (uma versão dele afinada em português pelo CEIA-UFG) têm licenças com restrições que não passam
nesse critério.

## Passo 3 — Preparar o texto

Cada parecer passa por três cuidados antes de qualquer busca.

**Separar o cabeçalho.** Pareceres começam com um bloco de identificação: "Processo nº ...",
partes, relator, "Protocolo nº ...". Esses números não são citações — são do próprio parecer — e o
gabarito do desafio nunca os conta. O sistema identifica esse bloco e ignora tudo que está nele.

**Fazer uma cópia limpa.** O sistema cria uma versão corrigida do texto para facilitar a leitura:

- `21737l8` vira `2173718`;
- `5úmula` vira `Súmula`;
- `n°`, `No` e `n.` viram `nº`;
- quebras de linha no meio de uma citação viram espaço.

A troca de letra por número só acontece **dentro de números**. Se fosse aplicada no texto todo,
"Súmula" viraria "5úmula" e nomes de relatores seriam estragados.

**Guardar um mapa de posições.** O desafio avalia as posições das citações no **texto original**,
com todos os erros. Como as correções mudam o tamanho do texto, o sistema anota, para cada ponto da
cópia limpa, qual é o ponto correspondente no original. Assim ele pode trabalhar na cópia e entregar
as posições certas.

> O texto original nunca é modificado. A cópia limpa é só uma ferramenta de trabalho.

## Passo 4 — Encontrar as citações

O sistema procura citações de duas formas ao mesmo tempo e junta os resultados.

**Pelas regras.** São padrões escritos pela equipe para os quatro jeitos de citar que o desafio
reconhece:

| Jeito de citar | Exemplo |
|---|---|
| Tipo de processo + número | `AgInt no RESP 21737l8 - SP`, `Rcl 88.178/RS` |
| Súmula + número | `Súmula 211 do STJ` |
| Artigo + lei | `art. 93, IX, da Constituição da República` |
| Tribunal ou tipo de processo + ano + relator, sem número | `julgado do STF proferido em 2024 pela relatoria de Dias Toffoli` |

As regras são muito precisas para os formatos que já conhecemos, mas não reconhecem formas de
escrever que ninguém previu.

**Pelo localizador de citações.** O modelo treinado lê o texto e marca os trechos que parecem
citações. Ele cobre o que as regras não previram — por exemplo, uma forma de escrever que só vai
aparecer no conjunto final da competição.

**Juntando as duas.** Tudo que qualquer um dos dois encontrou vira candidato. Depois vêm dois filtros:

- **o candidato precisa se encaixar num dos quatro jeitos de citar.** É assim que "A jurisprudência
  pacífica desta Corte" fica de fora: não tem número, nem lei, nem tribunal com ano e relator. Nos
  documentos de exemplo do desafio, frases vagas assim nunca são contadas como citação (a equipe
  ainda está analisando se isso vale para o conjunto final);
- **não pode haver dois candidatos em cima do mesmo trecho.** Se as regras e o modelo marcaram a
  mesma citação com bordas um pouco diferentes, fica uma só. Isso importa muito: o desafio **recusa a
  submissão inteira** se houver citações duplicadas.

No nosso exemplo, saem quatro citações; a frase vaga é descartada.

## Passo 5 — Ler as informações de cada citação

Cada citação encontrada é desmontada em informações:

```
"AgInt no RESP 21737l8 - SP"
   tipo de processo: Recurso Especial (com um agravo interno por cima)
   número: 2173718        (lido com correção de escaneamento)
   estado: SP

"art. 93, IX, da Constituição da República"
   lei: Constituição Federal de 1988
   artigo: 93             (o inciso IX não entra na busca)

"Rcl 88.178/RS"
   tipo de processo: Reclamação
   número: 88178
   estado: RS

"julgado do STF proferido em 2024 pela relatoria de Dias Toffoli"
   tribunal: STF   ano: 2024   relator: Dias Toffoli
   número: nenhum
```

Por que o inciso não entra: a base guarda os artigos inteiros, não os incisos. "art. 93, IX" aponta
para o artigo 93.

**E quando as regras não conseguem ler?** Às vezes a citação está escrita de um jeito que as regras
não entendem — por exemplo, com o tipo de processo depois do número, como `RE 1.234.567 AgR`
(exemplo ilustrativo). Essas citações vão para uma **fila de casos difíceis**.

Se o leitor de casos difíceis estiver ligado, ele recebe a fila inteira de uma vez e devolve as
informações de cada citação. Mas há uma trava de segurança: **o número que ele devolver só é aceito
se os dígitos estiverem de fato no trecho**, permitindo apenas as trocas conhecidas de escaneamento.
Modelos de linguagem às vezes "corrigem" números por conta própria, inventando dígitos; a trava impede
que isso vire um veredito errado. Se a conferência falhar, a citação segue como se não tivesse número.

## Passo 6 — Decidir o veredito

Esta é a parte que não usa IA. Para cada citação, o sistema faz duas perguntas à base.

**Pergunta 1: quais registros têm esse número (ou essa lei e esse artigo)?** Esses são os
**candidatos**.

**Pergunta 2: desses candidatos, quais não contradizem nada do que a citação diz?** Se a citação diz
"SP" e o registro é de outro estado, ele sai. O mesmo vale para tribunal e tipo de processo. Se a
citação não menciona o estado, o estado não elimina ninguém. E se a informação foi lida com correção
de escaneamento, ela também não elimina ninguém — pode ter sido lida errado.

Com as respostas, o veredito sai assim:

| Situação | Veredito |
|---|---|
| A citação não tem número (tribunal, ano e relator apenas) | **incompleta** |
| Tem número, mas nenhum registro tem esse número | **inventada** |
| Tem número, existe registro, mas todos contradizem a citação (outro estado, outro tribunal) | **inventada** |
| Sobra exatamente um registro | **real**, com o identificador dele |
| Sobram vários registros | **incompleta** |

Aplicando ao exemplo:

| Citação | O que a base responde | Veredito |
|---|---|---|
| `AgInt no RESP 21737l8 - SP` | um registro com esse número, de SP | **real** |
| `art. 93, IX, da Constituição da República` | um registro: artigo 93 da Constituição | **real** |
| `julgado do STF ... Dias Toffoli` | sem número; nem pergunta | **incompleta** |
| `Rcl 88.178/RS` | nenhum registro com esse número | **inventada** |

**Dois casos que merecem atenção:**

- **O mesmo número em vários registros.** Um mesmo processo pode ter várias decisões na base: o
  recurso principal e depois agravos e embargos sobre ele. Se a citação diz "AgInt no REsp
  1.640.323", o sistema usa essa "cadeia" de recursos para escolher o registro certo. Se mesmo assim
  sobrarem vários, o veredito é incompleta.
- **O número emprestado.** Uma alucinação esperta usa um número que existe, mas com dados trocados —
  por exemplo, o estado errado. Como nenhum registro bate com tudo que a citação afirma, o veredito é
  inventada.

**A regra de ouro: na dúvida, nunca "real".** Qualquer situação ambígua termina em incompleta ou
inventada. Chamar de real uma citação inventada pode cortar a nota do desafio pela metade — e, fora
do desafio, é justamente o erro de carimbar uma alucinação como verificada.

Cada veredito vem com o nome do **caminho** que levou a ele ("sem número", "número ausente", "número
único", "número ambíguo" e assim por diante). Isso é usado no passo seguinte e para investigar erros.

## Passo 7 — Dizer quanto confiar

O desafio dá um bônus de até 10% para quem informa, junto com cada veredito, uma confiança entre 0 e
1 — desde que essa confiança seja honesta: alta quando acerta, baixa quando erra.

O sistema calcula isso de um jeito simples. Durante os testes, ele mede com que frequência cada
caminho acerta. Por exemplo:

- "número ausente → inventada" acerta quase sempre → confiança perto de 1;
- "número único, mas lido com correção de escaneamento" erra de vez em quando → confiança menor.

Na hora de entregar, cada citação recebe a taxa de acerto do seu caminho. Se nos testes essa
confiança não for melhor do que chutar sempre o mesmo valor, o sistema simplesmente não envia a
confiança.

## Passo 8 — Entregar

Para cada parecer, o sistema grava um arquivo com a lista de citações: onde começa e termina cada
uma no texto original, o trecho, o tipo (jurisprudência ou lei), o veredito, o identificador quando
for real e a confiança. Depois, o conversor oficial do desafio junta tudo numa planilha, que é o
arquivo enviado ao Kaggle.

## Passo 9 — Conferir

Toda rodada termina com uma checagem, e ela tem três partes.

**A nota.** O sistema calcula a nota com o mesmo script oficial que o Kaggle usa, em dois grupos de
documentos:

- os documentos de exemplo que vieram com gabarito;
- um **conjunto de controle**: parte dos exemplos separada só para medir, mais documentos sintéticos
  criados pela equipe. Nenhum deles é usado para ajustar as regras.

Comparar as duas notas mostra se o sistema está funcionando de verdade ou só "decorou" os 26
documentos de exemplo. Isso importa porque a nota final da competição vem de documentos que ninguém
viu.

**Testes de robustez.**

- o mesmo documento, com e sem erros de escaneamento, precisa dar os mesmos vereditos;
- trocar os nomes dos arquivos não pode mudar nada.

**A prova de repetição.** Antes de enviar, a rodada é feita duas vezes no mesmo ambiente. As duas
planilhas precisam ser idênticas, letra por letra. É isso que a organização vai verificar depois, se
formos finalistas.

---

## Por trás das cortinas: a preparação

Os passos acima descrevem a rodada que gera uma submissão. Antes disso, a equipe faz um trabalho de
preparação que acontece uma vez (ou poucas vezes):

**1. Criar documentos sintéticos.** Só 192 citações vieram anotadas — pouco para treinar um modelo e
pouco para testar. Então a equipe fabrica pareceres de treino em duas camadas:

- **por programa:** escolhe citações reais da base, fabrica inventadas (números que não existem,
  números emprestados com estado trocado, artigos inexistentes de leis conhecidas), cria incompletas e
  injeta erros de escaneamento. Como foi a equipe que montou, o gabarito vem pronto;
- **por um modelo de linguagem:** escreve o texto ao redor das citações, com frases variadas, para que
  os documentos não fiquem todos iguais.

Esses documentos são publicados, porque as regras só permitem treinar com dados públicos.

**2. Treinar o localizador de citações.** Com os documentos sintéticos e um conjunto público de textos
jurídicos anotados (o LeNER-Br), a equipe treina o modelo que encontra citações. O treino roda nas
GPUs gratuitas do Kaggle, e os pesos resultantes são publicados — as regras exigem isso.

**3. Medir cada peça.** Nada entra só porque parece boa ideia. O localizador é comparado com a versão
só com regras; o leitor de casos difíceis é comparado com a versão sem ele. Só fica o que melhora a
nota no conjunto de controle.

## Onde cada coisa roda

| Atividade | Onde |
|---|---|
| Criar documentos sintéticos com modelo de linguagem | GPU do Kaggle |
| Treinar o localizador de citações | GPU do Kaggle |
| Escrever regras, tabelas e testar | computador de qualquer integrante |
| Gerar cada submissão | sempre o mesmo ambiente (uma GPU do Kaggle, mesma configuração) |
| Reprodução pela organização | máquina deles: 1 GPU de 24 GB, 8 processadores, 32 GB de memória |

O sistema também funciona sem os modelos (só com regras, sem GPU), o que serve de rede de segurança.

## Como o código chega até o Kaggle

O código do sistema vive num único lugar: um repositório privado no GitHub, visível só para a
equipe. O notebook do Kaggle **não tem código escrito dentro dele** — a primeira coisa que ele faz,
toda vez que roda, é ir buscar o código nesse repositório. É o mesmo código, sempre da mesma fonte,
nunca copiado e colado numa célula.

O mecanismo, em quatro passos:

1. Um integrante cria uma **chave de acesso** no GitHub, só de leitura, que só abre esse
   repositório — nada além disso.
2. Essa chave fica guardada num cofre de senhas da própria conta do Kaggle (a aba "Secrets"), nunca
   escrita dentro do notebook nem visível para outra pessoa.
3. A primeira célula do notebook pega essa chave do cofre e a usa para baixar o repositório inteiro —
   o equivalente a um `git clone`, só que autenticado.
4. A partir daí, o notebook trata a pasta baixada como um projeto comum: instala o que falta e roda
   os mesmos comandos que rodariam numa máquina local.

Dois cuidados fazem parte desse mecanismo: a chave nunca aparece em nenhum arquivo (nem do notebook,
nem do repositório) e **o notebook sempre baixa uma versão marcada** do código (uma "etiqueta" fixa,
não "a versão mais recente de hoje"). Assim, para qualquer submissão enviada, dá para apontar
exatamente qual código a gerou.

Há ainda um detalhe de precisão. É comum, em projetos de software, empacotar um ambiente inteiro
(sistema, bibliotecas, tudo) numa caixa fechada chamada container, para garantir que ele rode igual
em qualquer lugar — normalmente com uma ferramenta chamada Docker. Isso seria o ideal aqui também,
mas **o notebook do Kaggle não aceita um container próprio**: ele já roda dentro do ambiente pronto
do Kaggle. A solução foi fixar exatamente **qual versão** desse ambiente usar (em vez de deixar
atualizar sozinho) e somar, por cima, a lista exata das dependências do projeto. Para entregar à
organização um pacote que funcione fora do Kaggle também, existe um arquivo de container — mas ele
parte do mesmo ambiente público do Kaggle, para não haver diferença entre os dois.

O passo a passo completo, com telas e comandos, está em `docs/guia_kaggle.md`.

## Regras da competição que moldam o projeto

Várias decisões deste documento não vieram só de bom senso técnico — vieram de regras específicas da
competição, que desclassificam a equipe se forem quebradas:

- **Só participam estudantes do Brasil**, em equipes de até 4 pessoas, cada uma com sua própria
  conta no Kaggle.
- **Só ferramentas e modelos de licença realmente aberta** (aprovada pela OSI, sem restringir uso
  comercial) — a regra que já descartou alguns modelos candidatos (Passo 2).
- **A solução inteira precisa caber num "envelope" de hardware fixo**: 1 GPU de 24 GB, 8
  processadores e 32 GB de memória. Passar disso desclassifica, mesmo que o sistema funcione bem na
  máquina de quem o construiu.
- **Todo modelo próprio e todo dado sintético usado no treino precisam ser publicados**, com endereço
  e versão fixa, até o fechamento das submissões.
- **Os documentos do conjunto final de avaliação nunca são lidos para ajustar regras** — só
  processados. Tentar adivinhar ou espiar as respostas certas desclassifica a equipe.
- **O código fica num repositório privado**, visível só para a equipe, enquanto a competição estiver
  rodando.
- **Toda geração feita por modelo de linguagem precisa ser determinística** (sempre a mesma resposta
  para a mesma entrada) — é por isso que cada submissão é gerada duas vezes antes de ser enviada, só
  para conferir que bateu certinho.

As regras completas estão em `scope.md`.

## O que o sistema deliberadamente não faz

- **Não deixa a IA decidir o veredito.** Modelos de linguagem não sabem o que está na base; decidir é
  papel da consulta.
- **Não conta frases vagas como citação**, porque os exemplos do desafio não contam. É uma decisão em
  análise e pode ser religada com uma configuração.
- **Não lê os documentos do conjunto final para ajustar regras.** As regras da competição proíbem, e
  isso desclassifica.
- **Não usa serviços pagos nem APIs** para gerar a submissão.

## O que fica registrado de cada rodada

- **Uma ficha de identidade:** versão do código, versões dos modelos, configuração e ambiente usados.
  Com ela dá para refazer a rodada exatamente.
- **Um relatório:** a nota em cada grupo de documentos, onde o sistema acerta e onde erra, quanto cada
  peça (regras, localizador, leitor) contribuiu, e quanto de memória e tempo foi usado.
- **Um rastro por citação:** como ela foi encontrada, o que foi lido, o que a base respondeu e por que
  o veredito saiu assim. É o primeiro lugar para olhar quando algo dá errado.

## Uma diferença importante para o mundo real

No desafio, a base é fechada: o que não está nela conta como inexistente. Num produto de verdade,
nenhuma base tem todos os processos do país. Lá, "não encontrei" não significaria "inventada", e sim
"fora da cobertura — mandar para uma pessoa conferir". O resto do sistema funcionaria do mesmo jeito,
com a base sendo atualizada continuamente conforme novas decisões são publicadas.

---

## Pequeno glossário

- **Base (ou base canônica):** o banco de dados de referência do desafio, com 1.014 registros.
- **Citação:** trecho do parecer que menciona uma decisão judicial, uma súmula ou um artigo de lei.
- **Número do processo:** o identificador de uma decisão, como `1.741.784` ou
  `7000075-58.2022.7.00.0000`.
- **Súmula:** um enunciado curto que resume o entendimento consolidado de um tribunal.
- **Relator:** o juiz ou ministro responsável por conduzir o caso.
- **Erro de escaneamento (OCR):** letras e números trocados quando um documento impresso é lido por
  computador.
- **Nível 1 e Nível 2:** os dois tipos de documento do desafio — limpos e com erros de escaneamento;
  o segundo vale o dobro na nota.
- **Gabarito:** as respostas certas dos documentos de exemplo.
- **Conjunto de controle:** documentos usados só para medir, nunca para ajustar.
- **Pesos de um modelo:** o arquivo que contém o que o modelo aprendeu no treino.
- **Licença aberta (aprovada pela OSI):** selo dado por uma organização independente a licenças de
  software que garantem liberdade de uso, inclusive comercial — o padrão que os modelos e bibliotecas
  do projeto precisam seguir.
- **Ambiente de avaliação:** o "tamanho" de computador que a organização vai usar para conferir a
  solução — 1 GPU de 24 GB, 8 processadores, 32 GB de memória.
- **Determinístico:** que sempre dá a mesma resposta para a mesma entrada, sem variar por acaso.
- **Repositório:** o lugar (no GitHub) onde o código do projeto fica guardado e organizado por
  versões; neste projeto, é privado, visível só para a equipe.

Para detalhes técnicos: `DESIGN.md` (arquitetura), `DEFINE.md` (requisitos), `docs/ia_no_pipeline.md`
(uso de IA), `docs/guia_kaggle.md` (passo a passo do repositório ao notebook) e `docs/decisions/`
(decisões registradas, uma por ADR).
