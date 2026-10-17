#!/usr/bin/env python3
"""Провал первого ответа мастера не теряет созданного персонажа (регресс №3)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import dndai.game.session as session_mod
import dndai.main as main_mod
from dndai.game.character import CharacterState
from dndai.game.party import Party
from dndai.game.world import WorldState


def use_tmp_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(session_mod, "SESSION_DIR", tmp_path)


def silence_ui(monkeypatch):
    monkeypatch.setattr(main_mod, "show_startup_hint", lambda: None)
    monkeypatch.setattr(main_mod, "show_dm_status", lambda: None)


def make_party(name="Тест"):
    party = Party()
    party.add(CharacterState({"name": name, "class": "Воин"}))
    return party


def fail_dm(*a, **k):
    return None, None, "нет доступных моделей", False


def test_failed_first_call_saves_party(tmp_path, monkeypatch):
    """Регресс №3: провал первого хода не должен терять персонажа."""
    use_tmp_dir(monkeypatch, tmp_path)
    silence_ui(monkeypatch)
    monkeypatch.setattr(main_mod, "ask_dm", fail_dm)

    history, err = main_mod.start_new_game("s1", make_party(), WorldState())

    assert history is None and err == ""
    raw = json.loads((tmp_path / "s1.json").read_text(encoding="utf-8"))
    party = Party(raw["state"])
    assert [c.name for c in party.chars] == ["Тест"]


def test_failed_first_call_does_not_overwrite_existing(tmp_path, monkeypatch):
    """Существующую сессию повторный провал не трогает (не затираем прогресс)."""
    use_tmp_dir(monkeypatch, tmp_path)
    silence_ui(monkeypatch)
    session_mod.save_game_session("s1", [{"role": "user", "content": "старый ход"}])
    monkeypatch.setattr(main_mod, "ask_dm", fail_dm)

    main_mod.start_new_game("s1", make_party("Другой"), WorldState())

    raw = json.loads((tmp_path / "s1.json").read_text(encoding="utf-8"))
    assert raw["history"][0]["content"] == "старый ход"


def test_successful_first_call_saves_history(tmp_path, monkeypatch):
    """Успешный путь не сломан: история и партия пишутся как раньше."""
    use_tmp_dir(monkeypatch, tmp_path)
    silence_ui(monkeypatch)
    monkeypatch.setattr(
        main_mod,
        "ask_dm",
        lambda *a, **k: ("Мастер приветствует вас.", "TestProv:m1", None, False),
    )

    history, err = main_mod.start_new_game("s2", make_party(), WorldState())

    assert err == "" and [m["role"] for m in history] == ["user", "assistant"]
    raw = json.loads((tmp_path / "s2.json").read_text(encoding="utf-8"))
    assert raw["history"][-1]["content"] == "Мастер приветствует вас."
    assert raw["state"]["chars"][0]["name"] == "Тест"
