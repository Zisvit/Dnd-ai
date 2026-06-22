#!/usr/bin/env python3
"""Бенчмарк моделей — проверка пинга и русского языка"""

import time
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
from ..config import API_KEYS, FALLBACK_MODELS, URL
from ..logger import info, debug, error, warning

# Список заведомо рабочих моделей с хорошим русским (приоритет)
PRIORITY_MODELS = {
    "red": [
        "openai/gpt-oss-120b:free",
        "deepseek/deepseek-r1:free",
    ],
    "yellow": [
        "openai/gpt-oss-20b:free",
        "qwen/qwen-2.5-32b-instruct:free",
        "google/gemini-2.0-flash-thinking-exp:free",
    ],
    "blue": [
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free",
    ]
}

def get_free_models(session: requests.Session) -> Optional[Dict[str, List[str]]]:
    try:
        resp = session.get("https://openrouter.ai/api/v1/models", timeout=30)
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        free = {"red": [], "yellow": [], "blue": []}
        
        for model in data.get("data", []):
            pricing = model.get("pricing", {})
            if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                mid = model["id"]
                # Пропускаем заведомо плохие модели
                if any(x in mid for x in ["openrouter/free", "nvidia/nemotron", "poolside", "google/lyria"]):
                    continue
                m = re.search(r'(\d+)b', mid)
                if m:
                    size = int(m.group(1))
                    if size < 40:
                        free["blue"].append(mid)
                    elif size <= 80:
                        free["yellow"].append(mid)
                    else:
                        free["red"].append(mid)
                else:
                    free["yellow"].append(mid)
        
        # Добавляем приоритетные модели, если их нет
        for color in ["red", "yellow", "blue"]:
            for model in PRIORITY_MODELS.get(color, []):
                if model not in free[color]:
                    free[color].append(model)
        
        info(f"Найдено моделей: красных={len(free['red'])}, жёлтых={len(free['yellow'])}, синих={len(free['blue'])}")
        return free
    except Exception as e:
        error(f"Ошибка получения списка моделей: {e}")
        return None

def check_model(session: requests.Session, model: str) -> tuple[bool, Optional[float]]:
    if not API_KEYS:
        return False, None
    
    key = API_KEYS[0]
    
    # Проверка пинга (увеличиваем таймаут до 15 сек для медленных моделей)
    try:
        start = time.time()
        r = session.post(URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json; charset=utf-8"},
            json={"model": model, "messages": [{"role":"user","content":"ping"}], 
                  "max_tokens": 1, "temperature": 0.0},
            timeout=15)
        if r.status_code != 200:
            return False, None
        ping = round((time.time() - start) * 1000, 1)
    except:
        return False, None
    
    # Проверка русского языка (только если пинг < 3000 мс)
    if ping > 3000:
        return False, None
    
    try:
        r = session.post(URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json; charset=utf-8"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Ответь на русском одним словом: привет"}],
                "max_tokens": 10,
                "temperature": 0.0
            },
            timeout=10)
        if r.status_code != 200:
            return False, None
        text = r.json()["choices"][0]["message"]["content"].strip()
        if not re.search(r'[а-яА-ЯёЁ]', text):
            return False, None
    except:
        return False, None
    
    return True, ping

def update_rankings(manager):
    if manager.is_updating:
        return
    if not API_KEYS:
        warning("Нет API ключей для бенчмарка")
        return
    
    manager.is_updating = True
    info("Начинаю бенчмарк моделей...")
    
    try:
        all_models = get_free_models(manager.http_session)
        if not all_models:
            all_models = FALLBACK_MODELS.copy()
        
        new_rankings = {"red": [], "yellow": [], "blue": []}
        total = 0
        working = 0
        
        for color in ["red", "yellow", "blue"]:
            models = all_models.get(color, [])
            # Ограничиваем количество проверяемых моделей для скорости
            models = models[:15]
            results = []
            
            for model in models:
                total += 1
                ok, ping = check_model(manager.http_session, model)
                if ok:
                    results.append((ping, model))
                    working += 1
                    info(f"✅ {model} — {ping}мс")
                time.sleep(0.2)
            
            results.sort(key=lambda x: x[0])
            # Берём топ-5, но не больше чем есть
            new_rankings[color] = [[p, m] for p, m in results[:5]]
        
        with manager.lock:
            manager.rankings = new_rankings
            manager.last_update = datetime.now()
            manager._save_to_cache()
        
        info(f"Бенчмарк завершён: проверено {total}, найдено {working} рабочих")
    except Exception as e:
        error(f"Ошибка бенчмарка: {e}")
    finally:
        manager.is_updating = False
