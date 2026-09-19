# Análise de erro — linha de base só-regras

**Data:** 2026-09-18 · **Versão:** `main` sem commit (A + B + C + D + integração) · **Sem encoder, sem LLM, sem confiança.**
Gerado por `rodar` + `avaliar` sobre a amostra oficial e sobre `gerar-sintetico --pares 100 --semente 0`.

> **Cuidado (ADR-009).** A amostra é a mesma que o leaderboard da fase de treino usa. Uma nota alta nela **não**
> prova generalização. O número que informa é o do **sintético** e, dentro dele, o **controle**.

## 1. Números

| Conjunto | Docs | Score final | Nível 1 | Nível 2 | τ | Recall de spans |
|---|---|---|---|---|---|---|
| Amostra (26 docs) | 26 | **0,9885** | 1,0000 | 0,9827 | 0 | 192/192 |
| ↳ ajuste | 14 | 0,9955 | 1,0000 | 0,9932 | 0 | 101/101 |
| ↳ controle | 12 | 0,9823 | 1,0000 | 0,9734 | 0 | 91/91 |
| Sintético (100 pares) | 200 | **0,8864** | 0,9004 | 0,8793 | 0 | 821/994 (82,6%) |
| ↳ treino | 160 | 0,8875 | 0,9018 | 0,8804 | 0 | 649/784 (82,8%) |
| ↳ controle | 40 | 0,8817 | 0,8947 | 0,8751 | 0 | 172/210 (81,9%) |

Tempo de execução na amostra: ~0,1 s de processamento (extração 0,05 s), fora a indexação da base (~0,3 s).

## 2. O que está certo

- **Nenhuma citação inventada foi chamada de real** (τ = 0) em nenhum conjunto.
- **Precisão de span 100%**: nenhum span espúrio, nem na amostra nem no sintético (as frases distratoras — "jurisprudência
  pacífica", "fls. 10/20", protocolo — nunca viram citação, R33).
- **No sintético, toda citação que a extração acha recebe a classe certa**: 360 reais, 292 inventadas e 169 incompletas,
  matriz de confusão sem nenhum elemento fora da diagonal. A cadeia A → B → D concorda.
- **R35 (limpo × ruidoso)**: 96% dos pares têm exatamente a mesma resposta; nos outros 4% a diferença é sempre um span que
  o OCR fez a extração perder, nunca uma classe ou id diferente.
- Oito dos dez caminhos aparecem em execução. Não aparecem `lei_apelido_desconhecido` (ver seção 5) e `lei_ambigua` (a base
  não tem dois dispositivos para a mesma lei e artigo); os dois têm teste unitário.

## 3. Perdas na amostra oficial (2 de 192 citações)

| Documento | O que acontece | Veredito |
|---|---|---|
| `gen_n2_010` | `AgInt no Recurso Especial nº 1.597.443 - PR`: **dois registros idênticos** (mesma classe, cadeia, UF) → `numero_ambiguo` → `incompleta`; o gabarito diz `real` | Perda **aceita** (R7). Só se resolveria por ano/relator, que a citação não traz |
| `gen_n2_005` | `TST-AgARR-25823-78…`: cita `AgARR`, o gabarito aponta o registro `AIRR`; o pipeline resolve para o registro `ARR`+`AgRg` (`numero_desempatado`) → link errado | Ruído do gabarito. Não decorar |

## 4. Perdas de recall no sintético (173 de 994) — o que sobra a melhorar

As perdas são **só de extração**: o span não é achado. Separando pelo gêmeo limpo:

**Lacunas estruturais** (perdidas já na versão limpa; 77 por versão, 154 nos dois gêmeos):

| Causa | Citações | Exemplos | Ganho estimado no recall |
|---|---|---|---|
| Forma (d): moldes de frase novos | 36 | `julgado da Corte (TSE, 2015, Min. X)`, `decisão colegiada do STM em 2025, relatada pelo Ministro X` | +7,2 pontos |
| Classe escrita só por sigla que a tabela não tem | 31 | `EIN`, `MS`, `ROE`, `CJ`, `SLS`, `CautInom`, `LT`, `DCG`, `AP`, `AC` | +6,2 pontos |
| Súmula com `n.`/`nº` | 10 | `Súmula n. 331 do TST`, `Súmula n. 83 do STJ` | +2,0 pontos |

**Perdas só com OCR** (achadas na versão limpa, perdidas na ruidosa; 19):

| Causa | Citações | Exemplos |
|---|---|---|
| Letra no **primeiro** dígito de um grupo | 15 | `art. l.239`, `artigo I.003`, `REsp nº g.324.784` |
| Letra trocada + espaço/quebra dentro do número | 3 | `Rcl n. 7I. 346/SP` (o espaço é removido antes da letra ser convertida) |
| Outra | 1 | `art. 1. o21` |

(Ganho estimado = fração das 497 citações da versão limpa; para OCR, das 497 da ruidosa: 19 → +3,8 pontos.)

**Ressalva importante (ADR-012):** os moldes do gerador são meus. Dois dos seis moldes da forma (d) são novos de propósito e
pesam 36 das 77 perdas; a frequência real no conjunto final é desconhecida. A causa "súmula com `n.`" é a mais
confiável como problema real: **a própria base escreve `Súmula n. 83 do STJ`**. Já as siglas por extenso (`EIN`, `MS`,
`ROE`…) existem como classes na base (15 registros do STM são `EIN`), mas escritas por extenso lá; se as citações do
conjunto final usam a sigla é desconhecido.

## 5. Outros achados

- **Dois bugs de B achados na integração e já corrigidos** (com teste): (1) a UF `/RO` ou `/RR` era lida como a classe
  `RO`/`RR` (Recurso Ordinário/de Revista) e derrubava uma `real` em `numero_contradito`; (2) o `no` de "Inter**no**
  7000249…" era lido como `nº` e cortava a classe ao meio, virando `campos_nao_lidos`.
- **`lei_apelido_desconhecido` não é alcançável hoje**: o regex de lei de B só extrai identificadores que já existem na
  lista dele (que é fixa e não usa `leis.json`), então um apelido fora da tabela nunca chega à decisão — ele só não é
  extraído (recall). Ex.: `art. 5 do Estatuto da Criança`.
- **Formas fora do escopo do regex** (nunca extraídas): plural (`arts. 489 e 1.022 do CPC`), `CF/88`, lei citada com o
  artigo depois (`Lei nº 8.069/1990, art. 5º`). Não aparecem no sintético e não foram medidas.
- **`campos_nao_lidos`** (11º caminho): não ocorreu na amostra nem no sintético.

## 6. Recomendação (você decide; nada de B foi alterado por causa desta análise)

| # | Correção | Onde | Risco | Ganho medido no sintético |
|---|---|---|---|---|
| 1 | `Súmula` aceitar `n.`, `nº`, `n°` antes do número | `extracao/padroes.py` (`_compilar_sumula`) | Baixo | +2,0 pontos |
| 2 | Acrescentar a sigla (`\bein\b`, `\bms\b`…) às classes que a base já usa | `tabelas/classes.json` | Baixo, mas `AC`/`AP`/`MS` colidem com UF: só com a leitura "classe antes do número" (já corrigida) | +6,2 pontos |
| 3 | Normalizador: converter letra→dígito **antes** de remover espaço, e aceitar letra no 1º dígito do grupo | `texto/normalizacao.py` | Médio (mexe no mapa de offsets; rodar `test_normalizacao`) | +3,8 pontos |
| 4 | Generalizar a forma (d) | `extracao/padroes.py` | **Alto** (falsos positivos) | +7,2 pontos — é o caso de uso do **encoder NER** (ADR-011), melhor que mais regex |

Cada uma deve ser medida em `ajuste` + `sintético treino` e só então conferida no `controle` (ADR-009), sempre com
`verificador comparar` contra esta execução.

## 7. Como reproduzir

```bash
python -m verificador gerar-sintetico --dados desafio-jusbrasil-bracis-2026 --saida sintetico/ --pares 100 --semente 0
python -m verificador rodar   --entrada desafio-jusbrasil-bracis-2026/txt --run base
python -m verificador avaliar --run base
python -m verificador rodar   --entrada sintetico/txt --run sint --dados desafio-jusbrasil-bracis-2026
python -m verificador avaliar --run sint --gabarito sintetico/goldenset_offsets.csv
```
