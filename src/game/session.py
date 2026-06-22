#!/usr/bin/env python3
import json
import re
from ..core.config import SESSION_DIR
from ..core.text import clean, highlight, format_paragraphs
from ..api.openrouter import compress, save_session, load_session

def load_game_session(session_name):
    data = load_session(session_name)
    history = data.get("history", [])
    memory = data.get("memory", "")
    for m in history:
        m['content'] = clean(m['content'])
    return history, memory

def get_player_name_from_history(history, default_name="player"):
    for m in reversed(history):
        if 'Теперь тебя зовут' in m.get('content', ''):
            match = re.search(r'Теперь тебя зовут (\S+)', m['content'])
            if match:
                return match.group(1)
    return default_name

def compress_if_needed(history, session_name):
    if len(history) > 20:
        from ..core.colors import YELLOW
        print(f"{YELLOW}⏳ Сжимаю историю...{RESET}")
        history = compress(history)
        save_session(session_name, {"history": history, "memory": ""})
    return history

def show_history(history, player_name):
    from ..core.colors import GREEN, BLUE, RESET
    from ..core.text import highlight
    for m in history:
        role = f"{GREEN}{player_name}{RESET}" if m['role'] == 'user' else f"{BLUE}DM{RESET}"
        print(f"{role}: {highlight(m['content'])}")
