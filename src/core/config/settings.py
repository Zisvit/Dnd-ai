#!/usr/bin/env python3
"""Настройки из переменных окружения"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API ключи
API_KEYS = []

def get_data_dir():
    """Возвращает путь к папке data"""
    base_dir = Path(__file__).parent.parent.parent.parent
    return base_dir / "data"

def load_api_keys():
    """Загружает API ключи из .env или data/keys.txt, или запрашивает в терминале"""
    global API_KEYS
    
    # 1. Пробуем из .env
    keys_str = os.getenv("OPENROUTER_API_KEYS", "")
    if keys_str:
        API_KEYS = [k.strip() for k in keys_str.split(",") if k.strip()]
        if API_KEYS:
            return API_KEYS
    
    # 2. Пробуем из data/keys.txt
    data_dir = get_data_dir()
    keys_file = data_dir / "keys.txt"
    if keys_file.exists():
        try:
            with open(keys_file, 'r', encoding='utf-8') as f:
                keys = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if keys:
                    API_KEYS = keys
                    return API_KEYS
        except:
            pass
    
    # 3. Запрашиваем в терминале
    print("\n" + "="*50)
    print("\033[93m⚠️  API ключи не найдены!\033[0m")
    print("Для работы бота нужны ключи OpenRouter.")
    print("Получить ключи: https://openrouter.ai/keys")
    print("\n💡 Введите один или несколько ключей через запятую:")
    print("   Пример: sk-or-v1-xxxxx, sk-or-v1-yyyyy")
    print("="*50)
    print()
    
    while True:
        user_input = input("🔑 Ключи: ").strip()
        if user_input:
            keys = [k.strip() for k in user_input.split(",") if k.strip()]
            if keys:
                # Сохраняем ключи
                data_dir.mkdir(parents=True, exist_ok=True)
                with open(keys_file, 'w', encoding='utf-8') as f:
                    f.write("# API ключи OpenRouter\n")
                    f.write("# Получить: https://openrouter.ai/keys\n")
                    f.write(f"# Добавлено: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    for k in keys:
                        f.write(f"{k}\n")
                API_KEYS = keys
                print(f"\n\033[92m✅ Сохранено {len(keys)} ключей в {keys_file}\033[0m\n")
                return API_KEYS
            else:
                print("\033[91m❌ Некорректный ввод. Попробуйте ещё раз.\033[0m")
        else:
            print("\033[91m❌ Ключи не могут быть пустыми. Попробуйте ещё раз.\033[0m")

# Загружаем ключи при импорте
load_api_keys()

# Параметры вывода
OUTPUT_DELAY = float(os.getenv("OUTPUT_DELAY", "0.008"))
DEFAULT_PLAYER_NAME = os.getenv("DEFAULT_PLAYER_NAME", "player")

# URL
URL = "https://openrouter.ai/api/v1/chat/completions"
