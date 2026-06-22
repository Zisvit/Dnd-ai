#!/usr/bin/env python3
import re
from src.core.colors import GREEN, BLUE, RED, YELLOW, CYAN, ORANGE, PURPLE, RESET
from src.api.openrouter import FAST_MODELS, FAST_PINGS, BLACKLIST, load_fast_cache, save_session
from .help import show_dm_help, show_color_legend, test_colors

forced_model = None
forced_detail_level = 0
PLAYER_NAME = "player"

def set_globals(forced_model_val, forced_detail_level_val, player_name_val):
    global forced_model, forced_detail_level, PLAYER_NAME
    forced_model = forced_model_val
    forced_detail_level = forced_detail_level_val
    PLAYER_NAME = player_name_val

def show_dm_status():
    global forced_model, forced_detail_level
    mn = {None: f"{GREEN}авто{RESET}", 'red': f"{RED}умные{RESET}", 
          'yellow': f"{YELLOW}средние{RESET}", 'blue': f"{BLUE}тупые{RESET}"}.get(
              forced_model, f"{GREEN}авто{RESET}")
    det = f"{YELLOW}{'★'*forced_detail_level}{RESET}" if forced_detail_level > 0 else "обычный"
    print(f"{GREEN}Режим:{RESET} модель {mn}, детализация {det}")

def parse_model_switch_text(cmd_text):
    low = cmd_text.lower().strip()
    if re.search(r'(красн|red|умн|толков|продвинут|120)', low):
        return 'red'
    if re.search(r'(жёлт|желт|yellow|средн|норм|70)', low):
        return 'yellow'
    if re.search(r'(син|blue|туп|слаб|эконом|20|10)', low):
        return 'blue'
    if re.search(r'авто|автомат|обычн|default', low):
        return 'auto'
    return None

def update_models():
    from src.core.models import update_rankings
    print(f"{YELLOW}🔄 Обновляю ранкинги моделей...{RESET}")
    update_rankings(models_manager)
    print(f"{GREEN}✅ Ранкинги обновлены!{RESET}")

def show_models():
    from src.core.models import show_rankings
    show_rankings()

def clear_history_and_exit(session_name):
    from src.api.openrouter import save_session
    print(f"{YELLOW}♻️  История очищена.{RESET}")
    save_session(session_name, {"history": [], "memory": ""})
    print(f"{GREEN}✅ Выхожу. До встречи!{RESET}")

def handle_dm_command(raw_act, history, session_name):
    return "ok", history, "", ""
