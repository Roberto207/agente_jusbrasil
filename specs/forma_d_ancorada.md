# Spec — forma (d) ancorada em invariantes

**Data:** 2026-09-21 · **ADR:** 015 (decisão), 011 (união com encoder), 009 (protocolo de medição)
**Status:** **implementada em 2026-09-21** — resultados na seção "Resultado" ao fim

## Objetivo

Fazer o extrator da forma (d) reconhecer citações cujas palavras de ligação ninguém escreveu antes,
sem perder precisão. Hoje ele só enxerga as quatro frases da amostra oficial.

## Contexto

A forma (d) é a citação de um julgado **sem número**: só tribunal, ano e relator. Sem número não há
consulta à base, então ela é sempre `incompleta` — é a definição da classe.

Das 101 citações que o sistema não achava no sintético, 29 foram resolvidas pelas causas 2 e 4
(commit `da571f1`). As **72 restantes são todas forma (d)**, e `incompleta` é a classe de F1 mais baixo:

| Classe | F1 no sintético (nível 1) |
|---|---|
| `real` | 1,0000 |
| `inventada` | 0,9882 |
| `incompleta` | **0,8295** |

### O defeito

`_compilar_sem_numero` em `src/verificador/extracao/padroes.py` transcreve as conjunções da amostra:

```python
rf"(?P<tipo_j>julgado|precedente|ac[oó]rd[aã]o)\s+do\s+(?P<tribunal_j>{_TRIBUNAL})\s+"
rf"(?:prof[ce]rido\s+em\s+(?P<ano_j1>\d{{4}})\s+pela\s+relatoria\s+(?:de|dc)\s+"
rf"|(?:de|julgado\s+em)\s+(?P<ano_j2>\d{{4}}),?\s+"
rf"(?:da\s+relatoria\s+(?:de|dc)|sob\s+relatoria\s+(?:de|dc))\s+)"
```

Acerta 32/32 na amostra e não vê nada quando a ligação muda:

```
decisão colegiada do STM em 2025, relatada pelo Ministro X     não acha
julgado da Corte (TSE, 2015, Min. Jorge Mussi)                 não acha
```

## Fix proposto

Âncoras extraídas das **31 citações reais** da amostra (dado do organizador, não invenção da equipe):

| Âncora | Vocabulário | Obrigatória |
|---|---|---|
| Gatilho | `julgad[oa]`, `precedente`, `ac[oó]rd[aã]o`, `decis[aã]o`, `aresto` — ou classe processual via `_padrao_classe()` | sim |
| Tribunal | `STF\|STJ\|STM\|TSE\|TST`, sigla ou por extenso | **não** — some quando há classe (`Rcl de 2021, Rel. Min. Rosa Weber`) |
| Ano | `(?:19\|20)\d{2}` | sim |
| Marcador de relator | `Rel\.?`, `Min\.?`, `Ministr[oa]`, `relatori[ao]`, `relatad[oa]` | sim |
| Nome | padrão `nome` já existente na função | sim |

Esboço da forma (não é o código final):

```python
_GATILHO_D   = r"(?:julgad[oa]|precedente|ac[oó]rd[aã]o|decis[aã]o|aresto)"
_MARCADOR_REL = r"(?:Rel\.?|Min\.?|Ministr[oa]|relatori[ao]|relatad[oa])"
_ANO_D       = r"(?:19|20)\d{2}"
_ENCHIMENTO  = r"(?:(?!\.\s+[A-ZÁ-Ú])[^;\n]){0,30}"   # não cruza fim de frase

# (gatilho | classe) ~ [tribunal] ~ ano ~ marcador  nome
```

**Restrição dura e auditável: o padrão não pode conter literal de conjunção** (`proferido`, `pela`,
`sob`, `da relatoria`…). Só âncoras e preenchimento genérico. É o que o impede de decorar molde, e é
verificável lendo o código — não depende da intenção de quem escreveu.

### Dois detalhes a resolver na implementação

1. **Fim de frase.** O preenchimento não pode atravessar `. ` seguido de maiúscula, senão une trechos
   não relacionados ("o STF decidiu em 2024. O Ministro X afirmou"). O esboço acima usa um padrão
   temperado; medir se o custo em desempenho é aceitável sobre documentos de ~50 KB.
2. **Número dentro do trecho.** A forma (d) não pode conter número de processo. Duas saídas: rejeitar
   no pós-filtro de `extrair`, ou confiar na resolução de sobreposição, que já dá prioridade 3 a
   `com_numero` contra 0 de `sem_numero` (`extracao/sobreposicao.py`). Verificar qual basta.

## O que NÃO muda

- `ADR-011` segue valendo: encoder em **união** com o regex. Esta spec melhora o componente de precisão
  da união, útil nos dois desfechos.
- O gancho já existe: `def extrair(t: TextoPreparado, encoder=None)` em `extracao/__init__.py`.
- ~~`ler_campos` não é tocada~~ — **errado, corrigido na implementação.** `extrair` de fato só usa o
  span, mas `campos.py::_RELATOR` tinha o **mesmo** defeito (enumerava `relatoria de|rel. min.|sob
  relatoria de`). Sem corrigi-lo, a citação era extraída e o relator não era lido, e o caminho caía em
  `campos_nao_lidos` em vez de `sem_numero` — o que muda o rastro que alimenta `taxa_acerto.json`.
  O marcador virou `MARCADOR_RELATOR`, público em `padroes.py`, para os dois usarem a mesma fonte.
- Classificação da forma (d) segue `incompleta` em todos os casos.

## Passos para resolver

- [x] Reescrever `_compilar_sem_numero()` com as âncoras; nenhum literal de conjunção no padrão.
- [x] Resolver os dois detalhes acima. **Os dois pelo mesmo mecanismo:** o preenchimento proíbe dígito,
      o que impede o span de engolir número de processo — e isso era necessário, porque a resolução de
      sobreposição **não** protege: em `sobreposicao.py`, `_contida(outra, cand)` faz o candidato maior
      substituir o menor, então um span ganancioso expulsaria o `com_numero` correto apesar da prioridade.
- [x] 10 moldes de estresse em `sintetico/moldes.py`, com a ressalva de autoria registrada no código.
- [x] Um teste por âncora, positivo e negativo (`test_extracao.py`, `test_campos.py`; 142 no total).
- [x] Medir com o protocolo das causas 2 e 4.
- [x] Decidir entre desfecho A e B — os números apontam **A**; ver "Resultado".

## Critérios de aceite — todos obrigatórios

- amostra oficial segue **32/32** na forma (d) e **192/192** no total;
- **precisão de spans 1,0** em todos os conjuntos — é o risco real de afrouxar âncora;
- **τ = 0**;
- melhora **também** no controle e no sintético-controle, não só no treino;
- `pytest` verde; determinismo R49 (duas execuções → CSV idêntico).

Item que falhe em qualquer critério é **revertido**, não ajustado até passar (ADR-009). O mesmo
protocolo pegou dois falsos positivos na rodada das causas 2 e 4 — a UF `GO` virando `90` e o guarda
de número curto rejeitando `CautInom nº 87.` pelo ponto final da frase.

## Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Âncoras unem trechos não relacionados | Preenchimento limitado, barreira de fim de frase, precisão medida em todo conjunto |
| Moldes de teste escritos por quem escreve o padrão | Proibição de literal de conjunção; ressalva registrada no código e aqui |
| Ganho no sintético não se repete no conjunto cego | Nenhuma medida de forma (d) é validável contra dado externo — ver ADR-015, Consequências |
| Custo de desempenho do preenchimento temperado | Medir tempo de `rodar` antes e depois; hoje a amostra roda em menos de 1 s |

## Verificação

```bash
pytest
python -m verificador rodar   --entrada desafio-jusbrasil-bracis-2026/txt --run X --dados desafio-jusbrasil-bracis-2026
python -m verificador rodar   --entrada sintetico/txt --run X_sint --dados desafio-jusbrasil-bracis-2026
python -m verificador avaliar --run X --dados desafio-jusbrasil-bracis-2026
python -m verificador avaliar --run X_sint --gabarito sintetico/goldenset_offsets.csv --dados desafio-jusbrasil-bracis-2026
python -m verificador comparar --run <anterior> --run X
```

Linha de base para comparar (commit `da571f1`): sintético 1,03940 com recall 922/994; sintético-controle
1,04293 com 196/210; amostra 1,08604 com 192/192.

---

## Resultado (2026-09-21)

| Conjunto | Antes (`da571f1`) | Depois | Recall |
|---|---|---|---|
| Amostra oficial | 1,08604 | **1,08603** | 192/192 → 192/192 |
| Controle (amostra) | 1,07925 | **1,07923** | 91/91 → 91/91 |
| Sintético | 1,03940 | **1,09571** | 922/994 → **988/994 (99,4%)** |
| Sintético-controle | 1,04293 | **1,08530** | 196/210 → **206/210 (98,1%)** |

Precisão de spans **1,0** e **τ = 0** em todos os conjuntos; zero spans espúrios; 142 testes verdes;
R49 determinístico nos dois conjuntos; `rodar` na amostra em 0,69 s (sem degradação).

O sintético foi **regenerado** com 10 moldes de estresse novos (16 no total), então os números do
sintético não são comparáveis linha a linha com a medição anterior — o conjunto ficou mais difícil e
ainda assim o recall subiu.

### Quanto isso mede de generalização

Dos **10 moldes que as âncoras nunca viram**, 9 são cobertos. O único que falha é deliberado (abaixo).
Isso é o mais perto de um teste honesto que o projeto consegue, com a ressalva registrada no ADR-015:
os moldes foram escritos por quem escreveu as âncoras. A proteção que resta é estrutural — o padrão
não contém literal de conjunção, então não tem como decorar nenhuma frase específica.

### Falha conhecida e deliberada

`entendimento do {trib} assentado em {ano} pela relatora Ministra {rel}` (6 citações) **não é extraída
de propósito**. Admitir `entendimento` como gatilho foi testado e reprovado: estendia o span à esquerda
num documento **real** da amostra (`gen_n1_007`: `Rcl de 2025, Rel. Min. CÁRMEN LÚCIA` virava
`entendimento a Rcl de 2025, …`). Nas 31 citações reais o gatilho nunca é essa palavra, e o `scope.md`
registra que `o entendimento sumulado sobre a matéria` aparece nos textos sem ser anotado. Proteger o
dado oficial vale mais que cobrir um molde que a própria equipe escreveu. O molde fica no gerador como
sonda permanente.

### Efeito colateral bom, na amostra oficial

Três spans ficaram **mais justos** — o padrão antigo arrastava lixo à direita:

```
antes 'julgado do TSE proferido em 2016 pela relatoria de HENRIQUE NEVES DA SILVA para'
agora 'julgado do TSE proferido em 2016 pela relatoria de HENRIQUE NEVES DA SILVA'
antes 'Rcl de 2024, Rel.  Min. Flávio Dino\npara sustentar tese'
agora 'Rcl de 2024, Rel.  Min. Flávio Dino'
```

A queda de 1,08604 para 1,08603 **não vem da extração** — vem da recalibração de `taxa_acerto.json`
(ADR-008 manda regenerar por versão), que mudou a confiança de uma única citação `numero_ambiguo`
de 0,9091 para 0,9167. É diferença na quinta casa decimal.

### Decisão da Fase 4 que estes números informam

As âncoras cobrem 9 dos 10 moldes novos mantendo precisão 1,0, **sem GPU, sem treino e sem
publicação de pesos**. Pelo limiar do ADR-015, é o **desfecho A**. O que continua sem resposta é se o
conjunto cego usa ligações fora deste repertório — e isso nenhum teste local pode responder, porque
não existe forma (d) na base oficial para calibrar.
