# Spec — forma (d) ancorada em invariantes

**Data:** 2026-09-21 · **ADR:** 015 (decisão), 011 (união com encoder), 009 (protocolo de medição)
**Status:** proposta, não implementada

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
- `ler_campos` não é tocada — ela reanalisa o trecho e não consome os grupos nomeados do padrão.
- Classificação da forma (d) segue `incompleta` em todos os casos.

## Passos para resolver

- [ ] Reescrever `_compilar_sem_numero()` com as âncoras; nenhum literal de conjunção no padrão.
- [ ] Resolver os dois detalhes acima (fim de frase, número no trecho).
- [ ] Escrever 8–12 moldes de estresse em `sintetico/moldes.py`, marcados como reservados, **com
      comentário registrando que autor do padrão e autor dos moldes são o mesmo** — a ressalva fica no
      artefato, não só na conversa.
- [ ] Um teste por âncora, com exemplo positivo **e** negativo.
- [ ] Medir com o protocolo das causas 2 e 4 (ver "Critérios de aceite").
- [ ] Decidir em **25/09** entre desfecho A (só regex) e B (regex + encoder), com número na mão.

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
