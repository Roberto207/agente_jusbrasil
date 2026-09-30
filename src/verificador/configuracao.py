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
    extrair_referencia_vaga: bool = False
    semente: int = 0
    encoder_link: str | None = None
    encoder_revisao: str | None = None

    def hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def com_flags(self, *, usar_encoder: bool | None = None) -> Configuracao:
        return self if usar_encoder is None else replace(self, usar_encoder=usar_encoder)


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
        extrair_referencia_vaga=bool(dados.get("extrair_referencia_vaga", False)),
        semente=int(dados.get("semente", 0)),
        encoder_link=dados.get("encoder_link"),
        encoder_revisao=dados.get("encoder_revisao"),
    )

    if "VERIFICADOR_USAR_ENCODER" in os.environ:
        cfg = replace(cfg, usar_encoder=_como_bool(os.environ["VERIFICADOR_USAR_ENCODER"]))
    if "VERIFICADOR_EXTRAIR_REFERENCIA_VAGA" in os.environ:
        cfg = replace(
            cfg,
            extrair_referencia_vaga=_como_bool(os.environ["VERIFICADOR_EXTRAIR_REFERENCIA_VAGA"]),
        )
    if "VERIFICADOR_ENCODER_LINK" in os.environ:
        cfg = replace(cfg, encoder_link=os.environ["VERIFICADOR_ENCODER_LINK"])
    if "VERIFICADOR_ENCODER_REVISAO" in os.environ:
        cfg = replace(cfg, encoder_revisao=os.environ["VERIFICADOR_ENCODER_REVISAO"])
    if "VERIFICADOR_SEMENTE" in os.environ:
        cfg = replace(cfg, semente=int(os.environ["VERIFICADOR_SEMENTE"]))
    return cfg
