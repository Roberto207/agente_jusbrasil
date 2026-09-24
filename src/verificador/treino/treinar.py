"""Treina o encoder NER sobre o `dataset.jsonl` e mede nos conjuntos de controle.

Roda no Kaggle (GPU); em CPU só serve para teste de fumaça (`--max-passos`). `torch` e
`transformers` são importados dentro das funções que os usam: o resto do módulo (mistura,
métricas, escolha do modelo) é puro e testado sem eles.

Uso:
    python -m verificador.treino.treinar --dataset runs/encoder_dataset/dataset.jsonl \\
        --modelo neuralmind/bert-base-portuguese-cased \\
        --revisao 94d69c95f98f7d5b2a8700c420230ae10def0baa --saida runs/encoder/bertimbau
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from verificador.treino import bio

# Conjuntos medidos ao fim do treino. `amostra/treino` entra só como referência (é otimista:
# esteve no treino); a decisão usa `lener/dev` e os três controles.
CONJUNTOS_DE_MEDIDA = (
    "lener/dev",
    "sintetico_base/controle",
    "sintetico_diversificado/controle",
    "amostra/controle",
    "amostra/treino",
)
CONTROLES = ("sintetico_base/controle", "sintetico_diversificado/controle", "amostra/controle")
IOU_MINIMO = 0.5
RUIDO_DEV = 1  # no dev do LeNER-Br (22 citações), ganho de 1 é ruído


@dataclass(frozen=True)
class Config:
    modelo: str
    revisao: str
    semente: int = 0
    lr: float = 5e-5
    epocas: int = 5
    lote: int = 16
    aquecimento: float = 0.1
    decaimento: float = 0.01
    tamanho_janela: int = bio.TAMANHO_JANELA
    sobreposicao: int = bio.SOBREPOSICAO
    fracao_so_o_lener: float = 1 / 3
    repeticoes_amostra: int = 4
    fp16: bool = True
    max_passos: int | None = None  # teste de fumaça
    max_docs_medida: int | None = None  # teste de fumaça


@dataclass
class Janela:
    fonte: str
    documento: str
    divisao: str
    ids: list[int]  # sem [CLS]/[SEP]
    rotulos: list[int]
    so_o: bool = field(init=False)

    def __post_init__(self) -> None:
        self.so_o = all(r in (bio.ID_ROTULO["O"], bio.IGNORAR) for r in self.rotulos)


# --- puro -----------------------------------------------------------------------------------------

def ler_exemplos(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as fh:
        return [json.loads(linha) for linha in fh]


def misturar(janelas: list[Janela], cfg: Config) -> tuple[list[Janela], dict[str, int]]:
    """Só divisão `treino`. Toda janela com citação entra; das só-O do LeNER-Br entra uma fração;
    a amostra (a fonte mais parecida com o conjunto final, ~3% das janelas) é repetida."""
    rng = random.Random(cfg.semente)
    saida: list[Janela] = []
    for j in janelas:
        if j.divisao != "treino":
            continue
        if j.fonte == "lener" and j.so_o and rng.random() >= cfg.fracao_so_o_lener:
            continue
        saida.extend([j] * (cfg.repeticoes_amostra if j.fonte == "amostra" else 1))
    contagem = Counter(j.fonte for j in saida)
    return saida, dict(sorted(contagem.items()))


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    uniao = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / uniao if uniao > 0 else 0.0


def contar_acertos(
    gold: list[tuple[int, int, str]], pred: list[tuple[int, int, str]], ignorar: list[tuple[int, int]]
) -> Counter[str]:
    """Por tipo: `gold`, `achados` (IoU ≥ 0,5, mesmo tipo), `pred` e `pred_certos`.

    Previsão que toca uma região ignorada não conta como erro nem como acerto: ali a anotação
    de origem não diz o que é (número do próprio processo, jurisprudência ambígua…).
    """
    c: Counter[str] = Counter()
    for i, f, t in gold:
        c[f"{t}_gold"] += 1
        c[f"{t}_achados"] += any(tp == t and _iou((i, f), (a, b)) >= IOU_MINIMO for a, b, tp in pred)
    for a, b, t in pred:
        if any(a < fi and b > ii for ii, fi in ignorar):
            continue
        c[f"{t}_pred"] += 1
        c[f"{t}_pred_certos"] += any(tg == t and _iou((i, f), (a, b)) >= IOU_MINIMO for i, f, tg in gold)
    return c


def resumir(c: Counter[str]) -> dict[str, object]:
    saida: dict[str, object] = {}
    for t in ("JUR", "LEI"):
        g, a, p, pc = (c[f"{t}_{k}"] for k in ("gold", "achados", "pred", "pred_certos"))
        saida[t] = {
            "gold": g, "achados": a, "recall": round(a / g, 4) if g else None,
            "previstos": p, "precisao": round(pc / p, 4) if p else None,
        }
    return saida


def escolher(metricas: dict[str, dict]) -> str:
    """Principal (o primeiro) fica, a não ser que outro ganhe no `lener/dev` por mais que o ruído
    **e** não perca citação em nenhum controle."""
    nomes = list(metricas)
    principal = nomes[0]

    def achados(nome: str, conjunto: str) -> int:
        m = metricas[nome][conjunto]
        return sum(m[t]["achados"] for t in ("JUR", "LEI"))

    for outro in nomes[1:]:
        ganha_dev = achados(outro, "lener/dev") > achados(principal, "lener/dev") + RUIDO_DEV
        nao_perde = all(achados(outro, c) >= achados(principal, c) for c in CONTROLES)
        if ganha_dev and nao_perde:
            return outro
    return principal


def _progresso(feitos: int, total: int, t0: float) -> str:
    """`12s decorridos · 1.40s/item · faltam ~8.0 min`, a partir da velocidade medida até aqui."""
    decorrido = time.time() - t0
    por_item = decorrido / feitos
    faltam = por_item * (total - feitos)
    return f"{decorrido:.0f}s decorridos · {por_item:.2f}s/item · faltam ~{faltam / 60:.1f} min"


# --- com torch ------------------------------------------------------------------------------------

def janelas_do_exemplo(ex: dict, tokenizer, cfg: Config) -> list[Janela]:
    enc = tokenizer(ex["texto"], add_special_tokens=False, return_offsets_mapping=True)
    offsets = [tuple(o) for o in enc["offset_mapping"]]
    rotulos = bio.rotular(offsets, [tuple(s) for s in ex["spans"]], [tuple(s) for s in ex["ignorar"]])
    return [
        Janela(ex["fonte"], ex["documento"], ex["divisao"], enc["input_ids"][i:f], rotulos[i:f])
        for i, f in bio.janelas(len(offsets), cfg.tamanho_janela, cfg.sobreposicao)
    ]


def _lote(janelas: list[Janela], tokenizer, dispositivo):
    import torch

    n = max(len(j.ids) for j in janelas) + 2
    ids = torch.full((len(janelas), n), tokenizer.pad_token_id, dtype=torch.long)
    mascara = torch.zeros((len(janelas), n), dtype=torch.long)
    rotulos = torch.full((len(janelas), n), bio.IGNORAR, dtype=torch.long)
    for k, j in enumerate(janelas):
        seq = [tokenizer.cls_token_id, *j.ids, tokenizer.sep_token_id]
        ids[k, : len(seq)] = torch.tensor(seq)
        mascara[k, : len(seq)] = 1
        rotulos[k, 1 : 1 + len(j.rotulos)] = torch.tensor(j.rotulos)
    return ids.to(dispositivo), mascara.to(dispositivo), rotulos.to(dispositivo)


def prever(modelo, tokenizer, texto: str, cfg: Config, dispositivo, lote: int = 16) -> list[tuple[int, int, str]]:
    """Spans por caractere: cada token fica com a previsão da janela em que está mais ao centro."""
    import torch

    enc = tokenizer(texto, add_special_tokens=False, return_offsets_mapping=True)
    offsets = [tuple(o) for o in enc["offset_mapping"]]
    if not offsets:
        return []
    cortes = bio.janelas(len(offsets), cfg.tamanho_janela, cfg.sobreposicao)
    janelas = [Janela("", "", "", enc["input_ids"][i:f], [0] * (f - i)) for i, f in cortes]
    previsoes: list[list[int]] = []
    with torch.no_grad():
        for k in range(0, len(janelas), lote):
            ids, mascara, _ = _lote(janelas[k : k + lote], tokenizer, dispositivo)
            logits = modelo(input_ids=ids, attention_mask=mascara).logits
            for linha, j in zip(logits.argmax(-1).tolist(), janelas[k : k + lote]):
                previsoes.append(linha[1 : 1 + len(j.ids)])
    donos = bio.dono_por_token(len(offsets), cortes)
    rotulos = [previsoes[d][t - cortes[d][0]] for t, d in enumerate(donos)]
    return bio.decodificar(offsets, rotulos)


def medir(modelo, tokenizer, exemplos: list[dict], cfg: Config, dispositivo) -> dict[str, dict]:
    modelo.eval()
    por_conjunto: dict[str, Counter[str]] = {}
    vistos: Counter[str] = Counter()
    alvo = [ex for ex in exemplos if f"{ex['fonte']}/{ex['divisao']}" in CONJUNTOS_DE_MEDIDA]
    print(f"medindo {len(alvo)} documentos em {len(CONJUNTOS_DE_MEDIDA)} conjuntos…", flush=True)
    t0 = time.time()
    for k, ex in enumerate(alvo, start=1):
        conjunto = f"{ex['fonte']}/{ex['divisao']}"
        if k % 50 == 0:
            print(f"medição {k}/{len(alvo)} · {_progresso(k, len(alvo), t0)}", flush=True)
        if cfg.max_docs_medida is not None and vistos[conjunto] >= cfg.max_docs_medida:
            continue
        vistos[conjunto] += 1
        pred = prever(modelo, tokenizer, ex["texto"], cfg, dispositivo)
        gold = [tuple(s) for s in ex["spans"]]
        por_conjunto.setdefault(conjunto, Counter()).update(
            contar_acertos(gold, pred, [tuple(s) for s in ex["ignorar"]])  # type: ignore[arg-type]
        )
    print(f"medição concluída em {time.time() - t0:.0f}s", flush=True)
    return {c: resumir(por_conjunto.get(c, Counter())) for c in CONJUNTOS_DE_MEDIDA}


def treinar(cfg: Config, dataset: Path, saida: Path) -> dict[str, object]:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer, get_linear_schedule_with_warmup

    random.seed(cfg.semente)
    torch.manual_seed(cfg.semente)
    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    usar_fp16 = cfg.fp16 and dispositivo.type == "cuda"

    tokenizer = AutoTokenizer.from_pretrained(cfg.modelo, revision=cfg.revisao)
    if not tokenizer.is_fast:
        raise RuntimeError("precisa de tokenizador rápido (offset_mapping)")
    modelo = AutoModelForTokenClassification.from_pretrained(
        cfg.modelo,
        revision=cfg.revisao,
        num_labels=len(bio.ROTULOS),
        id2label=dict(enumerate(bio.ROTULOS)),
        label2id=bio.ID_ROTULO,
    ).to(dispositivo)

    exemplos = ler_exemplos(dataset)
    janelas = [j for ex in exemplos if ex["divisao"] == "treino" for j in janelas_do_exemplo(ex, tokenizer, cfg)]
    mistura, contagem = misturar(janelas, cfg)
    passos_por_epoca = -(-len(mistura) // cfg.lote)
    total = passos_por_epoca * cfg.epocas
    if cfg.max_passos is not None:
        total = min(total, cfg.max_passos)

    sem_decaimento = ("bias", "LayerNorm.weight")
    grupos = [
        {"params": [p for n, p in modelo.named_parameters() if not n.endswith(sem_decaimento)], "weight_decay": cfg.decaimento},
        {"params": [p for n, p in modelo.named_parameters() if n.endswith(sem_decaimento)], "weight_decay": 0.0},
    ]
    otimizador = torch.optim.AdamW(grupos, lr=cfg.lr)
    agenda = get_linear_schedule_with_warmup(otimizador, int(total * cfg.aquecimento), total)
    escala = torch.amp.GradScaler("cuda", enabled=usar_fp16)

    print(f"{len(mistura)} janelas de treino {contagem} · {total} passos · {dispositivo}", flush=True)
    rng = random.Random(cfg.semente)
    passo = 0
    t0 = time.time()
    modelo.train()
    while passo < total:
        ordem = list(range(len(mistura)))
        rng.shuffle(ordem)
        for k in range(0, len(ordem), cfg.lote):
            if passo >= total:
                break
            ids, mascara, rotulos = _lote([mistura[i] for i in ordem[k : k + cfg.lote]], tokenizer, dispositivo)
            with torch.autocast(device_type=dispositivo.type, dtype=torch.float16, enabled=usar_fp16):
                perda = modelo(input_ids=ids, attention_mask=mascara, labels=rotulos).loss
            otimizador.zero_grad(set_to_none=True)
            escala.scale(perda).backward()
            escala.unscale_(otimizador)
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            escala.step(otimizador)
            escala.update()
            agenda.step()
            passo += 1
            if passo in (1, 10) or passo % 50 == 0 or passo == total:
                print(f"passo {passo}/{total} · perda {perda.item():.4f} · {_progresso(passo, total, t0)}", flush=True)

    metricas = medir(modelo, tokenizer, exemplos, cfg, dispositivo)
    saida.mkdir(parents=True, exist_ok=True)
    modelo.save_pretrained(saida)
    tokenizer.save_pretrained(saida)
    manifesto = {
        "config": asdict(cfg),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "mistura": contagem,
        "passos": passo,
        "segundos": round(time.time() - t0),
        "dispositivo": str(dispositivo),
        "metricas": metricas,
    }
    (saida / "manifesto_treino.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifesto


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--modelo", required=True)
    p.add_argument("--revisao", required=True)
    p.add_argument("--saida", type=Path, required=True)
    p.add_argument("--epocas", type=int, default=Config.epocas)
    p.add_argument("--lote", type=int, default=Config.lote)
    p.add_argument("--max-passos", type=int)
    p.add_argument("--max-docs-medida", type=int)
    args = p.parse_args(argv)
    cfg = Config(
        modelo=args.modelo, revisao=args.revisao, epocas=args.epocas, lote=args.lote,
        max_passos=args.max_passos, max_docs_medida=args.max_docs_medida,
    )
    manifesto = treinar(cfg, args.dataset, args.saida)
    print(json.dumps(manifesto["metricas"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
