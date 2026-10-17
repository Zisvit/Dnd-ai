#!/usr/bin/env python3
"""Пути приложения: каталог данных, сессии, промпты.

Все пользовательские данные живут в одном доме (по умолчанию ~/.dnd_ai,
переопределяется переменной окружения DND_AI_HOME):

    ~/.dnd_ai/
    ├── .env              — ключи API (читает settings.py)
    ├── blacklist.json    — заблокированные пары провайдер+модель
    ├── input_history     — история ввода (стрелки ↑↓)
    ├── sessions/         — сохранения игр
    └── prompts/          — необязательный оверрайд промптов

Промпты поставляются внутри пакета (dndai/prompts); приоритет чтения:
$DND_PROMPTS_DIR → ~/.dnd_ai/prompts → пакет. Каталог для правок
создаёт ``dndd --copy-prompts``.

Модуль — «лист»: не импортирует другие модули пакета и ничего не пишет
на импорте. Создание каталогов — ensure_home() из main().
"""

import os
import shutil
import sys
from pathlib import Path

__all__ = [
    "DATA_DIR",
    "SESSION_DIR",
    "BLACKLIST_PATH",
    "app_home",
    "ensure_home",
    "get_prompts_dir",
    "package_prompts_dir",
    "migrate_legacy_data",
]

_HOME_NAME = ".dnd_ai"
_MIGRATION_MARKER = ".migrations.json"


def _warn(msg):
    """Предупреждение в stderr (не зависит от i18n-слоя)."""
    print(f"⚠️  {msg}", file=sys.stderr)


def app_home():
    """Дом данных: $DND_AI_HOME или ~/.dnd_ai.

    Если $DND_AI_HOME указывает на существующий файл — предупреждаем и
    откатываемся на ~/.dnd_ai, не роняя запуск.
    """
    env = os.getenv("DND_AI_HOME")
    if env:
        p = Path(env).expanduser()
        if p.exists() and not p.is_dir():
            _warn(f"DND_AI_HOME указывает на файл, а не каталог: {p}")
            _warn(f"Использую ~/{_HOME_NAME}")
            return Path.home() / _HOME_NAME
        return p
    return Path.home() / _HOME_NAME


def package_prompts_dir():
    """Каталог prompts внутри установленного пакета."""
    try:
        from importlib import resources

        return Path(str(resources.files("dndai"))) / "prompts"
    except Exception:
        return Path(__file__).resolve().parents[2] / "prompts"


def get_prompts_dir():
    """Каталог, из которого читаются промпты (приоритет — в docstring)."""
    env = os.getenv("DND_PROMPTS_DIR")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p
    user = app_home() / "prompts"
    if user.is_dir():
        return user
    return package_prompts_dir()


# Статические пути; каталоги создаёт ensure_home(), не импорт.
DATA_DIR = app_home()
SESSION_DIR = DATA_DIR / "sessions"
BLACKLIST_PATH = DATA_DIR / "blacklist.json"


def ensure_home():
    """Создаёт каталог данных и сессий. False — если писать некуда."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        _warn(f"Нет доступа к каталогу данных {DATA_DIR}: {e}")
        _warn("Задайте другой каталог переменной DND_AI_HOME.")
        return False
    if not os.access(DATA_DIR, os.W_OK):
        _warn(f"Каталог данных недоступен для записи: {DATA_DIR}")
        _warn("Задайте другой каталог переменной DND_AI_HOME.")
        return False
    return True


def migrate_legacy_data():
    """Одноразовый перенос данных из старой раскладки репозитория.

    Старая раскладка: ``./data`` и ``./dnd_sessions`` рядом с кодом.
    Копируются только отсутствующие файлы (источники не трогаем).
    Маркер ``.migrations.json`` пишется в конце: прерванный перенос
    безопасно повторяется при следующем запуске.

    Возвращает число скопированных файлов.
    """
    marker = DATA_DIR / _MIGRATION_MARKER
    if marker.exists():
        return 0

    root = Path.cwd()
    legacy = [
        (root / "dnd_sessions", SESSION_DIR, None),
        (root / "data", DATA_DIR, ("blacklist.json", "input_history")),
    ]
    if not any(src.is_dir() for src, _, _ in legacy):
        return 0  # переносить нечего — маркер не ставим

    copied = 0
    for src, dst, names in legacy:
        if not src.is_dir():
            continue
        try:
            src_r, dst_r = src.resolve(), dst.resolve()
        except OSError:
            continue
        if src_r == dst_r or src_r in dst_r.parents or dst_r in src_r.parents:
            continue  # тот же каталог или вложенность — не переносим
        try:
            dst.mkdir(parents=True, exist_ok=True)
            files = [src / n for n in names] if names else sorted(src.iterdir())
        except OSError as e:
            _warn(f"Не удалось подготовить перенос из {src}: {e}")
            continue
        for f in files:
            try:
                if not f.is_file() or f.name.endswith(".tmp"):
                    continue
            except OSError:
                continue
            target = dst / f.name
            if target.exists():
                continue
            try:
                shutil.copy2(f, target)
                copied += 1
            except OSError as e:
                _warn(f"Не удалось скопировать {f} → {target}: {e}")

    tmp = marker.with_name(marker.name + ".tmp")
    try:
        tmp.write_text('{"done": ["repo_data_v1"]}\n', encoding="utf-8")
        os.replace(tmp, marker)
    except OSError:
        pass
    return copied
