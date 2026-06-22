#!/usr/bin/env python3
"""Менеджер моделей"""

import json
import time
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..config import API_KEYS, MODELS_RANKING_FILE, FALLBACK_MODELS
from ..logger import info, debug, warning, error
from .static import load_static_models

class ModelsManager:
    """Менеджер моделей с динамическим ранкингом и статичным резервом"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.rankings: Dict[str, List] = {"red": [], "yellow": [], "blue": []}
        self.static_models = load_static_models()
        self.last_update: Optional[datetime] = None
        self.http_session = requests.Session()
        self.is_updating: bool = False
        self.background_thread: Optional[threading.Thread] = None
        self.running: bool = True
        self._load_from_cache()
        self._start_background_updater()
    
    def _load_from_cache(self) -> bool:
        if not MODELS_RANKING_FILE.exists():
            return False
        
        try:
            with open(MODELS_RANKING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for color in ["red", "yellow", "blue"]:
                    if color in data:
                        self.rankings[color] = data[color]
                self.last_update = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
                
                if self.last_update and (datetime.now() - self.last_update) > timedelta(hours=2):
                    debug("Кэш моделей устарел")
                    return False
                
                info(f"Загружен кэш моделей, обновлено: {self.last_update}")
                return True
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            error(f"Ошибка загрузки кэша: {e}")
            return False
    
    def _save_to_cache(self):
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "red": self.rankings["red"],
                "yellow": self.rankings["yellow"],
                "blue": self.rankings["blue"]
            }
            with open(MODELS_RANKING_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            debug("Кэш сохранён")
        except Exception as e:
            error(f"Ошибка сохранения кэша: {e}")
    
    def _start_background_updater(self):
        if self.background_thread is None or not self.background_thread.is_alive():
            self.background_thread = threading.Thread(
                target=self._background_update_loop,
                daemon=True,
                name="ModelUpdater"
            )
            self.background_thread.start()
            info("Фоновый обновлятор запущен")
    
    def _background_update_loop(self):
        from .benchmark import update_rankings
        while self.running:
            try:
                time.sleep(3600)
                if API_KEYS and not self.is_updating:
                    info("Запуск фонового обновления...")
                    update_rankings(self)
            except Exception as e:
                error(f"Ошибка в фоновом обновлении: {e}")
    
    def _get_from_rankings(self, color: str, count: int = 1) -> List[str]:
        with self.lock:
            models = self.rankings.get(color, [])
            if models:
                return [m[1] for m in models[:count]]
        return []
    
    def get_best_model(self, color: str) -> str:
        models = self._get_from_rankings(color, 1)
        if models:
            return models[0]
        
        if not self.is_updating:
            from .benchmark import update_rankings
            info(f"Ранкинг {color} пуст, обновляю...")
            threading.Thread(target=update_rankings, args=(self,), daemon=True).start()
            time.sleep(0.5)
        
        models = self._get_from_rankings(color, 1)
        if models:
            return models[0]
        
        static = self.static_models.get(color, [])
        if static:
            warning(f"Использую статичную модель для {color}")
            return static[0]
        
        fallback = {
            "red": "openai/gpt-oss-120b:free",
            "yellow": "openai/gpt-oss-20b:free",
            "blue": "meta-llama/llama-3.2-3b-instruct:free"
        }
        return fallback.get(color, fallback["yellow"])
    
    def get_top_models(self, color: str, count: int = 3) -> List[str]:
        models = self._get_from_rankings(color, count)
        if models:
            return models
        
        if not self.is_updating:
            from .benchmark import update_rankings
            threading.Thread(target=update_rankings, args=(self,), daemon=True).start()
            time.sleep(0.5)
        
        models = self._get_from_rankings(color, count)
        if models:
            return models
        
        static = self.static_models.get(color, [])
        if static:
            return static[:count]
        
        fallback = {
            "red": ["openai/gpt-oss-120b:free"],
            "yellow": ["openai/gpt-oss-20b:free"],
            "blue": ["meta-llama/llama-3.2-3b-instruct:free"]
        }
        return fallback.get(color, fallback["yellow"])
    
    def print_summary(self):
        from ..colors import GREEN, RED, YELLOW, CYAN, BLUE, RESET
        
        print(f"\n{CYAN}📊 ДОСТУПНЫЕ МОДЕЛИ:{RESET}")
        has_data = False
        
        for color in ["red", "yellow", "blue"]:
            color_names = {
                "red": f"{RED}🔴 УМНЫЕ (80b-300b){RESET}", 
                "yellow": f"{YELLOW}🟡 СРЕДНИЕ (40b-80b){RESET} ⭐ АВТО", 
                "blue": f"{BLUE}🔵 БЫСТРЫЕ (1b-40b){RESET}"
            }
            models = self.rankings.get(color, [])
            static = self.static_models.get(color, [])
            print(f"\n{color_names[color]}:")
            if models:
                has_data = True
                for i, (ping, model) in enumerate(models, 1):
                    print(f"  {i}. {model} ({ping} мс)")
                if len(models) < len(static):
                    print(f"  💡 Ещё {len(static) - len(models)} статичных в резерве")
            elif static:
                print(f"  ⚡ Использую статичные:")
                for i, model in enumerate(static[:3], 1):
                    print(f"    {i}. {model}")
            else:
                print(f"  ❌ нет моделей")
        
        if self.last_update and has_data:
            age = datetime.now() - self.last_update
            print(f"\n{CYAN}📅 Обновлено: {age.seconds//60} мин назад{RESET}")

    def stop(self):
        self.running = False
        if self.background_thread:
            self.background_thread.join(timeout=2)
            info("Обновлятор остановлен")
