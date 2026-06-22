#!/usr/bin/env python3
"""Бенчмарк моделей"""

import time
import re
import requests
from datetime import datetime
from typing import Dict, List, Optional
from ..config import API_KEYS, FALLBACK_MODELS, URL
from ..logger import info, debug, error, warning

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
        
        info(f"Найдено моделей: красных={len(free['red'])}, жёлтых={len(free['yellow'])}, синих={len(free['blue'])}")
        return free
    except Exception as e:
        error(f"Ошибка получения списка моделей: {e}")
        return None

def check_model(session: requests.Session, model: str) -> tuple[bool, Optional[float]]:
    if not API_KEYS:
        return False, None
    
    key = API_KEYS[0]
    
    try:
        start = time.time()
        r = session.post(URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json; charset=utf-8"},
            json={"model": model, "messages": [{"role":"user","content":"ping"}], 
                  "max_tokens": 1, "temperature": 0.0},
            timeout=8)
        if r.status_code != 200:
            return False, None
        ping = round((time.time() - start) * 1000, 1)
    except:
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
            results = []
            for model in models:
                total += 1
                ok, ping = check_model(manager.http_session, model)
                if ok:
                    results.append((ping, model))
                    working += 1
                time.sleep(0.1)
            results.sort(key=lambda x: x[0])
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
