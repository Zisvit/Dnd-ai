#!/usr/bin/env python3
import re
import random

def roll_dice(cmd):
    """Обрабатывает команды броска кубиков"""
    m = re.search(r'(\d+)d(\d+)', cmd.lower())
    if m:
        count = min(int(m.group(1)), 100)
        sides = min(int(m.group(2)), 1000)
        results = [random.randint(1, sides) for _ in range(count)]
        return sum(results), results
    
    m = re.search(r'd(\d+)\s*([+-]\s*\d+)', cmd.lower())
    if m:
        sides = min(int(m.group(1)), 1000)
        mod = int(m.group(2).replace(' ', ''))
        result = random.randint(1, sides) + mod
        return result, [result]
    
    m = re.search(r'd(\d+)', cmd.lower())
    if m:
        sides = min(int(m.group(1)), 1000)
        result = random.randint(1, sides)
        return result, [result]
    
    return None, None
