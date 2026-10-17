#!/usr/bin/env python3
"""Тесты dndai/scripts/compress.py (регрессы №4 и №5).

Модуль берём через importlib: dndai/scripts/__init__.py реэкспортирует
функцию compress, затеняя подмодуль, поэтому `import dndai.scripts.compress`
связал бы функцию, а не модуль.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib

compress_mod = importlib.import_module("dndai.scripts.compress")
from dndai.core.task_types import ModelTier, TaskType

H6 = [
    {"role": "user", "content": "вхожу в <<Таверну>> и ищу бармена"},
    {"role": "assistant", "content": "Вас встречает {{Бармен}} и предлагает эль."},
    {"role": "user", "content": "беру эль"},
    {"role": "assistant", "content": "Бармен бросает монету. __пьяная драка__"},
    {"role": "user", "content": "уворачиваюсь"},
    {"role": "user", "content": "иду в <<Таверну>> к стойке"},
]


def test_compress_local_uses_double_brace_for_npc():
    """Регресс №5: в локальной сводке терялся второй '{' у NPC."""
    result = compress_mod.compress_local(H6)
    assert result is not None
    assert "{{Бармен}}" in result


def test_compress_local_short_history_returns_none():
    assert compress_mod.compress_local(H6[:3]) is None


def test_compress_via_api_returns_summary(monkeypatch):
    """Регресс №4: api_request возвращает 3 значения, распаковка на 2 падала."""
    monkeypatch.setattr(
        compress_mod,
        "PROVIDERS",
        [
            {
                "name": "Groq",
                "base_url": "http://g",
                "api_key": "k",
                "models": ["m-fast"],
            }
        ],
    )
    monkeypatch.setattr(
        compress_mod,
        "api_request",
        lambda *a, **k: (
            "  Сводка: партия вошла в таверну и встретила бармена.  ",
            None,
            None,
        ),
    )
    tt = importlib.import_module("dndai.core.task_types")
    monkeypatch.setattr(tt, "TIER_PROVIDER_PREFERENCE", {ModelTier.FAST: ["Groq"]})
    monkeypatch.setattr(
        tt, "PROVIDER_MODELS_BY_TIER", {"Groq": {ModelTier.FAST: ["m-fast"]}}
    )
    monkeypatch.setattr(tt, "TASK_DEFAULT_TIER", {TaskType.SIMPLE: ModelTier.FAST})

    result = compress_mod.compress_via_api(H6, TaskType.SIMPLE)
    assert result == "Сводка: партия вошла в таверну и встретила бармена."


def test_compress_prefers_local_without_api(monkeypatch):
    def boom(*a, **k):
        raise AssertionError(
            "compress_via_api не должен вызываться при успехе локально"
        )

    monkeypatch.setattr(compress_mod, "compress_via_api", boom)
    result = compress_mod.compress(H6)
    assert result is not None and "Бармен" in result


def test_build_compress_prompt_contains_history_and_facts():
    prompt = compress_mod.build_compress_prompt(H6)
    assert "иду в <<Таверну>> к стойке" in prompt
    assert "Локации: Таверну" in prompt
    assert "NPC: Бармен" in prompt
