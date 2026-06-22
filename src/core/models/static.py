#!/usr/bin/env python3
"""Статичные модели — резерв"""

from typing import Dict, List
from ..config import STATIC_MODELS_FILE, FALLBACK_MODELS
from ..logger import info, warning, error

def load_static_models() -> Dict[str, List[str]]:
    """Загружает статичные модели из файла"""
    static_models = {"red": [], "yellow": [], "blue": []}
    
    if STATIC_MODELS_FILE.exists():
        try:
            with open(STATIC_MODELS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '|' in line:
                        category, model = line.split('|', 1)
                        category = category.strip().lower()
                        model = model.strip()
                        if category in static_models:
                            static_models[category].append(model)
            info(f"Загружено статичных моделей: {len(static_models['red'])} красных, "
                 f"{len(static_models['yellow'])} жёлтых, {len(static_models['blue'])} синих")
        except Exception as e:
            error(f"Ошибка загрузки статичных моделей: {e}")
    
    # Заполняем пустые категории
    for color in ["red", "yellow", "blue"]:
        if not static_models[color]:
            fallback = {
                "red": "openai/gpt-oss-120b:free",
                "yellow": "openai/gpt-oss-20b:free",
                "blue": "meta-llama/llama-3.2-3b-instruct:free"
            }
            static_models[color] = [fallback.get(color, fallback["yellow"])]
            warning(f"Категория {color} пуста, использована модель по умолчанию")
    
    return static_models
