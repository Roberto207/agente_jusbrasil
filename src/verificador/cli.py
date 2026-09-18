"""CLI do esqueleto andante: ambiente, indexar, rodar, avaliar, submeter."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import platform
import sqlite3
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verificador.configuracao import Configuracao, carregar

PASTA_DADOS_PADRAO = "desafio-jusbrasil-bracis-2026"
TABELA_DOCUMENTOS = "documentos"


def raiz_repositorio() -> Path:
    return Path(__file__).resolve().parents[2]


def pasta_run(saida: Path, run_id: str) -> Path:
    return saida / run_id


def hash_arquivo(caminho: Path) -> str | None:
    if not caminho.is_file():
        return None
    digest = hashlib.sha256()
    digest.update(caminho.read_bytes())
    return digest.hexdigest()


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def info_git(cwd: Path | None = None) -> dict[str, Any]:
    raiz = cwd or raiz_repositorio()
    commit = _git(["rev-parse", "HEAD"], raiz)
    porcelain = _git(["status", "--porcelain"], raiz)
    if commit is None:
        return {"commit": None, "arvore_suja": None, "erro": "git indisponível"}
    return {
        "commit": commit,
        "arvore_suja": bool((porcelain or "").strip()),
        "status": porcelain or "",
    }


def info_gpu() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return {"disponivel": False, "motivo": "nvidia-smi não encontrado"}
    except OSError as exc:
        return {"disponivel": False, "motivo": str(exc)}
    except subprocess.TimeoutExpired:
        return {"disponivel": False, "motivo": "nvidia-smi estourou o tempo"}
    if proc.returncode != 0:
        motivo = (proc.stderr or proc.stdout or "nvidia-smi falhou").strip()
        return {"disponivel": False, "motivo": motivo}
    return {"disponivel": True, "nvidia_smi": proc.stdout.strip()}


def info_kaggle() -> dict[str, str]:
    return {chave: valor for chave, valor in sorted(os.environ.items()) if chave.startswith("KAGGLE")}


def coletar_ambiente(config: Configuracao | None = None) -> dict[str, Any]:
    raiz = raiz_repositorio()
    cfg = config if config is not None else carregar()
    requirements = raiz / "requirements.txt"
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "implementacao_python": sys.version,
        "so": platform.platform(),
        "sistema": platform.system(),
        "git": info_git(raiz),
        "gpu": info_gpu(),
        "kaggle": info_kaggle(),
        "hash_requirements": hash_arquivo(requirements),
        "config": asdict(cfg),
        "hash_configuracao": cfg.hash(),
        "imagem_docker": "gcr.io/kaggle-gpu-images/python:v170",
    }


def gravar_json(caminho: Path, dados: dict[str, Any]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def resolver_dados(dados: Path | None, entrada: Path | None = None) -> Path:
    if dados is not None:
        return dados.resolve()
    env = os.environ.get("VERIFICADOR_DADOS")
    if env:
        return Path(env).resolve()
    if entrada is not None:
        pai = entrada.resolve().parent
        if (pai / "desafio1_bracis.db").is_file() or (pai / "json_to_submission.py").is_file():
            return pai
    padrao = (Path.cwd() / PASTA_DADOS_PADRAO).resolve()
    if padrao.is_dir():
        return padrao
    return (raiz_repositorio() / PASTA_DADOS_PADRAO).resolve()


def caminho_db(dados: Path) -> Path:
    return dados / "desafio1_bracis.db"


def importar_modulo(nome: str, caminho: Path) -> Any:
    if not caminho.is_file():
        raise FileNotFoundError(f"script oficial ausente: {caminho}")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    if spec is None or spec.loader is None:
        raise ImportError(f"não foi possível carregar {caminho}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def contar_documentos(db: Path) -> int:
    if not db.is_file():
        raise FileNotFoundError(f"base canônica ausente: {db}")
    uri = db.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        (n,) = conn.execute(f"SELECT COUNT(*) FROM {TABELA_DOCUMENTOS}").fetchone()
    return int(n)


def converter_jsons_para_csv(script: Path, pasta_jsons: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(script), str(pasta_jsons), str(destino)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.returncode != 0:
        erro = (proc.stderr or proc.stdout or "json_to_submission.py falhou").strip()
        raise SystemExit(erro)


def montar_solution(gabarito: Path):
    import pandas as pd

    df = pd.read_csv(
        gabarito,
        dtype={
            "documento_id": str,
            "citacao_id": str,
            "classificacao": str,
            "id_canonico": "string",
        },
    )
    linhas: list[dict[str, Any]] = []
    for documento_id, grupo in df.groupby("documento_id", sort=True):
        nivel = int(grupo["nivel"].iloc[0])
        partes: list[str] = []
        ordenado = grupo.sort_values(["inicio", "fim"], kind="mergesort")
        for _, row in ordenado.iterrows():
            classe = str(row["classificacao"]).strip().lower()
            inicio = int(row["inicio"])
            fim = int(row["fim"])
            bruto = row["id_canonico"]
            if bruto is None or (isinstance(bruto, float) and pd.isna(bruto)) or pd.isna(bruto):
                doc_ids = "-"
            else:
                texto = str(bruto).strip()
                doc_ids = "-" if texto in ("", "<NA>", "nan", "None") else texto
            partes.append(f"{inicio},{fim},{classe},{doc_ids}")
        citacoes = "|".join(partes) if partes else "-"
        linhas.append(
            {
                "documento_id": str(documento_id),
                "nivel": nivel,
                "citacoes": citacoes,
            }
        )
    return pd.DataFrame(linhas)


def formatar_relatorio(run_id: str, resultado: dict[str, Any]) -> str:
    linhas = [
        f"# Relatório — `{run_id}`",
        "",
        "Esqueleto andante: listas de citações vazias. `score_final` baixo é esperado.",
        "",
        f"**score_final:** {float(resultado['score_final']):.6f}",
        "",
    ]
    for nivel, bloco in sorted(resultado["niveis"].items()):
        f1 = {classe: round(float(valor), 6) for classe, valor in bloco["f1_por_classe"].items()}
        linhas.extend(
            [
                f"## Nível {nivel}",
                f"- macro_f1: {float(bloco['macro_f1']):.6f}",
                f"- f1_por_classe: `{f1}`",
                f"- tau: {float(bloco['tau']):.6f}",
                f"- s: {float(bloco['s']):.6f}",
                f"- b: {float(bloco['b']):.6f}",
                f"- score: {float(bloco['score']):.6f}",
                "",
            ]
        )
    return "\n".join(linhas)


def cmd_ambiente(
    *,
    saida: Path,
    run_id: str,
    config: Configuracao | None = None,
) -> Path:
    manifesto = coletar_ambiente(config)
    manifesto["run_id"] = run_id
    destino = pasta_run(saida, run_id) / "manifesto.json"
    gravar_json(destino, manifesto)
    print(json.dumps(manifesto, ensure_ascii=False, indent=2))
    print(f"manifesto: {destino}")
    return destino


def cmd_indexar(dados: Path) -> int:
    db = caminho_db(dados)
    n = contar_documentos(db)
    print(f"{db}: {n} registros em `{TABELA_DOCUMENTOS}`")
    return n


def cmd_rodar(
    *,
    entrada: Path,
    run_id: str,
    saida: Path,
    dados: Path | None = None,
    usar_encoder: bool | None = None,
    usar_llm: bool | None = None,
) -> Path:
    entrada = entrada.resolve()
    pasta_dados = resolver_dados(dados, entrada)
    script = pasta_dados / "json_to_submission.py"
    db = caminho_db(pasta_dados)
    txts = sorted(entrada.glob("*.txt"))
    if not txts:
        raise SystemExit(f"nenhum .txt em {entrada}")
    if not script.is_file():
        raise SystemExit(f"json_to_submission.py não encontrado em {pasta_dados}")

    cfg = carregar().com_flags(usar_encoder=usar_encoder, usar_llm=usar_llm)
    destino_run = pasta_run(saida, run_id)
    pasta_jsons = destino_run / "jsons"
    pasta_jsons.mkdir(parents=True, exist_ok=True)

    for txt in txts:
        documento_id = txt.stem
        gravar_json(pasta_jsons / f"{documento_id}.json", {"documento_id": documento_id, "citacoes": []})

    submission = destino_run / "submission.csv"
    converter_jsons_para_csv(script, pasta_jsons, submission)

    manifesto = coletar_ambiente(cfg)
    manifesto.update(
        {
            "run_id": run_id,
            "argumentos": {
                "entrada": str(entrada),
                "dados": str(pasta_dados),
                "saida": str(saida.resolve()),
            },
            "caminhos": {
                "jsons": str(pasta_jsons),
                "submission": str(submission),
                "db": str(db),
                "json_to_submission": str(script),
            },
            "hash_db": hash_arquivo(db),
            "hash_json_to_submission": hash_arquivo(script),
            "documentos": len(txts),
        }
    )
    gravar_json(destino_run / "manifesto.json", manifesto)
    print(f"submission: {submission} ({len(txts)} documentos)")
    return submission


def cmd_avaliar(
    *,
    run_id: str,
    saida: Path,
    gabarito: Path | None = None,
    dados: Path | None = None,
) -> dict[str, Any]:
    import pandas as pd

    destino_run = pasta_run(saida, run_id)
    submission_path = destino_run / "submission.csv"
    if not submission_path.is_file():
        raise SystemExit(f"submission ausente: {submission_path} — rode `verificador rodar` antes")

    manifesto_path = destino_run / "manifesto.json"
    manifesto: dict[str, Any] = {}
    if manifesto_path.is_file():
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))

    if gabarito is None:
        dados_resolvido = None
        if dados is not None:
            dados_resolvido = dados
        elif manifesto.get("argumentos", {}).get("dados"):
            dados_resolvido = Path(manifesto["argumentos"]["dados"])
        else:
            dados_resolvido = resolver_dados(None, None)
        gabarito = dados_resolvido / "goldenset_offsets.csv"
    gabarito = gabarito.resolve()
    if not gabarito.is_file():
        raise SystemExit(f"gabarito ausente: {gabarito}")

    metric_path = gabarito.parent / "kaggle_metric.py"
    metrica = importar_modulo("kaggle_metric_oficial", metric_path)
    solution = montar_solution(gabarito)
    submission = pd.read_csv(submission_path, dtype={"documento_id": str, "citacoes": str})
    resultado = metrica.avaliar(solution, submission)
    relatorio = destino_run / "relatorio.md"
    relatorio.write_text(formatar_relatorio(run_id, resultado), encoding="utf-8")
    print(relatorio.read_text(encoding="utf-8"))
    print(f"relatorio: {relatorio}")
    return resultado


def cmd_submeter(*, run_id: str, saida: Path) -> None:
    destino_run = pasta_run(saida, run_id)
    submission = destino_run / "submission.csv"
    if not submission.is_file():
        raise SystemExit(f"submission ausente: {submission}")

    git = info_git()
    if git.get("arvore_suja"):
        raise SystemExit(
            "árvore git suja — commite (ou descarte) as mudanças antes de submeter (R31)"
        )
    if git.get("commit") is None:
        raise SystemExit("não foi possível ler o commit git")

    tags = _git(["tag", "-l", "sub-*"], raiz_repositorio()) or ""
    existentes = [linha for linha in tags.splitlines() if linha.strip()]
    proximo = len(existentes) + 1
    tag = f"sub-{proximo:03d}"
    print("Submissão ainda não envia nem cria tag.")
    print("TODO(R49): quando houver lógica real, rodar duas vezes e exigir CSV idêntico.")
    print(f"faria: git tag {tag}  (commit {git['commit'][:12]})")
    print(f"arquivo: {submission}")


def _saida_padrao() -> Path:
    return (Path.cwd() / "runs").resolve()


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="verificador", description="Verificador de citações jurídicas")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_amb = sub.add_parser("ambiente", help="grava manifesto com commit, GPU e hashes")
    p_amb.add_argument("--saida", type=Path, default=_saida_padrao())
    p_amb.add_argument("--run", dest="run_id", default="ambiente")

    p_idx = sub.add_parser("indexar", help="abre a base canônica em modo leitura")
    p_idx.add_argument("--dados", type=Path, required=True)

    p_run = sub.add_parser("rodar", help="JSON vazio por documento + submission.csv oficial")
    p_run.add_argument("--entrada", type=Path, required=True)
    p_run.add_argument("--run", dest="run_id", required=True)
    p_run.add_argument("--saida", type=Path, default=_saida_padrao())
    p_run.add_argument("--dados", type=Path, default=None)
    p_run.add_argument("--sem-encoder", action="store_true")
    p_run.add_argument("--sem-llm", action="store_true")

    p_av = sub.add_parser("avaliar", help="nota via kaggle_metric.py oficial")
    p_av.add_argument("--run", dest="run_id", required=True)
    p_av.add_argument("--saida", type=Path, default=_saida_padrao())
    p_av.add_argument("--gabarito", type=Path, default=None)
    p_av.add_argument("--dados", type=Path, default=None)

    p_sub = sub.add_parser("submeter", help="checa árvore limpa; tag fica para depois")
    p_sub.add_argument("--run", dest="run_id", required=True)
    p_sub.add_argument("--saida", type=Path, default=_saida_padrao())
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = construir_parser()
    args = parser.parse_args(argv)
    if args.comando == "ambiente":
        cmd_ambiente(saida=args.saida, run_id=args.run_id)
    elif args.comando == "indexar":
        cmd_indexar(args.dados.resolve())
    elif args.comando == "rodar":
        usar_encoder = False if args.sem_encoder else None
        usar_llm = False if args.sem_llm else None
        cmd_rodar(
            entrada=args.entrada,
            run_id=args.run_id,
            saida=args.saida,
            dados=args.dados,
            usar_encoder=usar_encoder,
            usar_llm=usar_llm,
        )
    elif args.comando == "avaliar":
        cmd_avaliar(
            run_id=args.run_id,
            saida=args.saida,
            gabarito=args.gabarito,
            dados=args.dados,
        )
    elif args.comando == "submeter":
        cmd_submeter(run_id=args.run_id, saida=args.saida)
    else:  # pragma: no cover
        parser.error(args.comando)
