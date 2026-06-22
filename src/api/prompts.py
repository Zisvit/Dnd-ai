#!/usr/bin/env python3
from src.core.config import PROMPTS_DIR

def load_prompt(filename):
    path = PROMPTS_DIR / filename
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

SYSTEM_PROMPT_TEMPLATE = load_prompt("system_prompt.txt")
FIRST_MESSAGE_PROMPT = load_prompt("first_message.txt")
JAILBREAK_PROMPT = load_prompt("jailbreak.txt")
COMPRESS_PROMPT = load_prompt("compress.txt")
