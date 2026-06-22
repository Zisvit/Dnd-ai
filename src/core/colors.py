#!/usr/bin/env python3
"""Цвета ANSI для терминала"""

GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
ORANGE = '\033[38;5;208m'
PURPLE = '\033[95m'
RESET = '\033[0m'

COLORS = {
    'green': GREEN,
    'blue': BLUE,
    'red': RED,
    'yellow': YELLOW,
    'cyan': CYAN,
    'orange': ORANGE,
    'purple': PURPLE,
}

def colorize(text, color):
    """Окрашивает текст в указанный цвет"""
    return f"{COLORS.get(color, RESET)}{text}{RESET}"
