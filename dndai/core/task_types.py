#!/usr/bin/env python3
"""Типы задач для маршрутизации к разным моделям/провайдерам"""

from enum import Enum


class TaskType(Enum):
    SIMPLE = "simple"          # compress, dice, formatting, простые извлечения
    NARRATIVE = "narrative"    # основной геймплей, диалоги, описания
    COMPLEX = "complex"        # планирование сюжета, сложные решения, jailbreak


class ModelTier(Enum):
    FAST = "fast"      # малые/быстрые модели (1b-20b) - для SIMPLE
    BALANCED = "balanced"  # средние (27b-70b) - для NARRATIVE
    SMART = "smart"    # большие (80b-120b+) - для COMPLEX


TASK_DEFAULT_TIER = {
    TaskType.SIMPLE: ModelTier.FAST,
    TaskType.NARRATIVE: ModelTier.BALANCED,
    TaskType.COMPLEX: ModelTier.SMART,
}

# Игровые категории из README («красный» / «жёлтый» / «синий») → tier.
TIER_FOR_COLOR = {
    "red": ModelTier.SMART,
    "yellow": ModelTier.BALANCED,
    "blue": ModelTier.FAST,
}

# Провайдеры для каждого tier
TIER_PROVIDER_PREFERENCE = {
    ModelTier.FAST: ["Groq", "Gemini", "OpenRouter", "Ollama-Server"],
    ModelTier.BALANCED: ["Groq", "Gemini", "OpenRouter", "Ollama-Server"],
    ModelTier.SMART: ["OpenRouter", "Groq", "Gemini", "Ollama-Server"],
}

# Модели по tier для каждого провайдера
PROVIDER_MODELS_BY_TIER = {
    "Groq": {
        ModelTier.FAST: [
            "groq/compound-mini",
            "allam-2-7b",
        ],
        ModelTier.BALANCED: [
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
            "groq/compound",
        ],
        ModelTier.SMART: [
            "openai/gpt-oss-120b",
        ],
    },
    "Gemini": {
        ModelTier.FAST: ["gemini-3.6-flash"],
        ModelTier.BALANCED: ["gemini-3.6-flash"],
        ModelTier.SMART: ["gemini-3.1-pro-preview"],
    },
    "OpenRouter": {
        ModelTier.FAST: [
            "liquid/lfm-2.5-2.6b:free",
            "nvidia/nemotron-3.5-lightning:free",
            "openrouter/free",
        ],
        ModelTier.BALANCED: [
            "google/gemma-4-26b-a4b-it:free",
            "google/gemma-4-31b-it:free",
            "stealth/ox-alpha",
        ],
        ModelTier.SMART: [
            "nvidia/nemotron-3-super-120b-a12b:free",
            "openai/gpt-oss-120b:free",
            "deepseek/deepseek-r1:free",
        ],
    },
    "Ollama-Server": {
        ModelTier.FAST: [
            "qwen2.5:3b",
        ],
        ModelTier.BALANCED: [
            "gemma3:12b",
            "hf.co/mradermacher/Qwen3-DND-Jan-v1-256k-ctx-Brainstorm40x-8B-i1-GGUF:Q4_K_M",
        ],
        ModelTier.SMART: [
            "qwen3:30b-a3b",
            "gemma3:12b",
            "qwen2.5-coder:14b",
        ],
    },
    "Ollama": {
        ModelTier.FAST: [],
        ModelTier.BALANCED: [],
        ModelTier.SMART: [],
    },
}