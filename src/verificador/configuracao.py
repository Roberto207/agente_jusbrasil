"""Configuração versionada do verificador.

Lida de `verificador.toml` (raiz do repositório ou diretório de trabalho),
com overlay por variáveis de ambiente `VERIFICADOR_*`. O hash entra no manifesto.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


def _raiz_repositorio() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Configuracao:
    usar_encoder: bool = False
    usar_llm: bool = False
    extrair_referencia_vaga: bool = False
    semente: int = 0
    dtype: str = "float16"
    encoder_link: str | None = None
    encoder_revisao: str | None = None
    llm_link: str | None = None
    llm_revisao: str | None = None

    def hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def com_flags(
        self,
        *,
        usar_encoder: bool | None = None,
        usar_llm: bool | None = None,
    ) -> Configuracao:
        atual = self
        if usar_encoder is not None:
            atual = replace(atual, usar_encoder=usar_encoder)
        if usar_llm is not None:
            atual = replace(atual, usar_llm=usar_llm)
        return atual


_BOOLS = {"1", "true", "yes", "sim", "on"}


def _como_bool(valor: str) -> bool:
    return valor.strip().lower() in _BOOLS


def _caminho_toml() -> Path | None:
    env = os.environ.get("VERIFICADOR_CONFIG")
    if env:
        caminho = Path(env)
        return caminho if caminho.is_file() else None
    for candidato in (Path.cwd() / "verificador.toml", _raiz_repositorio() / "verificador.toml"):
        if candidato.is_file():
            return candidato
    return None


def carregar() -> Configuracao:
    dados: dict = {}
    toml_path = _caminho_toml()
    if toml_path is not None:
        with toml_path.open("rb") as fh:
            dados = tomllib.load(fh) or {}

    cfg = Configuracao(
        usar_encoder=bool(dados.get("usar_encoder", False)),
        usar_llm=bool(dados.get("usar_llm", False)),
        extrair_referencia_vaga=bool(dados.get("extrair_referencia_vaga", False)),
        semente=int(dados.get("semente", 0)),
        dtype=str(dados.get("dtype", "float16")),
        encoder_link=dados.get("encoder_link"),
        encoder_revisao=dados.get("encoder_revisao"),
        llm_link=dados.get("llm_link"),
        llm_revisao=dados.get("llm_revisao"),
    )

    if "VERIFICADOR_USAR_ENCODER" in os.environ:
        cfg = replace(cfg, usar_encoder=_como_bool(os.environ["VERIFICADOR_USAR_ENCODER"]))
    if "VERIFICADOR_USAR_LLM" in os.environ:
        cfg = replace(cfg, usar_llm=_como_bool(os.environ["VERIFICADOR_USAR_LLM"]))
    if "VERIFICADOR_EXTRAIR_REFERENCIA_VAGA" in os.environ:
        cfg = replace(
            cfg,
            extrair_referencia_vaga=_como_bool(os.environ["VERIFICADOR_EXTRAIR_REFERENCIA_VAGA"]),
        )
    if "VERIFICADOR_SEMENTE" in os.environ:
        cfg = replace(cfg, semente=int(os.environ["VERIFICADOR_SEMENTE"]))
    if "VERIFICADOR_DTYPE" in os.environ:
        cfg = replace(cfg, dtype=os.environ["VERIFICADOR_DTYPE"])
    return cfg
