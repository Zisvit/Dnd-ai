#!/usr/bin/env python3
"""Загрузка и парсинг промптов.

Каталог задаёт paths.get_prompts_dir(): $DND_PROMPTS_DIR →
~/.dnd_ai/prompts → пакетный dndai/prompts.
"""

from .paths import get_prompts_dir


def load_prompt(filename):
    """Возвращает текст промпта. Пустая строка — файл не найден."""
    path = get_prompts_dir() / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def load_refuse_patterns():
    patterns = []
    path = get_prompts_dir() / "refuse_patterns.txt"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            patterns = [line.strip() for line in f if line.strip()]
    return patterns or [
        r"i'm sorry",
        r"i am sorry",
        r"i can't",
        r"i cannot",
        r"я не могу",
        r"не могу",
        r"я не готов",
        r"не готов",
        r"против политики",
        r"не допускается",
        r"sorry",
        r"не предназначен",
    ]


def load_detail_levels():
    levels = {}
    path = get_prompts_dir() / "detail_levels.txt"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    key, val = line.strip().split("|", 1)
                    levels[int(key)] = val
    return levels or {
        0: "Отвечай кратко (1-3 предложения).",
        1: "Добавь пару деталей окружения, звуки, запахи.",
        2: "Описывай очень подробно: внешность, текстуры, освещение, эмоции. Не менее 4-5 предложений.",
        3: "МАКСИМАЛЬНАЯ детализация. Разверни сцену на 6-8 предложений, добавь мысли персонажей, скрытые смыслы.",
    }


REFUSE_PATTERNS = load_refuse_patterns()
DETAIL_LEVELS = load_detail_levels()
