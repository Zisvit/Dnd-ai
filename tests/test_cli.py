#!/usr/bin/env python3
"""CLI: версия, страж CHANGELOG, --copy-prompts, сообщение о ключах."""

import json
import re
from pathlib import Path

import pytest

import dndai
from dndai.core.i18n import t
from dndai.main import _valid_session_name, check_api_keys, main

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", dndai.__version__)


def test_changelog_has_current_version():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{dndai.__version__}]" in text


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert dndai.__version__ in capsys.readouterr().out


@pytest.mark.parametrize(
    "name,ok",
    [
        ("default", True),
        ("Моя кампания 2", True),
        ("my-game.v2", True),
        ("../etc", False),
        ("a/b", False),
        ("a" * 65, False),
        ("  ", False),
        ("", False),
    ],
)
def test_session_name_validation(name, ok):
    assert _valid_session_name(name) is ok


def test_copy_prompts_seeds_and_keeps_edits(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_AI_HOME", str(tmp_path / "home"))
    assert main(["--copy-prompts"]) == 0
    dst = tmp_path / "home" / "prompts"
    names = sorted(p.name for p in dst.glob("*.txt"))
    assert "system_prompt.txt" in names
    assert len(names) >= 7
    edited = dst / "system_prompt.txt"
    edited.write_text("моя правка", encoding="utf-8")
    assert main(["--copy-prompts"]) == 0
    assert edited.read_text(encoding="utf-8") == "моя правка"


def test_no_keys_message_points_to_env(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DND_AI_HOME", str(tmp_path))
    monkeypatch.setattr("dndai.main.API_KEYS", [])
    monkeypatch.delenv("OLLAMA_SERVER_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert check_api_keys() is False
    out = capsys.readouterr().out
    assert str(tmp_path / ".env") in out
    assert "❌ ❌" not in out


def test_invalid_session_name_exit_code(capsys, monkeypatch):
    monkeypatch.setattr("dndai.main.API_KEYS", ["dummy"])
    assert main(["../bad"]) == 2
    assert "Недопустимое имя сессии" in capsys.readouterr().out


def test_list_sessions_empty(capsys, monkeypatch, tmp_path):
    monkeypatch.setattr("dndai.main.SESSION_DIR", tmp_path)
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert t("main.list_empty") in out


def test_list_sessions_shows_rows_and_broken(capsys, monkeypatch, tmp_path):
    (tmp_path / "alpha.json").write_text(
        json.dumps({"history": [{"role": "user", "content": "hi"}]}),
        encoding="utf-8",
    )
    (tmp_path / "broken.json").write_text("{oops", encoding="utf-8")
    # >1 KiB — проверить человекочитаемый размер
    (tmp_path / "big.json").write_text(
        json.dumps({"history": [], "pad": "x" * 2048}), encoding="utf-8"
    )
    monkeypatch.setattr("dndai.main.SESSION_DIR", tmp_path)
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert t("main.list_title", n=3) in out
    assert "alpha" in out and "broken" in out and "big" in out
    assert "?" in out  # битый файл: число сообщений неизвестно
    assert "KiB" in out


def test_list_sessions_truncates_to_50(capsys, monkeypatch, tmp_path):
    for i in range(55):
        (tmp_path / f"s{i:02d}.json").write_text('{"history": []}', encoding="utf-8")
    monkeypatch.setattr("dndai.main.SESSION_DIR", tmp_path)
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert t("main.list_more", n=5) in out
    assert "s54" in out  # свежие сверху, показаны s54..s05
    assert "s04" not in out


def test_prompts_integrity_warning(capsys, monkeypatch):
    monkeypatch.setattr(
        "dndai.main.verify_prompts", lambda: ["sha256 не совпадает: a.txt"]
    )
    monkeypatch.setattr("dndai.main.API_KEYS", [])
    monkeypatch.delenv("OLLAMA_SERVER_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert main([]) == 2
    out = capsys.readouterr().out
    assert t("main.prompts_corrupt", n=1) in out
