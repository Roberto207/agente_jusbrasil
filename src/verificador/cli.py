"""CLI do esqueleto andante: ambiente, indexar, rodar, avaliar, submeter."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from verificador.avaliacao.determinismo import hash_arquivo
from verificador.avaliacao.solution import montar_solution
from verificador.configuracao import Configuracao, carregar
from verificador.saida import escrever_json

PASTA_DADOS_PADRAO = "desafio-jusbrasil-bracis-2026"
TABELA_DOCUMENTOS = "documentos"


def raiz_repositorio() -> Path:
    return Path(__file__).resolve().parents[2]


def pasta_run(saida: Path, run_id: str) -> Path:
    return saida / run_id


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


_CREDENCIAL = re.compile(r"TOKEN|SECRET|KEY|PASS|CREDENTIAL|AUTH", re.IGNORECASE)


def info_kaggle() -> dict[str, str]:
    """Variáveis `KAGGLE*` do ambiente, com o valor de credenciais oculto.

    A sessão do Kaggle expõe tokens (`KAGGLE_USER_SECRETS_TOKEN` dá acesso aos secrets anexados
    enquanto a sessão vive); o manifesto vai para o Output do notebook e para o pacote reproduzível.
    """
    return {
        chave: ("<oculto>" if _CREDENCIAL.search(chave) else valor)
        for chave, valor in sorted(os.environ.items())
        if chave.startswith("KAGGLE")
    }


def info_bibliotecas() -> dict[str, str | None]:
    """Versões instaladas do que decide a saída: o `requirements.txt` final fixa exatamente estas."""
    from importlib.metadata import PackageNotFoundError, version

    saida: dict[str, str | None] = {}
    for pacote in ("torch", "transformers", "tokenizers", "safetensors", "numpy", "pandas"):
        try:
            saida[pacote] = version(pacote)
        except PackageNotFoundError:
            saida[pacote] = None
    return saida


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
        "bibliotecas": info_bibliotecas(),
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
    """Constrói o índice da base e imprime o diagnóstico da frente A."""
    from verificador.base import construir_indice

    db = caminho_db(dados)
    indice = construir_indice(db)

    sem_id = indice.sem_numero()
    repetidos = indice.numeros_repetidos()
    por_natureza: dict[str, int] = {}
    for registro in indice.registros:
        por_natureza[registro.natureza] = por_natureza.get(registro.natureza, 0) + 1

    print(f"{db}: {len(indice)} registros em `{TABELA_DOCUMENTOS}`")
    for natureza, quantidade in sorted(por_natureza.items()):
        print(f"  {natureza}: {quantidade}")
    print(f"  sem número próprio: {len(sem_id)} {[r.id for r in sem_id]}")
    print(f"  números em mais de um registro: {len(repetidos)}")
    return len(indice)


def cmd_rodar(
    *,
    entrada: Path,
    run_id: str,
    saida: Path,
    dados: Path | None = None,
    usar_encoder: bool | None = None,
    usar_llm: bool | None = None,
) -> Path:
    from collections import Counter

    from verificador.avaliacao.rastro import escrever_rastro, linha_de_rastro
    from verificador.base import construir_indice
    from verificador.decisao.confianca import hash_tabela
    from verificador.pipeline import processar_documento
    from verificador.saida import ErroDeSaida
    from verificador.tabelas import hash_tabelas

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
    if cfg.usar_llm:
        raise SystemExit("usar_llm ainda não está implementado nesta versão (Fase 5)")
    encoder = None
    if cfg.usar_encoder:
        if not cfg.encoder_link:
            raise SystemExit("usar_encoder exige encoder_link (verificador.toml ou VERIFICADOR_ENCODER_LINK)")
        from verificador.extracao.encoder import Encoder

        encoder = Encoder(cfg.encoder_link, cfg.encoder_revisao)
    destino_run = pasta_run(saida, run_id)
    pasta_jsons = destino_run / "jsons"
    pasta_jsons.mkdir(parents=True, exist_ok=True)

    indice = construir_indice(db)
    tempos: dict[str, float] = {}
    por_classe: Counter[str] = Counter()
    por_caminho: Counter[str] = Counter()
    rastro: list[dict[str, Any]] = []
    for txt in txts:
        documento_id = txt.stem
        with txt.open(encoding="utf-8", newline="") as fh:  # sem tradução de \r\n: offsets exatos (R2)
            texto = fh.read()
        citacoes = processar_documento(texto, indice, tempos, encoder)
        try:
            escrever_json(documento_id, citacoes, pasta_jsons, texto)
        except ErroDeSaida as erro:
            raise SystemExit(f"saída inválida em {documento_id}:\n{erro}") from erro
        for c in citacoes:
            por_classe[c.resolucao.classificacao] += 1
            por_caminho[c.resolucao.caminho] += 1
            rastro.append(linha_de_rastro(documento_id, c))
    escrever_rastro(destino_run, rastro)

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
            },
            "execucao": {
                "documentos": len(txts),
                "citacoes": sum(por_classe.values()),
                "por_classe": dict(sorted(por_classe.items())),
                "por_caminho": dict(sorted(por_caminho.items())),
                "tempos_s": {etapa: round(seg, 3) for etapa, seg in sorted(tempos.items())},
            },
            "hashes": {
                "tabelas": hash_tabelas(),
                "base": hash_arquivo(db),
                "json_to_submission": hash_arquivo(script),
                "taxa_acerto": hash_tabela(),
            },
        }
    )
    gravar_json(destino_run / "manifesto.json", manifesto)
    print(f"submission: {submission} ({len(txts)} documentos, {sum(por_classe.values())} citações {dict(por_classe)})")
    return submission


def cmd_avaliar(
    *,
    run_id: str,
    saida: Path,
    gabarito: Path | None = None,
    dados: Path | None = None,
    conjunto: str = "todos",
) -> dict[str, Any]:
    import pandas as pd

    from verificador.avaliacao import divisao, rastro as rastro_mod, relatorio

    destino_run = pasta_run(saida, run_id)
    submission_path = destino_run / "submission.csv"
    if not submission_path.is_file():
        raise SystemExit(f"submission ausente: {submission_path} — rode `verificador rodar` antes")

    manifesto_path = destino_run / "manifesto.json"
    manifesto: dict[str, Any] = {}
    if manifesto_path.is_file():
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))

    if dados is not None:
        dados_resolvido = dados
    elif manifesto.get("argumentos", {}).get("dados"):
        dados_resolvido = Path(manifesto["argumentos"]["dados"])
    else:
        dados_resolvido = resolver_dados(None, None)
    if gabarito is None:
        gabarito = dados_resolvido / "goldenset_offsets.csv"
    gabarito = gabarito.resolve()
    if not gabarito.is_file():
        raise SystemExit(f"gabarito ausente: {gabarito}")

    disponiveis = divisao.conjuntos_disponiveis(gabarito)
    if conjunto != "todos" and conjunto not in disponiveis:
        raise SystemExit(f"conjunto {conjunto!r} não existe para este gabarito; use {list(disponiveis)}")
    escolhidos = disponiveis if conjunto == "todos" else (conjunto,)

    # A métrica oficial mora na pasta de dados, não ao lado de um gabarito que pode ser sintético.
    metrica = importar_modulo("kaggle_metric_oficial", dados_resolvido / "kaggle_metric.py")
    solution = montar_solution(gabarito)
    submission = pd.read_csv(submission_path, dtype={"documento_id": str, "citacoes": str})

    resultados: dict[str, dict[str, Any]] = {}
    for nome in escolhidos:
        docs = divisao.documentos_do_conjunto(nome, gabarito)
        try:
            resultado = relatorio.avaliar_conjunto(metrica, solution, submission, docs)
            analise = relatorio.analisar(metrica, solution, submission, docs)
        except metrica.ParticipantVisibleError as erro:
            raise SystemExit(f"submissão rejeitada pelo kaggle_metric: {erro}") from erro
        resultados[nome] = {"resultado": resultado, "analise": analise}

    rastro = rastro_mod.carregar_rastro(destino_run)
    trechos = _trechos_do_gabarito(gabarito)
    (destino_run / "relatorio.md").write_text(
        relatorio.formatar_relatorio(run_id, resultados, rastro_mod.contar_caminhos(rastro)), encoding="utf-8"
    )
    (destino_run / "relatorio.json").write_text(relatorio.relatorio_json(resultados), encoding="utf-8")
    (destino_run / "erros.md").write_text(
        relatorio.formatar_erros(run_id, resultados, rastro, trechos), encoding="utf-8"
    )
    print((destino_run / "relatorio.md").read_text(encoding="utf-8"))
    print(f"relatorio: {destino_run / 'relatorio.md'}")
    return resultados[escolhidos[0]]["resultado"]


def _trechos_do_gabarito(gabarito: Path) -> dict[tuple[str, int, int], str]:
    with gabarito.open(encoding="utf-8-sig", newline="") as fh:
        return {
            (l["documento_id"], int(l["inicio"]), int(l["fim"])): l["trecho"].replace("\\n", " ")
            for l in csv.DictReader(fh)
        }


def criar_tag_git(cwd: Path, tag: str, mensagem: str) -> None:
    """Tag anotada no commit atual (R31). Falha alto: submissão sem tag não vale."""
    proc = subprocess.run(
        ["git", "tag", "-a", tag, "-m", mensagem], cwd=cwd, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise SystemExit(f"não foi possível criar a tag {tag}: {(proc.stderr or proc.stdout).strip()}")


def cmd_submeter(*, run_id: str, saida: Path, criar_tag: bool = False) -> str:
    """Confere R31 e R49 e (com `criar_tag`) cria a tag `sub-NNN`. Devolve o nome da tag."""
    import shutil

    from verificador.avaliacao.determinismo import csv_identicos, proximo_tag

    destino_run = pasta_run(saida, run_id)
    submission = destino_run / "submission.csv"
    if not submission.is_file():
        raise SystemExit(f"submission ausente: {submission}")

    raiz = raiz_repositorio()
    git = info_git(raiz)
    if git.get("arvore_suja"):
        raise SystemExit("árvore git suja — commite (ou descarte) as mudanças antes de submeter (R31)")
    if git.get("commit") is None:
        raise SystemExit("não foi possível ler o commit git")

    manifesto_path = destino_run / "manifesto.json"
    if not manifesto_path.is_file():
        raise SystemExit(f"manifesto ausente: {manifesto_path} — a execução precisa vir de `verificador rodar`")
    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    argumentos = manifesto.get("argumentos", {})
    if not argumentos.get("entrada"):
        raise SystemExit("manifesto sem `argumentos.entrada`; não dá para repetir a execução (R49)")
    if manifesto.get("git", {}).get("commit") not in (None, git["commit"]):
        raise SystemExit("a execução foi feita em outro commit; rode `rodar` de novo neste commit (R31)")

    # R49: mesma entrada, mesmo commit, mesma configuração → CSV idêntico byte a byte.
    cfg = manifesto.get("config", {})
    repeticoes = [f"{run_id}.r49a", f"{run_id}.r49b"]
    try:
        gerados = [
            cmd_rodar(
                entrada=Path(argumentos["entrada"]),
                run_id=nome,
                saida=saida,
                dados=Path(argumentos["dados"]) if argumentos.get("dados") else None,
                usar_encoder=cfg.get("usar_encoder"),
                usar_llm=cfg.get("usar_llm"),
            )
            for nome in repeticoes
        ]
        if not (csv_identicos(gerados[0], gerados[1]) and csv_identicos(gerados[0], submission)):
            raise SystemExit("execuções repetidas geraram CSV diferente: submissão recusada (R49)")
    finally:
        for nome in repeticoes:
            shutil.rmtree(pasta_run(saida, nome), ignore_errors=True)

    tags = (_git(["tag", "-l", "sub-*"], raiz) or "").splitlines()
    tag = proximo_tag(tags)
    print(f"R49 ok: duas execuções idênticas (sha256 {hash_arquivo(submission)[:16]})")
    if not criar_tag:
        print(f"faria: git tag -a {tag}  (commit {git['commit'][:12]}) — passe --criar-tag para criar")
        return tag
    criar_tag_git(raiz, tag, f"submissão da execução {run_id} (commit {git['commit'][:12]})")
    manifesto["submissao"] = {"tag": tag, "commit": git["commit"], "sha256_csv": hash_arquivo(submission)}
    gravar_json(manifesto_path, manifesto)
    print(f"tag criada: {tag}")
    return tag


def cmd_comparar(*, run_a: str, run_b: str, saida: Path) -> Path:
    from verificador.avaliacao.comparar import comparar_runs

    pasta_a, pasta_b = pasta_run(saida, run_a), pasta_run(saida, run_b)
    for pasta in (pasta_a, pasta_b):
        if not (pasta / "relatorio.json").is_file():
            raise SystemExit(f"{pasta / 'relatorio.json'} ausente — rode `verificador avaliar` nessa execução")
    texto = comparar_runs(pasta_a, pasta_b, run_a, run_b)
    destino = pasta_b / f"comparacao_com_{run_a}.md"
    destino.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"comparacao: {destino}")
    return destino


def cmd_gerar_sintetico(*, dados: Path, saida: Path, pares: int, semente: int) -> Path:
    from verificador.sintetico import gerar_dataset

    destino = gerar_dataset(dados, saida, pares, semente)
    print(f"dataset sintético: {destino} ({pares} pares limpo×ruidoso, semente {semente})")
    return destino


def cmd_calibrar(
    *,
    run_id: str,
    saida: Path,
    dados: Path | None = None,
    gabarito: Path | None = None,
    run_sintetico: str | None = None,
    gabarito_sintetico: Path | None = None,
    destino: Path | None = None,
) -> Path:
    """Gera `taxa_acerto.json` no controle da amostra (+ sintético, se informado)."""
    from verificador.avaliacao.calibrar import (
        destino_padrao,
        gravar_tabela,
        montar_tabela,
        observacoes_do_run,
    )
    from verificador.avaliacao.divisao import documentos_do_conjunto
    from verificador.decisao.confianca import carregar as recarregar

    pasta_dados = resolver_dados(dados, None)
    gabarito_amostra = (gabarito or pasta_dados / "goldenset_offsets.csv").resolve()
    metrica = importar_modulo("kaggle_metric_oficial", pasta_dados / "kaggle_metric.py")

    observacoes = observacoes_do_run(
        pasta_run(saida, run_id),
        gabarito_amostra,
        documentos_do_conjunto("controle", gabarito_amostra),
        metrica,
    )
    if run_sintetico:
        if gabarito_sintetico is None:
            raise SystemExit("calibrar com --run-sintetico exige --gabarito-sintetico")
        gab_s = gabarito_sintetico.resolve()
        observacoes += observacoes_do_run(
            pasta_run(saida, run_sintetico),
            gab_s,
            documentos_do_conjunto("sintetico_controle", gab_s),
            metrica,
        )

    tabela = montar_tabela(observacoes)
    caminho = gravar_tabela(tabela, destino or destino_padrao())
    recarregar.cache_clear()
    decisao = "enviar" if tabela["enviar"] else "não enviar (R26)"
    print(
        f"tabela: {caminho} ({tabela['n_controle']} observações no controle, "
        f"brier {tabela['brier_controle']} vs constante {tabela['brier_constante']} -> {decisao})"
    )
    return caminho


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
    p_av.add_argument(
        "--conjunto",
        choices=("todos", "amostra", "ajuste", "controle", "sintetico", "sintetico_treino", "sintetico_controle"),
        default="todos",
        help="conjunto a avaliar (padrão: todos os que existem para o gabarito)",
    )

    p_sub = sub.add_parser("submeter", help="checa árvore limpa e R49; com --criar-tag cria a tag sub-NNN")
    p_sub.add_argument("--run", dest="run_id", required=True)
    p_sub.add_argument("--saida", type=Path, default=_saida_padrao())
    p_sub.add_argument("--criar-tag", action="store_true", help="cria de fato a tag git (sem isso só mostra)")

    p_gen = sub.add_parser("gerar-sintetico", help="gera dataset sintético por código (pares limpo × ruidoso)")
    p_gen.add_argument("--dados", type=Path, required=True)
    p_gen.add_argument("--saida", type=Path, required=True)
    p_gen.add_argument("--pares", type=int, default=100)
    p_gen.add_argument("--semente", type=int, default=0)

    p_cmp = sub.add_parser("comparar", help="diferença de nota e de citações entre duas execuções")
    p_cmp.add_argument("--run", dest="runs", action="append", required=True, metavar="RUN", help="informe duas vezes: antes e depois")
    p_cmp.add_argument("--saida", type=Path, default=_saida_padrao())

    p_cal = sub.add_parser("calibrar", help="gera taxa_acerto.json no controle (ADR-008 / R26)")
    p_cal.add_argument("--run", dest="run_id", required=True, help="execução da amostra oficial")
    p_cal.add_argument("--saida", type=Path, default=_saida_padrao())
    p_cal.add_argument("--dados", type=Path, default=None)
    p_cal.add_argument("--gabarito", type=Path, default=None)
    p_cal.add_argument("--run-sintetico", dest="run_sintetico", default=None)
    p_cal.add_argument("--gabarito-sintetico", dest="gabarito_sintetico", type=Path, default=None)
    p_cal.add_argument("--destino", type=Path, default=None, help="arquivo da tabela (padrão: pacote)")
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
            conjunto=args.conjunto,
        )
    elif args.comando == "submeter":
        cmd_submeter(run_id=args.run_id, saida=args.saida, criar_tag=args.criar_tag)
    elif args.comando == "gerar-sintetico":
        cmd_gerar_sintetico(dados=args.dados.resolve(), saida=args.saida, pares=args.pares, semente=args.semente)
    elif args.comando == "comparar":
        if len(args.runs) != 2:
            parser.error("`comparar` exige exatamente dois --run (antes e depois)")
        cmd_comparar(run_a=args.runs[0], run_b=args.runs[1], saida=args.saida)
    elif args.comando == "calibrar":
        cmd_calibrar(
            run_id=args.run_id,
            saida=args.saida,
            dados=args.dados,
            gabarito=args.gabarito,
            run_sintetico=args.run_sintetico,
            gabarito_sintetico=args.gabarito_sintetico,
            destino=args.destino,
        )
    else:  # pragma: no cover
        parser.error(args.comando)
