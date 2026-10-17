#!/usr/bin/env python3
"""Тесты dndai/core/atomic.py — атомарная запись файлов."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from dndai.core.atomic import atomic_write


def test_write_and_read(tmp_path):
    f = tmp_path / "out.txt"
    atomic_write(f, "привет мир")
    assert f.read_text(encoding="utf-8") == "привет мир"
    # временные файлы не остаются
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_overwrite(tmp_path):
    f = tmp_path / "out.txt"
    atomic_write(f, "первая версия")
    atomic_write(f, "вторая версия")
    assert f.read_text(encoding="utf-8") == "вторая версия"


def test_creates_parent_dirs(tmp_path):
    f = tmp_path / "deep" / "nested" / "out.txt"
    atomic_write(f, "data")
    assert f.read_text(encoding="utf-8") == "data"


def test_failure_keeps_original(tmp_path, monkeypatch):
    """Если replace упал — оригинал цел, временный файл убран."""
    import dndai.core.atomic as atomic_mod

    f = tmp_path / "keep.txt"
    atomic_write(f, "оригинал")

    def boom(a, b):
        raise OSError("disk on fire")

    monkeypatch.setattr(atomic_mod.os, "replace", boom)
    with pytest.raises(OSError):
        atomic_write(f, "новые данные")
    assert f.read_text(encoding="utf-8") == "оригинал"
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
