#!/usr/bin/env python3
import sys
import re
import time
from .config import TERM_WIDTH, OUTPUT_DELAY
from .colors import RESET

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def _write(text):
    """Запись в stdout с UTF-8"""
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()

def wrap_ansi(text, width):
    if width < 10:
        width = 40
    lines = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if not paragraph:
            lines.append('')
            continue
        visible = ANSI_ESCAPE.sub('', paragraph)
        if len(visible) <= width:
            lines.append(paragraph)
            continue
        parts = re.split(r'(\s+)', paragraph)
        current_line = ''
        current_len = 0
        for i in range(0, len(parts), 2):
            word = parts[i] if i < len(parts) else ''
            space = parts[i+1] if i+1 < len(parts) else ''
            word_visible = ANSI_ESCAPE.sub('', word)
            space_visible = ANSI_ESCAPE.sub('', space) if space else ''
            word_len = len(word_visible)
            space_len = len(space_visible)
            if current_len + word_len > width and current_len > 0:
                lines.append(current_line.rstrip())
                current_line = word + space
                current_len = word_len + space_len
            else:
                current_line += word + space
                current_len += word_len + space_len
        if current_line.strip():
            lines.append(current_line.rstrip())
    return '\n'.join(lines)

def slow_print(text, delay=OUTPUT_DELAY):
    if not text:
        return
    if not text.endswith(RESET):
        text += RESET
    wrapped = wrap_ansi(text, TERM_WIDTH)
    lines = wrapped.split('\n')
    for line_idx, line in enumerate(lines):
        if not line:
            _write('\n')
            continue
        parts = re.split(r'(\x1B\[[0-9;]*[a-zA-Z])', line)
        for part in parts:
            if re.match(r'\x1B\[[0-9;]*[a-zA-Z]', part):
                _write(part)
            else:
                for ch in part:
                    _write(ch)
                    if delay > 0:
                        time.sleep(delay)
        if line_idx < len(lines) - 1:
            _write('\n')
    _write('\n')

def clean(text):
    if not text:
        return ''
    return ANSI_ESCAPE.sub('', text)
