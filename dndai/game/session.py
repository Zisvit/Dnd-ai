#!/usr/bin/env python3
"""Сохранение/загрузка игровых сессий.

Формат файла ~/.dnd_ai/sessions/<имя>.json:
{schema_version, history, memory, summary, state, world, rpg}

Запись атомарная (atomic_write), при битом JSON основной файл
автоматически заменяется бэкапом .bak.
"""

import json
import re
import shutil

from ..core.config import SESSION_DIR
from ..core.atomic import atomic_write
from ..core.text import clean, highlight
from ..core.colors import YELLOW, RESET
from ..core.logger import warning as _log_warning

SCHEMA_VERSION = 2


def load_session(name):
    """Читает сессию; битый JSON -> fallback на .bak, затем пустая сессия."""
    default = {"history": [], "memory": ""}
    f = SESSION_DIR / f"{name}.json"
    if not f.exists():
        return default
    try:
        data = json.loads(f.read_text())
        if isinstance(data, dict):
            return data
        return default
    except (json.JSONDecodeError, OSError):
        # Основной файл повреждён (обрыв записи, ручная правка) — пробуем бэкап
        bak = SESSION_DIR / f"{name}.json.bak"
        if bak.exists():
            try:
                data = json.loads(bak.read_text())
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return default


def save_session(name, data):
    """Атомарно пишет сессию на диск."""
    payload = dict(data)
    payload.setdefault("schema_version", SCHEMA_VERSION)
    atomic_write(
        SESSION_DIR / f"{name}.json", json.dumps(payload, ensure_ascii=False, indent=2)
    )


def load_game_session(session_name):
    data = load_session(session_name)
    history = data.get("history", [])
    memory = data.get("memory", "")
    summary = data.get("summary", "")
    state = data.get("state", {})
    world = data.get("world", {})
    rpg = data.get("rpg", {})
    # Минимальная валидация схемы — чтобы битый/частичный файл не крашнул
    # конструкторы состояний с TypeError/AttributeError.
    if not isinstance(state, (dict, list)):
        state = {}
    if not isinstance(world, dict):
        world = {}
    if not isinstance(rpg, dict):
        rpg = {}
    if not isinstance(history, list):
        history = []
    for m in history:
        if isinstance(m, dict) and "content" in m:
            m["content"] = clean(m["content"])
        elif isinstance(m, dict):
            m["role"] = m.get("role", "user")
            m["content"] = clean(str(m.get("content", "")))
    return history, memory, summary, state, world, rpg


def _backup_path(session_name):
    return SESSION_DIR / f"{session_name}.json.bak"


def save_game_session(
    session_name, history, memory="", summary="", state=None, world=None, rpg=None
):
    save_session(
        session_name,
        {
            "history": history,
            "memory": memory,
            "summary": summary,
            "state": state or {},
            "world": world or {},
            "rpg": rpg or {},
        },
    )


def archive_log(session_name, role, content):
    """Дублирует каждое сообщение в полный архивный лог (jsonl).

    История в сессии обрезается компрессией, но архив сохраняет ВСЕ
    сообщения целиком — страховка на случай, если summary исказит сюжет.
    """
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        with (SESSION_DIR / f"{session_name}.archive.jsonl").open(
            "a", encoding="utf-8"
        ) as f:
            f.write(line + "\n")
    except Exception as e:
        _log_warning(f"archive_log {session_name}: {e}")


def backup_session(session_name):
    """Снимает снимок сессии ДО начала игры в .bak.

    При каждом входе в сессию обновляем .bak актуальным состоянием на момент
    входа (это состояние, к которому вернёт !откат). Предыдущий .bak сдвигаем
    в .bak2, чтобы сохранять одно поколение назад и не терять его.
    """
    sess_file = SESSION_DIR / f"{session_name}.json"
    bak = _backup_path(session_name)
    if not sess_file.exists():
        return False
    try:
        bak2 = SESSION_DIR / f"{session_name}.json.bak2"
        if bak.exists():
            shutil.copy2(bak, bak2)  # сохраняем предыдущее поколение
        shutil.copy2(sess_file, bak)
        return True
    except Exception:
        return False


def rollback_session(session_name):
    """Откат к бэкапу на момент входа (.bak). Возвращает True/False.

    Бэкап КОПИРУЕТСЯ, а не перемещается — откат можно выполнять
    многократно за вход, каждый раз возвращаясь к одной и той же точке.
    """
    bak = _backup_path(session_name)
    if not bak.exists():
        return False
    sess_file = SESSION_DIR / f"{session_name}.json"
    try:
        # Текущее состояние сохраняем как .bak2 на всякий случай
        if sess_file.exists():
            shutil.copy2(sess_file, SESSION_DIR / f"{session_name}.json.bak2")
        shutil.copy2(bak, sess_file)
        return True
    except Exception:
        return False


def get_player_name_from_history(history, default_name="player"):
    from ..core.i18n import t

    marker = t("main.name_change_marker")
    pattern = t("main.name_change_pattern")
    for m in reversed(history):
        content = m.get("content", "")
        if marker in content:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
    return default_name


def compress_if_needed(history, session_name, character=None, old_summary=""):
    """Сжимает историю и обновляет вечную память сюжета (summary).

    Оставляем последние 12 сообщений, генерируем summary из старых.
    Если генерация summary не удалась (пусто), сохраняем старую память,
    чтобы не стереть сюжет вхолостую.
    Возвращает (history, summary).
    """
    if len(history) <= 30:
        return history, old_summary
    from ..core.i18n import t

    print(f"{YELLOW}⏳ {t('session.compressing')}{RESET}")
    from ..api.openrouter import compress

    new_summary = compress(history)
    # Накапливаем вечную память: старый сюжет + новая порция,
    # а не заменяем целиком одной строкой.
    if new_summary:
        summary = (
            f"{old_summary}\n{new_summary}".strip() if old_summary else new_summary
        )
    else:
        summary = old_summary
    # Оставляем последние 12 сообщений, стираем старые
    keep = history[-12:]
    history = keep
    return history, summary


def show_history(history, player_name):
    from ..core.colors import GREEN, BLUE, RESET

    for m in history:
        role = (
            f"{GREEN}{player_name}{RESET}"
            if m["role"] == "user"
            else f"{BLUE}DM{RESET}"
        )
        print(f"{role}: {highlight(m['content'])}")


def export_chronicle(session_name, history, player_name="player", summary=""):
    """Экспортирует хронику партии в Markdown-файл (запись атомарная)."""
    import datetime

    path = SESSION_DIR / f"{session_name}.chronicle.md"
    lines = [
        f"# Хроника сессии «{session_name}»",
        "",
        f"*Экспортировано: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
    ]
    if summary:
        lines += ["## Память сюжета", "", summary, ""]
    lines += ["## История событий", ""]
    for m in history:
        role = player_name if m.get("role") == "user" else "Мастер"
        content = clean(m.get("content", "")).replace("\n", "\n> ")
        prefix = "**" + role + ":** "
        lines.append("> " + (prefix if not content.startswith(">") else "") + content)
        lines.append("")
    atomic_write(path, "\n".join(lines))
    return str(path)
