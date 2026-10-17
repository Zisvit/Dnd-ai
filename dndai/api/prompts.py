#!/usr/bin/env python3
"""Промпты для API — единая точка загрузки шаблонов.

Текстовые шаблоны лежат в dndai/prompts (пакетный дефолт; переопределение —
$DND_PROMPTS_DIR или ~/.dnd_ai/prompts, см. core/config/paths.get_prompts_dir),
сам загрузчик — в core/config/prompts.py. Здесь только сборка констант,
которые использует api-слой."""

from dndai.core.config.prompts import load_prompt

SYSTEM_PROMPT_TEMPLATE = load_prompt("system_prompt.txt")
FIRST_MESSAGE_PROMPT = load_prompt("first_message.txt")
JAILBREAK_PROMPT = load_prompt("jailbreak.txt")
COMPRESS_PROMPT = load_prompt("compress.txt")
