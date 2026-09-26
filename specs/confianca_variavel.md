# Spec — confiança variável por caminho: o que ganha, o que arrisca

**Data:** 2026-09-25 · **ADR:** 008 (confiança por caminho), 009 (anti-overfitting) · **Código:**
`src/verificador/decisao/confianca.py`, `src/verificador/avaliacao/calibrar.py`
**Status:** **PAUSADA (decisão da equipe, 25/09).** Guardada para **se e quando** o leaderboard
público da fase final (40% do conjunto cego) for ativado antes de 30/09 23h59 BRT. Até lá a
submissão usa a confiança constante atual (0,999318, `taxa_acerto.json`), e nenhuma tabela é
regravada. Os Achados 2 e 3 foram revistos e não se sustentam (ver a revisão no fim).

> **Como reabrir (só com o leaderboard da fase final ativo):**
> 1. Gerar a tabela candidata (opção 1) em **arquivo separado**, sem trocar `taxa_acerto.json`.
> 2. Enviar **as mesmas citações** duas vezes no mesmo dia: uma com a confiança constante e outra
>    com a tabela candidata. Como spans, classes e ids são iguais, a diferença de nota vem só do
>    bônus de calibração (Brier).
> 3. Só adotar a tabela se ela ganhar no leaderboard público **e** a equipe aceitar o limite da
>    medida: ela vê só os 40% públicos, não os 60% privados que decidem o ranking.
> 4. Adotar exige nova tag (`sub-NNN`) e refazer a conferência de determinismo no Kaggle.
>
> **Custo:** 2 submissões do teto diário. **Não reabrir** se a Fase 6 (README, `requirements.txt`
> fixo, tag final) ainda não estiver pronta: ela é obrigatória para a solução ser reproduzível; esta
> spec não é.

## Objetivo

Responder três perguntas: (1) a `confianca` enviada hoje varia? (2) como ela se comportaria no
conjunto sintético com ruído? (3) tornar a confiança variável melhora a nota o bastante para valer o
risco?

## Contexto: como a confiança é calculada

Pelo ADR-008, a `confianca` de uma citação é a taxa de acerto do seu **caminho de decisão**
(`numero_unico`, `lei_ausente`, `sem_numero` etc.), lida de `src/verificador/avaliacao/taxa_acerto.json`.
O `decidir` continua puro (`confianca=None`); o pipeline preenche o campo depois (`confianca.atribuir`).

Regras da tabela (`calibrar.py`):

- toda taxa é suavizada para um prior fixo e pessimista (`ALFA = 7`);
- caminho com menos de `MINIMO = 5` ocorrências fica marcado em `usou_fallback`;
- cada célula só usa a própria taxa se bater a **constante** em Brier sobre os próprios dados
  (`brier_propria < brier_pooled`); empate ou pior, herda a constante (`calibrar.py:91`). Assim
  `brier_controle <= brier_constante` vale por construção (R26).

## Achado 1 — hoje a confiança é constante

`taxa_acerto.json` tem 12 células, **todas** com `usou_constante: true` e `taxa: 0.999318`. O controle
tem 301 observações e nenhum erro (`brier_controle = brier_constante = 0,0`), então dividir por caminho
nunca bate a constante. Toda citação sai com **0,999318**. É o comportamento previsto no comentário de
`calibrar.py:17`, e não um defeito.

## Achado 2 — no sintético a acurácia cai e varia por caminho

Medição de leitura (nada gravado), sobre os runs `runs/final` (amostra) e `runs/final_sint`
(sintético), casando o rastro com o gabarito pelo alinhamento da métrica oficial. **Não foi
conferido se esses runs saíram do commit atual.**

| | Amostra | Sintético com ruído |
|---|---|---|
| Pares casados | 192 | 551 |
| Acerto | 98,96% (2 erros) | **84,75%** |
| Brier com constante 0,9993 | 0,0104 | 0,1522 |
| Bônus `0,10·(1 − Brier)` | +0,0990 | +0,0848 |

Acerto por caminho no sintético:

| Caminho | n | Acerto |
|---|---|---|
| `numero_contradito` | 48 | **50–55%** |
| `lei_unica` | 54 | 78% |
| `numero_ambiguo` | 54 | 79–88% |
| `numero_unico` | 151 | 83–93% |
| `lei_ausente` | 58 | 90% |
| `numero_ausente` | 76 | 95% |
| `sem_numero` | 108 | 94% |

Na amostra quase todo caminho tem taxa 1,0, e por isso a tabela não tem o que distinguir. Os dois
erros da amostra são `numero_ambiguo` e `numero_desempatado` (n = 1 cada).

## Achado 3 — fora da amostra, a tabela variável ganha (pouco)

Ajustar a tabela numa base e medir na outra:

| Ajuste → medição | Brier da tabela | Brier da constante |
|---|---|---|
| amostra → sintético | 0,1470 | 0,1492 |
| sintético → amostra | 0,0226 | 0,0301 |

Nos dois sentidos a tabela variável vence. Isso corrige a nota de 21/09 (`calibracao-confianca-achados`),
que registrava empate ou pior num teste com um único erro em 281.

## Quanto isso vale em nota

`score = s · (1 + 0,10 · (1 − Brier))`. Cada 0,001 de Brier vale cerca de 0,0001 de score.

- Teto do bônus: +0,10, com Brier 0. No sintético, discriminação perfeita renderia cerca de
  **+0,015** sobre a constante.
- Se o conjunto cego se parecer com a amostra (~99%), a constante 0,9993 já é quase ótima e variar não
  muda nada.
- Se se parecer com o sintético (~85%), a constante é mal calibrada e variar ajuda mais.
- Confiança nunca piora a nota (`b ≥ 0`): mandar valor só muda o tamanho do bônus.

## Opções

| # | Opção | Custo | Risco |
|---|---|---|---|
| 1 | Regenerar a tabela com amostra + sintético **inteiros** (`calibrar --run-sintetico ... --gabarito-sintetico ...`), sem restringir ao controle | Baixo: já existe no código | Sintético é mais difícil que o real; pode subcalibrar a parte fácil |
| 2 | Revisar o prior/`ALFA` com dados que têm erros | Baixo | Mexe em hiperparâmetro medido em poucos dados |
| 3 | Sinais contínuos além do caminho (nº de candidatos, `correcao_ocr`, fonte encoder, distância regex×encoder) + regressão logística ou isotônica | Alto: rastro precisa expor os campos; modelo novo | Overfitting com poucos dados; menos explicável (contra o ADR-008) |

## Recomendação

Fazer só a **opção 1** numa tabela candidata em arquivo separado, comparar o Brier fora da amostra e só
então decidir a `sub-007`. As opções 2 e 3 não se justificam pelo ganho máximo de cerca de 0,015.

## Fora de escopo e pendências

- **Confiança de citações vindas do encoder.** A tabela só tem `fonte: regras`; nesse caso `consultar`
  cai na média da classe (`taxa_media_por_classe`). Não foi verificado no `sub-006`.
- **Caminhos frágeis** (`numero_contradito`, `numero_ambiguo`) hoje recebem a mesma confiança que os
  seguros. É a maior distorção da constante.
- Trocar a tabela muda o hash no manifesto, exige nova tag `sub-NNN`, e o projeto só faz commit, tag
  ou publicação quando a equipe pede.

---

## Revisão (Claude, 25/09) — a spec, o ajuste que eu sugeri, riscos e recomendação

### 1. Os Achados 2 e 3 são um artefato de medição

Reproduzi a medida do Achado 2 e cheguei ao mesmo número (551 pares, 84,75%). A causa não é o
sistema: **o run foi comparado com outra versão do gabarito.**

- `runs/final_sint` foi gerado em **22/09 às 00h16** (commit `2cb86eb`). O `sintetico/` foi
  **regerado em 22/09 às 22h26**. Casar o rastro antigo com o gabarito novo alinha só 551 dos 994
  pares, e os "erros" são desencontros entre versões.
- No próprio relatório daquele run, avaliado na época contra o gabarito dele: **994/994 casados,
  nota 1,099959**, o que é incompatível com 85% de acerto (com isso a nota ficaria perto de 0,9).
- **No commit atual**, com a mesma medida: sintético base **994/994 (100%)**, diversificado
  **994/994 (100%)** e amostra **192/192 (100%)**, em **todos** os caminhos, inclusive
  `numero_contradito` (108/108) e `numero_ambiguo` (80/80).

O Achado 3 (a tabela variável vence a constante fora da amostra) usa os mesmos dados desalinhados,
então também não se sustenta. O Achado 1 continua certo: a confiança é constante (0,999318), e isso
é o comportamento correto quando não há erro nenhum para aprender.

### 2. O ajuste que eu sugeri também não funciona

Em 25/09 sugeri "calibrar também no LeNER-Br `dev`, onde o sistema erra". **Isso estava errado:** o
LeNER-Br só anota **onde** está a citação. Ele não diz se ela é real, inventada ou incompleta, nem
qual registro do acervo ela cita (quase nenhuma está no acervo). Não dá para medir acerto de
**classificação** nele, que é o que a tabela de confiança precisa.

Hoje, portanto, **não existe base com erros de classificação** para a tabela aprender: a amostra, o
controle e os dois sintéticos estão em 100%. Sem erro, o calibrador cai na constante, por construção
(`calibrar.py`), e está certo em cair.

### 3. Quanto a confiança pesa (simulado com a métrica oficial, na amostra)

| Erros | Confiança 1,0 | Constante 0,999318 | Ideal: 0,5 só nas erradas |
|---|---|---|---|
| 0 | 1,100000 | 1,100000 | 1,100000 |
| 1 | 1,096599 | 1,096600 | 1,096850 |
| 5 | 1,076979 | 1,076981 | 1,078169 |
| 10 | 1,045923 | 1,045929 | 1,048702 |

- Cada citação errada custa cerca de **0,0035** (queda do F1). A confiança mexe muito menos.
- Constante × 1,0: diferença desprezível nos dois sentidos (0,0000004 por erro).
- O ganho real de uma confiança variável só aparece se ela acertar **quais** citações vão errar: no
  caso ideal, de 0,00025 (1 erro) a 0,0028 (10 erros).

### 4. Riscos

- **Uma tabela errada piora a nota.** A spec diz que "confiança nunca piora a nota (`b ≥ 0`)". Isso só
  vale em relação a **não mandar** confiança. Em relação à constante, uma tabela mal calibrada
  **reduz** o bônus. Aplicando as taxas da spec (0,52 para `numero_contradito`, 0,82 para
  `numero_ambiguo`, 0,78 para `lei_unica`, 0,88 para `numero_unico`) ao sintético atual, onde essas
  citações estão todas certas, a nota cai de **1,100000 para 1,096293 (−0,0037)**. É o preço de uma
  citação errada, pago sem errar nenhuma.
- **Calibrar no sintético é circular.** O sintético é nosso; a taxa de acerto nele mede a nossa
  capacidade de gerar casos que o nosso sistema resolve, não o conjunto cego da organização.
- **Qualquer troca de tabela muda o manifesto e exige nova tag** (`sub-007`), com toda a conferência
  de determinismo de novo, a 5 dias do prazo.
- **Perda máxima da constante é pequena.** Se o conjunto cego tiver erros, a constante 0,999318 perde
  para a confiança ideal no máximo cerca de 0,003 (com 10 erros). É o teto do que se arrisca ao não
  mexer.

### 5. Outros pontos

- **Citações do encoder.** A pendência da spec não se confirma: `consultar` usa `campos.fonte`, que é
  "regras" também para o que o encoder acha (a fonte é de quem **leu os campos**, não de quem achou o
  trecho). Elas recebem a mesma confiança do caminho, como as do regex.
- **Se a equipe quiser atacar isso no futuro,** o caminho é uma base com erros de classificação
  **conhecidos** e que não seja nossa: por exemplo, o conjunto final depois de liberado o gabarito,
  ou um conjunto anotado por outra pessoa. Com isso a opção 1 da spec passa a fazer sentido.

### 6. Recomendação

**Não mudar a confiança para a submissão final.** Manter a constante 0,999318 (`taxa_acerto.json`
atual). Os dados que justificariam a tabela variável não existem hoje, e a medida que sugeria o
contrário estava desalinhada. Registrar esta revisão e a correção do Achado 2 antes que alguém
regenere a tabela a partir dele.
