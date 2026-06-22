#!/usr/bin/env python3
"""Пути к файлам и директориям"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
DATA_DIR = BASE_DIR / "data"
SESSION_DIR = Path.home() / "dnd_sessions"

# Создаём необходимые папки
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# Файлы данных
MODELS_CACHE = DATA_DIR / "models_cache.json"
FAST_CACHE = DATA_DIR / "fast_models.json"
BLACKLIST_PATH = DATA_DIR / "blacklist.json"
MODELS_RANKING_FILE = DATA_DIR / "models_ranking.json"
STATIC_MODELS_FILE = DATA_DIR / "static_models.txt"
