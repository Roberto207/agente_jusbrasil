"""R49: duas execuções do mesmo comando devem gerar `submission.csv` byte a byte idênticos."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


def hash_csv(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def csv_identicos(a: Path, b: Path) -> bool:
    return a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes()


def proximo_tag(tags: list[str]) -> str:
    """`sub-NNN` seguinte ao maior já existente (contar as tags erra se alguma foi apagada)."""
    numeros = [int(m.group(1)) for t in tags if (m := re.fullmatch(r"sub-(\d+)", t.strip()))]
    return f"sub-{(max(numeros) if numeros else 0) + 1:03d}"
