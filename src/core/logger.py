#!/usr/bin/env python3
"""Логирование для бота"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from .config import DATA_DIR

# Настройка логгера
LOG_FILE = DATA_DIR / "dnd_bot.log"

def setup_logger(level=logging.INFO):
    """Настраивает логгер"""
    logger = logging.getLogger('dnd_bot')
    logger.setLevel(level)
    
    # Очищаем существующие хендлеры
    logger.handlers.clear()
    
    # Формат с временем
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Хендлер для файла
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Хендлер для консоли (только ошибки и выше)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Глобальный логгер
logger = setup_logger()

def debug(msg):
    logger.debug(msg)

def info(msg):
    logger.info(msg)

def warning(msg):
    logger.warning(msg)

def error(msg):
    logger.error(msg)

def critical(msg):
    logger.critical(msg)
