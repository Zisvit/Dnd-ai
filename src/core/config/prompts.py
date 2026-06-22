#!/usr/bin/env python3
"""Загрузка и парсинг промптов"""

from .paths import PROMPTS_DIR

def load_prompt(filename):
    path = PROMPTS_DIR / filename
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def load_refuse_patterns():
    patterns = []
    path = PROMPTS_DIR / "refuse_patterns.txt"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            patterns = [line.strip() for line in f if line.strip()]
    return patterns or [
        r"i'm sorry", r"i am sorry", r"i can't", r"i cannot",
        r"я не могу", r"не могу", r"я не готов", r"не готов",
        r"против политики", r"не допускается", r"sorry", r"не предназначен"
    ]

def load_detail_levels():
    levels = {}
    path = PROMPTS_DIR / "detail_levels.txt"
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line:
                    key, val = line.strip().split('|', 1)
                    levels[int(key)] = val
    return levels or {
        0: "Отвечай кратко (1-3 предложения).",
        1: "Добавь пару деталей окружения, звуки, запахи.",
        2: "Описывай очень подробно: внешность, текстуры, освещение, эмоции. Не менее 4-5 предложений.",
        3: "МАКСИМАЛЬНАЯ детализация. Разверни сцену на 6-8 предложений, добавь мысли персонажей, скрытые смыслы."
    }

REFUSE_PATTERNS = load_refuse_patterns()
DETAIL_LEVELS = load_detail_levels()
