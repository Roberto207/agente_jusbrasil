# Spec — auditoria multi-agente: código morto, enxugamento e overfitting

**Data:** 2026-09-24 · **ADR:** 009 (anti-overfitting), 005/011/013 (ganchos dormentes), 010/014 (reprodutibilidade)
**Status:** Etapas 0–3 feitas em 24/09 (`docs/gerais/auditoria_codigo.md`), **revalidadas em 25/09** no
código atual (seção 0 do relatório). **Aplicada em 30/09** no branch `limpeza-auditoria`, com a checagem
mecânica depois de cada commit (saída idêntica; ver "Aplicação de 30/09" no relatório).

## Objetivo

Deixar o repositório menor e mais legível antes do congelamento, achando código que não é mais usado — ou
que hoje é usado de outro jeito do que foi planejado. Bugs e overfitting entram como achados secundários.
**Nenhuma mudança de comportamento:** remoção de código morto tem que deixar o `submission.csv` byte a
byte idêntico.

## Contexto

- `src/` tem ~4,5 mil linhas em 52 arquivos (`cli.py` sozinho tem 665); `tests/` ~2,5 mil; 10 tabelas
  JSON; 6 notebooks Kaggle (`00`, `02`–`06`); ~5,9 mil linhas de specs/ADRs/docs.
- Muita coisa nasceu no esqueleto andante, antes da lógica real (ex.: o help de `rodar` na CLI ainda diz
  "JSON vazio por documento"; o docstring de `pipeline.py` fala de encoder/LLM "quando existirem").
- A Fase 6 já prevê `/code-review high` do repositório inteiro (`tarefas_equipe.md`). Esta spec
  amplia esse item: o foco principal é **enxugar**, não só achar bug.

### A distinção que guia a auditoria

O maior risco é tratar como morto o que é **dormente** ou **generalização**:

| Tipo | Definição | Exemplo real | Ação |
|---|---|---|---|
| **Morto** | nenhum chamador em `src/`, CLI, tabela ou notebook | a confirmar na Etapa 0 | remover |
| **Vestigial** | chamado, mas o motivo acabou | textos do esqueleto; `--sem-encoder`/`--sem-llm` se o encoder cair no go/no-go | simplificar |
| **Dormente** | atrás de flag, esperando decisão em aberto | `usar_encoder`, `usar_llm`, `ler_campos_llm` (stub que devolve `None`), `extrair_referencia_vaga`, `OrigemCandidata="encoder"` | **decisão humana**, amarrada ao go/no-go de 27/09 |
| **Generalização** | chamado, mas nenhum dado atual passa por ele | entrada de `classes.json`/`leis.json` que nunca casa na amostra | **manter** — é o seguro para o conjunto cego (ADR-009) |

"A amostra não exercita" ≠ "não é usado". Cortar pela cobertura da amostra seria overfitting ao contrário.

## Por que não só `/code-review ultra`

O ultra revisa o **diff do branch** em agentes na nuvem, com foco em bugs de correção, e é cobrado. Aqui:
(1) em `main` limpo o diff é vazio; (2) código morto não é o foco dele; (3) na nuvem os dados oficiais
não existem (fora do git), então o agente não roda o pipeline nem mede cobertura.

**Onde ele encaixa bem:** no fim, revisando o *branch de limpeza* — ali o diff é exatamente "o que foi
removido" e a pergunta dele ("isso quebrou algo?") é a certa. Se o custo não compensar, `/code-review high`
local cumpre o mesmo papel. Um "doctor" de código não existe como comando; o papel dele aqui é a Etapa 0.

## Desenho da análise

**Etapa 0 — dossiê determinístico (local, sem LLM).** Os agentes julgam sobre evidência, não impressão:
- `coverage` em duas passadas separadas: (a) `rodar` em amostra + controle + sintético + diversificado,
  (b) `pytest`. Classifica cada linha: produção executa / só teste executa / nunca.
- `vulture` em `src/` (definições sem referência). `vulture`/`coverage` só como dependência `dev`, nunca
  no `requirements.txt` de execução (R21).
- Mapa de chamadores: para cada função pública, quem importa em `src/`, `tests/`, notebooks e CLI.
- Tabelas: contagem de casamentos por entrada de JSON — só informativo (entrada sem casamento é
  *generalização*, não corte).
- Inventário fora do código: notebooks superados (`02`–`05` × `06_sub-005`), docs duplicados/superados,
  `docs/gerais/` × `specs/`.

**Etapa 1 — quatro agentes em paralelo, por lente** (o `src/` inteiro cabe no contexto de cada um, então
a divisão é por *pergunta*, não por pasta):

| Lente | Pergunta |
|---|---|
| A. Morto/vestigial | o que pode sair sem mudar a saída? |
| B. Enxugamento | duplicação, helpers repetidos, `cli.py` inchado, abstração com um uso só |
| C. Overfitting | regras sustentadas por n ≤ 2 exemplos, literais perto de R43, dependência de nome (R41) |
| D. Bugs | correção — dispensável se o `/code-review high` da Fase 6 já estiver agendado |

Cada achado sai com: tipo (tabela acima), `arquivo:linha`, evidência do dossiê, linhas economizadas.

**Etapa 2 — verificação adversarial.** Todo achado "remover" passa por um agente verificador cujo trabalho
é *refutar*: procurar uso dinâmico (via tabela, `getattr`), menção em ADR/spec, chamada em notebook.
Depois, checagem mecânica num worktree: `pytest` verde + `rodar`/`avaliar` nos quatro conjuntos com CSV
**idêntico** ao de antes + R49. Achado que muda a saída não é limpeza — vira spec própria.

**Etapa 3 — relatório e decisão humana.** `docs/gerais/auditoria_codigo.md` com a tabela de achados;
nada é removido antes do Roberto marcar o que aprova. Depois, commits por categoria num branch
`limpeza-auditoria`, revisado no fim (ultra ou `high`).

## O que NÃO faz parte

- Mudar comportamento, nota ou confiança.
- Remover código dormente antes do go/no-go do encoder (27/09).
- Mexer em `contratos.py` sem avisar a equipe (regra 1 da convivência).
- Usar o leaderboard como sinal.
- Adicionar dependência de execução.

## Quando rodar

Entre o go/no-go do encoder (27/09 22h) e a Fase 6 (29/09) — antes disso metade dos ganchos dormentes
ainda está em aberto. Se o prazo apertar, a Etapa 0 sozinha já dá o mapa, e o corte pode ficar para
depois da submissão final (serve para o pacote reproduzível de finalista).

## Verificação (quando implementar)

- `pytest` verde, incluindo `test_r41_*` e `test_r43_*`.
- CSV idêntico antes/depois em amostra, controle, sintético e diversificado.
- Linhas de `src/` antes/depois registradas no relatório.
