#!/usr/bin/env python3
"""Управление моделями — класс и методы доступа"""

import json
import time
import threading
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from .config import API_KEYS, FALLBACK_MODELS, DATA_DIR
from .colors import GREEN, RED, YELLOW, CYAN, BLUE, RESET
from .logger import logger, error, info, debug, warning

MODELS_RANKING_FILE = DATA_DIR / "models_ranking.json"
STATIC_MODELS_FILE = DATA_DIR / "static_models.txt"

class ModelsManager:
    """Менеджер моделей с динамическим ранкингом и статичным резервом"""
    
    def __init__(self) -> None:
        self.lock: threading.Lock = threading.Lock()
        self.rankings: Dict[str, List] = {"red": [], "yellow": [], "blue": []}
        self.static_models: Dict[str, List[str]] = {"red": [], "yellow": [], "blue": []}
        self.last_update: Optional[datetime] = None
        self.http_session = requests.Session()
        self.is_updating: bool = False
        self.background_thread: Optional[threading.Thread] = None
        self.running: bool = True
        self._load_static_models()
        self._load_from_cache()
        self._start_background_updater()
    
    def _load_static_models(self) -> None:
        """Загружает статичные модели из файла"""
        self.static_models = {"red": [], "yellow": [], "blue": []}
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
                            if category in self.static_models:
                                self.static_models[category].append(model)
                info(f"Загружено статичных моделей: {len(self.static_models['red'])} красных, "
                     f"{len(self.static_models['yellow'])} жёлтых, {len(self.static_models['blue'])} синих")
            except Exception as e:
                error(f"Ошибка загрузки статичных моделей: {e}")
        
        # Заполняем пустые категории
        for color in ["red", "yellow", "blue"]:
            if not self.static_models[color]:
                if color == "red":
                    self.static_models[color] = ["openai/gpt-oss-120b:free"]
                elif color == "yellow":
                    self.static_models[color] = ["openai/gpt-oss-20b:free"]
                else:
                    self.static_models[color] = ["meta-llama/llama-3.2-3b-instruct:free"]
                warning(f"Категория {color} пуста, использованы модели по умолчанию")
    
    def _load_from_cache(self) -> bool:
        """Загружает ранкинги из кэша"""
        if not MODELS_RANKING_FILE.exists():
            return False
        
        try:
            with open(MODELS_RANKING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for color in ["red", "yellow", "blue"]:
                    if color in data:
                        self.rankings[color] = data[color]
                self.last_update = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
                
                # Проверяем актуальность (не старше 2 часов)
                if self.last_update and (datetime.now() - self.last_update) > timedelta(hours=2):
                    debug("Кэш моделей устарел, будет обновлён")
                    return False
                
                info(f"Загружен кэш моделей, обновлено: {self.last_update}")
                return True
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            error(f"Ошибка загрузки кэша моделей: {e}")
            return False
    
    def _save_to_cache(self) -> None:
        """Сохраняет ранкинги в кэш"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "red": self.rankings["red"],
                "yellow": self.rankings["yellow"],
                "blue": self.rankings["blue"]
            }
            with open(MODELS_RANKING_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            debug("Кэш моделей сохранён")
        except Exception as e:
            error(f"Ошибка сохранения кэша моделей: {e}")
    
    def _start_background_updater(self) -> None:
        """Запускает фоновый поток обновления ранкингов"""
        if self.background_thread is None or not self.background_thread.is_alive():
            self.background_thread = threading.Thread(
                target=self._background_update_loop,
                daemon=True,
                name="ModelUpdater"
            )
            self.background_thread.start()
            info("Фоновый обновлятор моделей запущен")
    
    def _background_update_loop(self) -> None:
        """Фоновый цикл обновления ранкингов каждые 60 минут"""
        from .models_benchmark import update_rankings
        
        while self.running:
            try:
                time.sleep(3600)  # 60 минут
                if API_KEYS and not self.is_updating:
                    info("Запуск фонового обновления ранкингов...")
                    update_rankings(self)
            except Exception as e:
                error(f"Ошибка в фоновом обновлении: {e}")
    
    def _get_from_rankings(self, color: str, count: int = 1) -> List[str]:
        """Получает модели из ранкинга"""
        with self.lock:
            models = self.rankings.get(color, [])
            if models:
                return [m[1] for m in models[:count]]
        return []
    
    def get_best_model(self, color: str) -> str:
        """Возвращает лучшую модель из категории"""
        # 1. Пробуем динамические
        models = self._get_from_rankings(color, 1)
        if models:
            debug(f"Использую динамическую модель для {color}: {models[0]}")
            return models[0]
        
        # 2. Запускаем обновление если пусто
        if not self.is_updating:
            from .models_benchmark import update_rankings
            info(f"Ранкинг для {color} пуст, запускаю обновление...")
            threading.Thread(target=update_rankings, args=(self,), daemon=True).start()
            time.sleep(0.5)
        
        models = self._get_from_rankings(color, 1)
        if models:
            return models[0]
        
        # 3. Статичные как резерв
        static = self.static_models.get(color, [])
        if static:
            warning(f"Использую статичную модель для {color}: {static[0]}")
            return static[0]
        
        # 4. Абсолютный запасной
        fallback = {
            "red": "openai/gpt-oss-120b:free",
            "yellow": "openai/gpt-oss-20b:free",
            "blue": "meta-llama/llama-3.2-3b-instruct:free"
        }
        warning(f"Использую запасную модель для {color}: {fallback.get(color, fallback['yellow'])}")
        return fallback.get(color, fallback["yellow"])
    
    def get_top_models(self, color: str, count: int = 3) -> List[str]:
        """Возвращает топ модели из категории"""
        models = self._get_from_rankings(color, count)
        if models:
            return models
        
        if not self.is_updating:
            from .models_benchmark import update_rankings
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
    
    def print_summary(self) -> None:
        """Выводит краткую сводку по моделям"""
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
                    print(f"  💡 Ещё {len(static) - len(models)} статичных моделей в резерве")
            elif static:
                print(f"  ⚡ Использую статичные:")
                for i, model in enumerate(static[:3], 1):
                    print(f"    {i}. {model}")
            else:
                print(f"  ❌ нет моделей")
        
        if self.last_update and has_data:
            age = datetime.now() - self.last_update
            print(f"\n{CYAN}📅 Обновлено: {age.seconds//60} мин назад{RESET}")

# Глобальный экземпляр
models_manager = ModelsManager()

def get_best_model(color: str) -> str:
    return models_manager.get_best_model(color)

def get_top_models(color: str, count: int = 3) -> List[str]:
    return models_manager.get_top_models(color, count)

def show_rankings() -> None:
    models_manager.print_summary()

def init_models_manager() -> None:
    if not models_manager.rankings or not any(models_manager.rankings.values()):
        from .models_benchmark import update_rankings
        info("Запуск первичного обновления ранкингов...")
        threading.Thread(target=update_rankings, args=(models_manager,), daemon=True).start()

def model_color(model: str, fast_models: Dict) -> str:
    if not fast_models:
        return RESET
    for color, models in fast_models.items():
        if model in models:
            return {"yellow": YELLOW, "red": RED, "blue": BLUE}[color]
    return RESET

def shutdown_models() -> None:
    """Останавливает фоновые потоки моделей"""
    info("Останавливаю обновлятор моделей...")
    models_manager.running = False
    if models_manager.background_thread:
        models_manager.background_thread.join(timeout=2)
        info("Обновлятор моделей остановлен")
