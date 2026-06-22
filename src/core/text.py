#!/usr/bin/env python3
import re
from .colors import GREEN, BLUE, RED, YELLOW, CYAN, ORANGE, PURPLE, RESET
from .output import ANSI_ESCAPE, clean

def highlight(text):
    """
    Сюжетная подсветка — только важные элементы игры:
    - {{Персонажи}} — NPC
    - <<Места>> — локации
    - [[Предметы]] — вещи
    - __События__ — повороты сюжета
    - !!Эмоции!! — чувства
    - "Диалоги" — речь персонажей
    """
    if not text:
        return ''
    
    # Убираем существующие ANSI
    text = ANSI_ESCAPE.sub('', text)
    
    # {{Персонажи}} — голубой (NPC, имена)
    text = re.sub(r'\{\{([^}]+)\}\}', CYAN + r'\1' + RESET, text)
    
    # <<Места>> — жёлтый (локации)
    text = re.sub(r'<<([^>]+)>>', YELLOW + r'\1' + RESET, text)
    
    # [[Предметы]] — оранжевый (важные вещи)
    text = re.sub(r'\[\[([^]]+)\]\]', ORANGE + r'\1' + RESET, text)
    
    # __События__ — фиолетовый (повороты сюжета)
    text = re.sub(r'__([^_]+)__', PURPLE + r'\1' + RESET, text)
    
    # !!Эмоции!! — зелёный (чувства)
    text = re.sub(r'!!([^!]+)!!', GREEN + r'\1' + RESET, text)
    
    # "Диалоги" — синий (речь)
    text = re.sub(r'"([^"]+)"', BLUE + r'"\1"' + RESET, text)
    
    return text

def format_paragraphs(text, sentences_per_group=3):
    """Форматирует текст в абзацы"""
    if not text:
        return ''
    text = text.replace('\n', ' ')
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return text
    if len(sentences) <= sentences_per_group:
        return ' '.join(sentences)
    groups = []
    for i in range(0, len(sentences), sentences_per_group):
        group = ' '.join(sentences[i:i+sentences_per_group])
        groups.append(group.strip())
    return '\n\n'.join(groups)
