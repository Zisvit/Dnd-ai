#!/usr/bin/env python3
"""Тесты персистентности: schema_version, повторяемый откат,
атомарная хроника. Всё пишется во временную папку."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import dndai.game.session as session_mod
from dndai.game.session import (save_game_session, load_game_session,
                              backup_session, rollback_session,
                              export_chronicle)


def use_tmp_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(session_mod, "SESSION_DIR", tmp_path)


def test_schema_version_written(tmp_path, monkeypatch):
    use_tmp_dir(monkeypatch, tmp_path)
    save_game_session("s", [{"role": "user", "content": "hi"}])
    raw = json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))
    assert raw.get("schema_version") == session_mod.SCHEMA_VERSION


def test_rollback_repeatable(tmp_path, monkeypatch):
    """Откат можно выполнять несколько раз за вход — .bak не уничтожается."""
    use_tmp_dir(monkeypatch, tmp_path)
    # состояние на момент входа
    save_game_session("r", [{"role": "user", "content": "ВХОД"}],
                      summary="old")
    assert backup_session("r")
    # играем дальше: история растёт
    save_game_session("r", [{"role": "user", "content": "ВХОД"},
                            {"role": "assistant", "content": "дальше"},
                            {"role": "user", "content": "ещё"}],
                      summary="new")
    # первый откат
    assert rollback_session("r")
    h1, _, s1, *_ = load_game_session("r")
    assert len(h1) == 1 and s1 == "old"
    # ВТОРОЙ откат — раньше падал бы (bak перемещался)
    assert rollback_session("r")
    h2, _, s2, *_ = load_game_session("r")
    assert len(h2) == 1 and s2 == "old"


def test_corrupt_main_falls_back_to_bak(tmp_path, monkeypatch):
    use_tmp_dir(monkeypatch, tmp_path)
    save_game_session("c", [{"role": "user", "content": "хороший"}])
    backup_session("c")
    save_game_session("c", [{"role": "user", "content": "испорченный"}])
    (tmp_path / "c.json").write_text("{битый json", encoding="utf-8")
    h, *_ = load_game_session("c")
    # fallback на .bak (состояние на момент входа)
    assert h[0]["content"] == "хороший"


def test_chronicle_export(tmp_path, monkeypatch):
    use_tmp_dir(monkeypatch, tmp_path)
    path = export_chronicle(
        "ch",
        [{"role": "user", "content": "ход первый"},
         {"role": "assistant", "content": "ответ мастера"}],
        player_name="Артур", summary="сюжет")
    text = open(path, encoding="utf-8").read()
    assert "Хроника" in text and "ход первый" in text


def test_session_reads_with_utf8(tmp_path, monkeypatch):
    """Регресс №7: чтение сессии без явного encoding зависело от локали."""
    use_tmp_dir(monkeypatch, tmp_path)
    save_game_session("u", [{"role": "user", "content": "Привет, мир"}])

    from pathlib import Path

    seen = []
    original = Path.read_text

    def spy(self, *args, **kwargs):
        seen.append(kwargs.get("encoding"))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    h, *_ = load_game_session("u")
    assert h[0]["content"] == "Привет, мир"
    assert seen and all(enc == "utf-8" for enc in seen)


def test_invalid_utf8_falls_back_to_bak(tmp_path, monkeypatch):
    """Регресс №7: битая кодировка не должна ронять загрузку сессии."""
    use_tmp_dir(monkeypatch, tmp_path)
    save_game_session("x", [{"role": "user", "content": "старое"}])
    assert backup_session("x")
    save_game_session("x", [{"role": "user", "content": "новое"}])
    (tmp_path / "x.json").write_bytes(b"\xff\xfe\x00\x01 definitely not utf-8")

    h, *_ = load_game_session("x")
    assert h[0]["content"] == "старое"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
