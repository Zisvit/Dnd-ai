#!/usr/bin/env python3
import random
import re

# Строка целиком является dice-выражением: 2d6, d20, 1d20+5, 3d8-2
_DICE_RE = re.compile(r'(?i)^\s*(\d*)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$')

MAX_DICE_COUNT = 100
MAX_DICE_SIDES = 1000


def roll_dice(cmd):
    """Обрабатывает команды броска кубиков.

    Поддерживает форматы: 2d6, d20, 1d20+5, 3d8-2.
    Возвращает (итог_с_модификатором, список_бросков).
    Если строка не является корректным dice-выражением — (None, None).
    """
    if not isinstance(cmd, str):
        return None, None
    m = _DICE_RE.match(cmd)
    if not m:
        return None, None
    count = int(m.group(1)) if m.group(1) else 1
    sides = int(m.group(2))
    mod = int(m.group(3).replace(' ', '')) if m.group(3) else 0
    if count < 1 or sides < 2:
        return None, None
    count = min(count, MAX_DICE_COUNT)
    sides = min(sides, MAX_DICE_SIDES)
    results = [random.randint(1, sides) for _ in range(count)]
    return sum(results) + mod, results
