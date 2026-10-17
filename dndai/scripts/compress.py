#!/usr/bin/env python3
"""Локальная суммаризация истории — быстрая и бесплатная"""

import re
from typing import Any, Optional

from dndai.api.openrouter import api_request
from dndai.api.prompts import COMPRESS_PROMPT
from dndai.core.config import PROVIDERS
from dndai.core.task_types import TaskType


def extract_key_facts(history: list[dict]) -> dict:
    """Извлекает ключевые факты из истории без LLM"""
    facts: dict[str, Any] = {
        "locations": set(),
        "npcs": set(),
        "items": set(),
        "events": set(),
        "player_actions": [],
    }

    # Регулярки для разметки
    location_pattern = re.compile(r'<<([^>]+)>>')
    npc_pattern = re.compile(r'\{\{([^}]+)\}\}')
    item_pattern = re.compile(r'\[\[([^\]]+)\]\]')
    event_pattern = re.compile(r'__([^_]+)__')

    for msg in history:
        content = msg.get("content", "")
        if msg.get("role") == "user":
            facts["player_actions"].append(content[:100])

        facts["locations"].update(location_pattern.findall(content))
        facts["npcs"].update(npc_pattern.findall(content))
        facts["items"].update(item_pattern.findall(content))
        facts["events"].update(event_pattern.findall(content))

    return {
        "locations": list(facts["locations"])[:5],
        "npcs": list(facts["npcs"])[:5],
        "items": list(facts["items"])[:5],
        "events": list(facts["events"])[:5],
        "last_player_action": facts["player_actions"][-1] if facts["player_actions"] else "",
    }


def build_compress_prompt(history: list[dict]) -> str:
    """Строит промпт для суммаризации с извлечёнными фактами"""
    facts = extract_key_facts(history)

    # Последние 10 сообщений для контекста
    recent = history[-10:]
    history_text = "\n".join(
        f"{'Игрок' if m['role'] == 'user' else 'DM'}: {m['content'][:200]}"
        for m in recent
    )

    facts_text = []
    if facts["locations"]:
        facts_text.append(f"Локации: {', '.join(facts['locations'])}")
    if facts["npcs"]:
        facts_text.append(f"NPC: {', '.join(facts['npcs'])}")
    if facts["events"]:
        facts_text.append(f"События: {', '.join(facts['events'])}")

    prompt = COMPRESS_PROMPT.format(history=history_text)
    if facts_text:
        prompt = "Известные факты:\n" + "\n".join(facts_text) + "\n\n" + prompt

    return prompt


def compress_local(history: list[dict]) -> Optional[str]:
    """Пытается сделать суммаризацию локально (эвристика)"""
    if len(history) < 6:
        return None

    facts = extract_key_facts(history)

    # Простая эвристическая суммаризация
    parts = []
    if facts["locations"]:
        parts.append(f"Партия в <<{facts['locations'][0]}>>")
    if facts["npcs"]:
        parts.append("встречают {{" + facts['npcs'][0] + "}}")
    if facts["events"]:
        parts.append("__" + facts['events'][0] + "__")
    if facts["last_player_action"]:
        action = facts["last_player_action"][:80]
        parts.append(f"Игрок: {action}")

    if parts:
        return " ".join(parts) + "."

    return None


def compress_via_api(history: list[dict], task_type: TaskType = TaskType.SIMPLE) -> Optional[str]:
    """Суммаризация через API с приоритетом быстрых моделей"""
    from dndai.core.task_types import (
        PROVIDER_MODELS_BY_TIER,
        TASK_DEFAULT_TIER,
        TIER_PROVIDER_PREFERENCE,
        ModelTier,
    )

    tier = TASK_DEFAULT_TIER.get(task_type, ModelTier.FAST)
    preferred_providers = TIER_PROVIDER_PREFERENCE.get(tier, ["Groq", "Gemini", "OpenRouter"])

    prompt = build_compress_prompt(history)
    messages = [{"role": "user", "content": prompt}]

    # Пробуем провайдеры в порядке приоритета для этого tier
    for provider_name in preferred_providers:
        provider = next((p for p in PROVIDERS if p["name"] == provider_name), None)
        if not provider or (not provider.get("api_key") and provider_name not in ("Ollama", "Ollama-Server")):
            continue

        models = PROVIDER_MODELS_BY_TIER.get(provider_name, {}).get(tier, [])
        for model in models:
            try:
                ans, _err, _kind = api_request(provider, model, messages, max_tok=150, timeout=15)
                if ans and len(ans.strip()) > 10:
                    return ans.strip()
            except Exception:
                continue

    return None


def compress(history: list[dict]) -> Optional[str]:
    """Главная функция суммаризации: локально -> API"""
    # Сначала пробуем локально (мгновенно, бесплатно)
    local_result = compress_local(history)
    if local_result:
        return local_result

    # Фоллбэк на API с быстрыми моделями
    return compress_via_api(history, TaskType.SIMPLE)
