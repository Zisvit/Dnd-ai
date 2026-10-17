#!/usr/bin/env python3
"""Настройки из переменных окружения

Загружает API-ключи нескольких провайдеров из .env и строит
список PROVIDERS для мульти-провайдерного перебора при лимитах.
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from .paths import app_home

# Ключи читаются только из явных путей: no-arg load_dotenv() ищет .env
# от каталога вызывающего модуля вверх и может подхватить чужой файл.
# Приоритет (override=False — первое найденное значение выигрывает):
#   1) переменные окружения процесса — не трогаем;
#   2) .env в текущем каталоге (запуск из репозитория);
#   3) ~/.dnd_ai/.env — пользовательский конфиг.
load_dotenv(Path.cwd() / ".env", override=False)
load_dotenv(app_home() / ".env", override=False)

# Адрес удалённого/локального Ollama-сервера. НИКОГДА не хардкодим IP:
# значение берётся из .env (игнорируется git'ом). Дефолт — локальный.
_OLLAMA_SERVER_URL = os.getenv("OLLAMA_SERVER_URL", "http://localhost:11434").rstrip(
    "/"
)

# Базовые URL и модели по умолчанию для каждого провайдера.
# Все провайдеры используют OpenAI-совместимый формат /chat/completions.
PROVIDER_DEFS = [
    {
        "name": "Groq",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "models": [
            "openai/gpt-oss-120b",  # 120b — лучшая качество
            "openai/gpt-oss-20b",  # 20b — баланс скорость/качество
            "qwen/qwen3.6-27b",  # 27b — сильная китайская
            "groq/compound",  # составная умная
            "groq/compound-mini",  # очень быстрая
            "allam-2-7b",  # 7b — быстрая
        ],
    },
    {
        "name": "Gemini",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "models": [
            "gemini-3.6-flash",
        ],
    },
    {
        "name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "models": [
            "stealth/ox-alpha",
            "liquid/lfm-2.5-2.6b:free",
            "nvidia/nemotron-3.5-lightning:free",
            "google/gemma-4-26b-a4b-it:free",
            "google/gemma-4-31b-it:free",
            "z-ai/glm-5.2:free",
            "openrouter/free",
        ],
    },
    {
        "name": "Ollama-Server",
        "env_key": None,
        # Адрес сервера задаётся ТОЛЬКО через .env (OLLAMA_SERVER_URL),
        # чтобы реальный IP никогда не попадал в репозиторий.
        "base_url": f"{_OLLAMA_SERVER_URL}/v1/chat/completions",
        # Модели загружаются динамически из Ollama API
        "models": [],
        "dynamic_models": True,
        "ollama_api_url": _OLLAMA_SERVER_URL,
    },
]

# Локальный провайдер Ollama (опционально)
if os.getenv("OLLAMA_BASE_URL") and os.getenv("OLLAMA_MODEL"):
    PROVIDER_DEFS.append(
        {
            "name": "Ollama",
            "env_key": None,
            "base_url": os.getenv("OLLAMA_BASE_URL"),
            "models": [os.getenv("OLLAMA_MODEL")],
        }
    )


def fetch_ollama_models(ollama_api_url: str) -> list:
    """Получает список доступных моделей из Ollama API."""
    try:
        resp = requests.get(f"{ollama_api_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def get_ollama_models() -> list:
    """Получает список моделей от Ollama-Server с фоллбэком на хардкод."""
    for p in PROVIDER_DEFS:
        if p.get("dynamic_models") and p.get("ollama_api_url"):
            models = fetch_ollama_models(p["ollama_api_url"])
            if models:
                return models
    # Фоллбэк на хардкод
    for p in PROVIDER_DEFS:
        if p["name"] == "Ollama-Server":
            return p.get("models", [])
    return []


def build_providers():
    """Строит список активных провайдеров из переменных окружения.

    Без сетевых вызовов: модели Ollama-Server подгружаются лениво
    в момент запроса (_get_models_for_tier -> get_ollama_models),
    чтобы импорт конфига никогда не подвисал на сети.
    """
    providers = []
    for p in PROVIDER_DEFS:
        key = os.getenv(p["env_key"]) if p["env_key"] else None
        if key or p["name"] in ("Ollama", "Ollama-Server"):
            providers.append(
                {
                    "name": p["name"],
                    "base_url": p["base_url"],
                    "api_key": key or "",
                    "models": list(p.get("models", [])),
                    "stream": p.get("stream", True),
                    "disabled_until": 0.0,
                }
            )
    return providers


# ВАЖНО: без сетевых вызовов при импорте модуля.
PROVIDERS = build_providers()

# Для обратной совместимости
API_KEYS = [p["api_key"] for p in PROVIDERS if p["api_key"]]
URL = (
    PROVIDERS[0]["base_url"]
    if PROVIDERS
    else "https://openrouter.ai/api/v1/chat/completions"
)


# Параметры вывода (некорректное значение в .env не должно ронять запуск)
try:
    OUTPUT_DELAY = float(os.getenv("OUTPUT_DELAY", "0.008"))
except ValueError:
    OUTPUT_DELAY = 0.008
DEFAULT_PLAYER_NAME = os.getenv("DEFAULT_PLAYER_NAME", "player")
# Режим стриминга (живой вывод по токенам). По умолчанию ВЫКЛЮЧЕН —
# так сохраняется подсветка разметки {{}}/<<>>/[[ ]].
# Включить: STREAM_MODE=1 в .env.
STREAM_MODE = os.getenv("STREAM_MODE", "0").strip() == "1"

# Режим эмодзи: EMOJI=1 (по умолчанию) — с эмодзи, EMOJI=0 — только текст.
EMOJI = os.getenv("EMOJI", "1") != "0"

# Режим цветов: COLOR=1 (по умолчанию) — с ANSI цветами, COLOR=0 — без цветов.
COLOR = os.getenv("COLOR", "1") != "0"
