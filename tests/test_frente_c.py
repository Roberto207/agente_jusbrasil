"""Frente C — divisão, saída, relatório, comparação, determinismo/submeter, R41 e R43."""

from __future__ import annotations

import ast
import csv
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.helpers import citacao_verificada
from verificador import cli
from verificador.avaliacao import divisao
from verificador.avaliacao.comparar import diferencas
from verificador.avaliacao.determinismo import csv_identicos, proximo_tag
from verificador.saida import ErroDeSaida, escrever_json, validar_citacoes

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def metrica(pasta_dados):
    return cli.importar_modulo("kaggle_metric_oficial", pasta_dados / "kaggle_metric.py")


def _gabarito_por_documento(gabarito):
    saida: dict[str, list[dict[str, str]]] = {}
    for linha in gabarito:
        saida.setdefault(linha["documento_id"], []).append(linha)
    return saida


def _run_do_gabarito(pasta_dados, textos, gabarito, saida: Path, run_id: str, descartar=lambda linha: False, classe=lambda linha: linha["classificacao"]):
    """Grava uma execução cujos JSONs reproduzem o gabarito (com alterações opcionais)."""
    jsons = saida / run_id / "jsons"
    for doc, linhas in _gabarito_por_documento(gabarito).items():
        citacoes = [
            citacao_verificada(
                int(l["inicio"]), int(l["fim"]), textos[doc][int(l["inicio"]) : int(l["fim"])],
                classe(l), (l["id_canonico"] or None) if classe(l) == "real" else None, tipo=l["tipo"],
            )
            for l in linhas
            if not descartar(l)
        ]
        escrever_json(doc, citacoes, jsons, textos[doc])
    cli.converter_jsons_para_csv(pasta_dados / "json_to_submission.py", jsons, saida / run_id / "submission.csv")


# -- C1: divisão ----------------------------------------------------------------------------


def test_divisao_e_particao_estratificada_da_amostra(gabarito) -> None:
    niveis = {l["documento_id"]: l["nivel"] for l in gabarito}
    ajuste, controle = divisao.documentos("ajuste"), divisao.documentos("controle")
    assert ajuste and controle and not (ajuste & controle)
    assert ajuste | controle == set(niveis) == divisao.documentos("amostra")
    for parte in (ajuste, controle):
        assert {niveis[d] for d in parte} == {"1", "2"}


def test_divisao_versionada_e_reproduzivel(pasta_dados) -> None:
    gerada = divisao.gerar_divisao(pasta_dados / "goldenset_offsets.csv")
    assert gerada == divisao.carregar_divisao()


def test_divisao_rejeita_conjunto_desconhecido() -> None:
    with pytest.raises(ValueError):
        divisao.documentos("treino")


# -- C2: saída ------------------------------------------------------------------------------


def test_json_segue_o_contrato(tmp_path) -> None:
    texto = "x" * 5 + "REsp 1" + "y" * 5 + "art. 5 da CLT"
    c1 = citacao_verificada(5, 11, "REsp 1", "real", "123", confianca=0.9)
    c2 = citacao_verificada(16, 29, "art. 5 da CLT", "inventada", tipo="lei")
    caminho = escrever_json("doc", [c2, c1], tmp_path, texto)  # fora de ordem
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados["documento_id"] == "doc"
    assert [c["inicio"] for c in dados["citacoes"]] == [5, 16]
    assert dados["citacoes"][0] == {
        "inicio": 5, "fim": 11, "trecho": "REsp 1", "tipo": "jurisprudencia",
        "classificacao": "real", "resolucao": {"id_canonico": "123"}, "confianca": 0.9,
    }
    assert dados["citacoes"][1]["resolucao"] == {} and "confianca" not in dados["citacoes"][1]


@pytest.mark.parametrize(
    "citacoes, texto, trecho_do_erro",
    [
        ([citacao_verificada(0, 10, "a" * 10, "real", "1"), citacao_verificada(2, 10, "a" * 8, "real", "2")], "a" * 10, "R3"),
        ([citacao_verificada(0, 3, "abc", "inventada", "9")], "abc", "R13"),
        ([citacao_verificada(0, 3, "abc", "real", None)], "abc", "R12"),
        ([citacao_verificada(0, 3, "abc", "real", "1")], "xyz", "R38"),
        ([citacao_verificada(0, 3, "abc", "real", "1", tipo="lei", forma="com_numero")], "abc", "R42"),
        ([citacao_verificada(0, 3, "abc", "real", "1", confianca=1.5)], "abc", "confianca"),
    ],
)
def test_validador_barra_o_que_o_kaggle_rejeitaria(citacoes, texto, trecho_do_erro) -> None:
    assert any(trecho_do_erro in p for p in validar_citacoes("d", citacoes, texto))


def test_escrever_json_recusa_saida_invalida(tmp_path) -> None:
    with pytest.raises(ErroDeSaida):
        escrever_json("d", [citacao_verificada(0, 3, "abc", "inventada", "9")], tmp_path)
    assert not list(tmp_path.glob("*.json"))


# -- C3: relatório -------------------------------------------------------------------------


def test_gabarito_como_previsao_da_nota_maxima_em_todos_os_conjuntos(pasta_dados, textos, gabarito, tmp_path) -> None:
    _run_do_gabarito(pasta_dados, textos, gabarito, tmp_path, "oraculo")
    resultado = cli.cmd_avaliar(run_id="oraculo", saida=tmp_path, dados=pasta_dados)
    assert resultado["score_final"] == pytest.approx(1.0)
    dados = json.loads((tmp_path / "oraculo" / "relatorio.json").read_text(encoding="utf-8"))
    assert set(dados) == {"amostra", "ajuste", "controle"}
    assert all(d["score_final"] == pytest.approx(1.0) for d in dados.values())
    assert all(d["analise"]["recall_spans"] == 1.0 and d["analise"]["espurios"] == 0 for d in dados.values())
    assert "Nenhum erro." in (tmp_path / "oraculo" / "erros.md").read_text(encoding="utf-8")


def test_relatorio_classifica_cada_tipo_de_erro(pasta_dados, textos, gabarito, tmp_path) -> None:
    primeiro_real = next(l for l in gabarito if l["classificacao"] == "real")
    primeira_inventada = next(l for l in gabarito if l["classificacao"] == "inventada")
    _run_do_gabarito(
        pasta_dados, textos, gabarito, tmp_path, "falho",
        descartar=lambda l: l is primeira_inventada,  # span perdido
        classe=lambda l: "incompleta" if l is primeiro_real else l["classificacao"],  # real perdida
    )
    cli.cmd_avaliar(run_id="falho", saida=tmp_path, dados=pasta_dados, conjunto="amostra")
    dados = json.loads((tmp_path / "falho" / "relatorio.json").read_text(encoding="utf-8"))
    analise = dados["amostra"]["analise"]
    assert analise["perdidos"] == 1 and analise["casadas"] == 191
    assert analise["matriz"]["real|incompleta"] == 1 and analise["matriz"]["inventada|sem_span"] == 1
    erros = (tmp_path / "falho" / "erros.md").read_text(encoding="utf-8")
    assert "Span perdido" in erros and "Real perdida" in erros


def test_conjunto_inexistente_para_o_gabarito_e_recusado(pasta_dados, textos, gabarito, tmp_path) -> None:
    _run_do_gabarito(pasta_dados, textos, gabarito, tmp_path, "r")
    copia = tmp_path / "outro.csv"  # só um documento: não é a amostra oficial
    primeiro = next(iter(_gabarito_por_documento(gabarito)))
    with copia.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=list(gabarito[0]), lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(l for l in gabarito if l["documento_id"] == primeiro)
    for ruim in ("ajuste", "controle"):
        with pytest.raises(SystemExit):
            cli.cmd_avaliar(run_id="r", saida=tmp_path, gabarito=copia, dados=pasta_dados, conjunto=ruim)


# -- C4: comparação ------------------------------------------------------------------------


def test_diferencas_entre_execucoes() -> None:
    a = {"d": [{"inicio": 0, "fim": 10, "classe": "real", "id": "1"}, {"inicio": 50, "fim": 60, "classe": "inventada", "id": "-"}]}
    b = {"d": [{"inicio": 0, "fim": 10, "classe": "incompleta", "id": "-"}, {"inicio": 100, "fim": 110, "classe": "real", "id": "2"}]}
    dif = diferencas(a, b)
    assert len(dif["mudaram"]) == 1 and len(dif["sumiram"]) == 1 and len(dif["apareceram"]) == 1


def test_comparar_mostra_a_melhora(pasta_dados, textos, gabarito, tmp_path) -> None:
    _run_do_gabarito(pasta_dados, textos, gabarito, tmp_path, "antes", descartar=lambda linha: True)  # tudo vazio
    cli.cmd_avaliar(run_id="antes", saida=tmp_path, dados=pasta_dados)
    _run_do_gabarito(pasta_dados, textos, gabarito, tmp_path, "depois")
    cli.cmd_avaliar(run_id="depois", saida=tmp_path, dados=pasta_dados)
    texto = cli.cmd_comparar(run_a="antes", run_b="depois", saida=tmp_path).read_text(encoding="utf-8")
    assert "0.0000 → 1.0000 (+1.0000)" in texto and "apareceram: 192" in texto


# -- C6: determinismo e submeter -----------------------------------------------------------


def test_proximo_tag_ignora_lacunas() -> None:
    assert proximo_tag([]) == "sub-001"
    assert proximo_tag(["sub-001", "sub-003", "outra"]) == "sub-004"


def test_csv_identicos_compara_bytes(tmp_path) -> None:
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_bytes(b"x"), b.write_bytes(b"x")
    assert csv_identicos(a, b)
    b.write_bytes(b"y")
    assert not csv_identicos(a, b)


@pytest.fixture()
def repo_limpo(tmp_path, monkeypatch, pasta_dados):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a", encoding="utf-8")
    for cmd in (["init", "-q"], ["config", "user.name", "t"], ["config", "user.email", "t@t"], ["add", "."], ["commit", "-qm", "c"]):
        subprocess.run(["git", *cmd], cwd=repo, check=True)
    monkeypatch.setattr(cli, "raiz_repositorio", lambda: repo)
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    for arquivo in sorted((pasta_dados / "txt").glob("*.txt"))[:2]:
        shutil.copy(arquivo, entrada / arquivo.name)
    cli.cmd_rodar(entrada=entrada, run_id="r", saida=tmp_path / "runs", dados=pasta_dados)
    return repo, tmp_path / "runs"


def test_submeter_confere_r49_e_so_cria_a_tag_se_pedido(repo_limpo) -> None:
    repo, saida = repo_limpo
    assert cli.cmd_submeter(run_id="r", saida=saida) == "sub-001"
    assert subprocess.check_output(["git", "tag", "-l"], cwd=repo, text=True) == ""
    cli.cmd_submeter(run_id="r", saida=saida, criar_tag=True)
    assert subprocess.check_output(["git", "tag", "-l"], cwd=repo, text=True).split() == ["sub-001"]
    assert json.loads((saida / "r" / "manifesto.json").read_text(encoding="utf-8"))["submissao"]["tag"] == "sub-001"
    assert not list(saida.glob("r.r49*")), "as execuções de conferência não podem ficar no disco"


def test_submeter_recusa_configuracao_diferente_da_execucao(repo_limpo, monkeypatch) -> None:
    """R49 repete a execução com a configuração de agora: semente (ou encoder) diferente é recusada."""
    _, saida = repo_limpo
    monkeypatch.setenv("VERIFICADOR_SEMENTE", "7")
    with pytest.raises(SystemExit, match="configuração atual"):
        cli.cmd_submeter(run_id="r", saida=saida)


def test_submeter_recusa_arvore_suja(repo_limpo) -> None:
    repo, saida = repo_limpo
    (repo / "a.txt").write_text("mudou", encoding="utf-8")
    with pytest.raises(SystemExit, match="suja"):
        cli.cmd_submeter(run_id="r", saida=saida, criar_tag=True)


def test_submeter_recusa_execucoes_diferentes(repo_limpo, monkeypatch) -> None:
    repo, saida = repo_limpo
    original = cli.cmd_rodar
    chamadas = []

    def instavel(**kw):
        caminho = original(**kw)
        chamadas.append(caminho)
        if len(chamadas) == 2:
            caminho.write_text(caminho.read_text(encoding="utf-8") + "extra\n", encoding="utf-8")
        return caminho

    monkeypatch.setattr(cli, "cmd_rodar", instavel)
    with pytest.raises(SystemExit, match="R49"):
        cli.cmd_submeter(run_id="r", saida=saida, criar_tag=True)
    assert subprocess.check_output(["git", "tag", "-l"], cwd=repo, text=True) == ""


# -- C7: R41 e R43 -------------------------------------------------------------------------


def test_r41_saida_nao_depende_do_nome_dos_arquivos(pasta_dados, tmp_path) -> None:
    originais = sorted((pasta_dados / "txt").glob("*.txt"))[:3]
    for pasta, prefixo in (("a", ""), ("b", "renomeado_")):
        (tmp_path / pasta).mkdir()
        for k, arquivo in enumerate(originais):
            shutil.copy(arquivo, tmp_path / pasta / f"{prefixo}{k:02d}.txt")
    conteudos = []
    for pasta in ("a", "b"):
        cli.cmd_rodar(entrada=tmp_path / pasta, run_id=pasta, saida=tmp_path / "runs", dados=pasta_dados)
        conteudos.append(
            [json.loads(p.read_text(encoding="utf-8"))["citacoes"] for p in sorted((tmp_path / "runs" / pasta / "jsons").glob("*.json"))]
        )
    assert conteudos[0] == conteudos[1]


def _literais_de_codigo(caminho: Path) -> list[str]:
    """Strings do código, sem docstrings (R43 fala de literal, não de comentário)."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    docstrings = {
        id(no.body[0].value)
        for no in ast.walk(arvore)
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and no.body and isinstance(no.body[0], ast.Expr) and isinstance(no.body[0].value, ast.Constant)
    }
    return [n.value for n in ast.walk(arvore) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]


def test_r43_codigo_nao_tem_literal_da_amostra(gabarito) -> None:
    ids = {l["id_canonico"] for l in gabarito if l["id_canonico"]}
    documentos = {l["documento_id"] for l in gabarito}
    trechos = {l["trecho"].replace("\\n", "\n") for l in gabarito if len(l["trecho"]) >= 10}
    achados = []
    for arquivo in sorted((RAIZ / "src").rglob("*.py")):
        for literal in _literais_de_codigo(arquivo):
            if (
                any(re.search(rf"\b{i}\b", literal) for i in ids)
                or any(d in literal for d in documentos)
                or literal in trechos
            ):
                achados.append(f"{arquivo.relative_to(RAIZ)}: {literal[:60]!r}")
    assert not achados, "\n".join(achados)
