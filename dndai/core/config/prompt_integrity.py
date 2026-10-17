#!/usr/bin/env python3
"""Целостность промптов: манифест sha256 и его проверка.

Манифест ``dndai/prompts/checksums.json`` содержит sha256 всех ``*.txt``
каталога промптов пакета. Рантайм-проверка warn-only (сломанная установка
не должна ронять игру), в CI содержимое собранного wheel сверяется с
манифестом. Перегенерация после правки промптов — write_manifest().
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from .paths import package_prompts_dir

MANIFEST_NAME = "checksums.json"
ALGORITHM = "sha256"


def manifest_path(directory: Optional[Path] = None) -> Path:
    return (directory or package_prompts_dir()) / MANIFEST_NAME


def compute_checksums(directory: Optional[Path] = None) -> dict[str, str]:
    """sha256 всех *.txt каталога промптов: {имя файла: hex-дайджест}."""
    directory = directory or package_prompts_dir()
    return {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(directory.glob("*.txt"))
    }


def write_manifest(directory: Optional[Path] = None) -> int:
    """Перегенерирует манифест из фактических *.txt; возвращает их число."""
    checksums = compute_checksums(directory)
    payload = {"algorithm": ALGORITHM, "files": checksums}
    manifest_path(directory).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return len(checksums)


def verify_prompts(directory: Optional[Path] = None) -> list[str]:
    """Расхождения манифеста и фактических промптов (пусто — всё сходится)."""
    directory = directory or package_prompts_dir()
    try:
        manifest = json.loads(manifest_path(directory).read_text(encoding="utf-8"))
        expected = manifest["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return [f"манифест недоступен: {MANIFEST_NAME}"]
    actual = compute_checksums(directory)
    problems = []
    for name in sorted(set(expected) | set(actual)):
        if name not in actual:
            problems.append(f"нет файла: {name}")
        elif name not in expected:
            problems.append(f"нет в манифесте: {name}")
        elif actual[name] != expected[name]:
            problems.append(f"sha256 не совпадает: {name}")
    return problems
