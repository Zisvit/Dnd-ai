#!/usr/bin/env python3
"""Главный игровой цикл D&D Cyberpunk Master Bot"""

import sys
import re
from src.core.config import API_KEYS, DATA_DIR
from src.core.colors import GREEN, BLUE, RED, YELLOW, CYAN, ORANGE, PURPLE, RESET
from src.core.output import slow_print
from src.core.text import clean, highlight, format_paragraphs
from src.core.dice import roll_dice
from src.core.models import model_color, get_best_model, shutdown_models, models_manager
from src.core.shutdown import shutdown_handler
from src.core.logger import info, error
from src.api.openrouter import init_models, ask_dm, save_session, FAST_MODELS, expected_model
from src.game.session import load_game_session, get_player_name_from_history, compress_if_needed, show_history
from src.game.commands import (
    set_globals, show_dm_help, show_color_legend, test_colors,
    handle_dm_command, show_dm_status, update_models, show_models, 
    clear_history_and_exit
)
import src.game.commands as commands

shutdown_handler.register(shutdown_models)


def show_logo():
    print(f"\n{ORANGE}╔════════════════════════════════════════════╗")
    print(f"{YELLOW}              {RED}DnD_AI{YELLOW}-{CYAN}by-{PURPLE}AxemaN{RESET}     ")
    print(f"{ORANGE}╚════════════════════════════════════════════╝{RESET}\n")


def check_api_keys():
    if not API_KEYS:
        print(f"{RED}❌ Нет API ключей!{RESET}")
        print(f"{YELLOW}Добавьте ключи в {DATA_DIR}/keys.txt или настройте .env{RESET}")
        print(f"{CYAN}Получить ключи: https://openrouter.ai/keys{RESET}")
        return False
    return True


def show_startup_hint():
    print(f"{CYAN}💡 Введите 'помощь' или '/help' для списка команд{RESET}")
    print()


def print_welcome(session_name, history, player_name, memory):
    print(f"{GREEN}📂 Сессия '{session_name}' загружена{RESET}")
    if memory:
        print(f"{CYAN}🧠 Память: {memory}{RESET}")
    print(f"{YELLOW}📜 Последние события:{RESET}")
    for m in history[-5:]:
        role = f"{GREEN}{player_name}{RESET}" if m['role'] == 'user' else f"{BLUE}DM{RESET}"
        print(f"{role}: {highlight(m['content'])}")
    print()
    show_startup_hint()


def start_new_game(session_name):
    print(f"{GREEN}🆕 Новая сессия '{session_name}'{RESET}")
    show_startup_hint()
    show_dm_status()

    model = expected_model(commands.forced_model)
    col = model_color(model, FAST_MODELS)
    print(f"{col}DM:{RESET} ", end='', flush=True)

    history = [{"role": "user", "content": "Начинай игру. Опиши таверну."}]
    text, mdl = ask_dm(history, "", "Начинай игру. Опиши таверну.",
                       commands.forced_model, commands.forced_detail_level)

    if not text:
        print(f"{RED}❌ Модели недоступны{RESET}")
        return None, None

    history.append({"role": "assistant", "content": clean(text)})
    save_session(session_name, {"history": history, "memory": ""})
    slow_print(highlight(format_paragraphs(text)))

    return history, ""


def main():
    show_logo()

    if not check_api_keys():
        return

    init_models()

    session_name = "default"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        session_name = sys.argv[1]

    history, memory = load_game_session(session_name)
    player_name = get_player_name_from_history(history)
    commands.PLAYER_NAME = player_name
    set_globals(commands.forced_model, commands.forced_detail_level, commands.PLAYER_NAME)

    if history:
        history = compress_if_needed(history, session_name)
        print_welcome(session_name, history, player_name, memory)
    else:
        history, memory = start_new_game(session_name)
        if history is None:
            return

    try:
        while True:
            try:
                act = input(f"{GREEN}{commands.PLAYER_NAME} >_{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                save_session(session_name, {"history": history, "memory": memory})
                print()
                break

            if not act:
                continue

            if act.lower() in ("выход", "exit", "quit", "/quit"):
                save_session(session_name, {"history": history, "memory": memory})
                print(f"{GREEN}✅ Сессия сохранена. До встречи!{RESET}")
                break

            if re.search(r'^(очистить|сброс|clear|reset)$', act, re.IGNORECASE):
                clear_history_and_exit(session_name)
                break

            if act.lower() in ('/help', 'помощь', 'хелп'):
                show_dm_help()
                continue

            if act.lower() in ('/colors', 'test colors', 'тест цветов'):
                test_colors()
                continue

            if act.lower() in ('/colors-legend', 'цвета', 'цветовая легенда'):
                show_color_legend()
                continue

            if act.lower() in ('история', '/history'):
                show_history(history, commands.PLAYER_NAME)
                continue

            if act.lower() in ('обнови память', 'update memory'):
                print(f"{YELLOW}⏳ Обновляю память...{RESET}")
                history = compress_if_needed(history, session_name)
                save_session(session_name, {"history": history, "memory": ""})
                print(f"{CYAN}🧠 Память обновлена.{RESET}")
                continue

            if act.lower() in ('/models', 'модели', 'показать модели'):
                show_models()
                continue

            if act.lower() in ('/update', 'обновить модели', 'update models'):
                update_models()
                continue

            if re.match(r'(?i)(dm|дм)\s+', act):
                cmd = re.sub(r'(?i)(dm|дм)\s+', '', act).strip()
                if cmd:
                    print(f"{YELLOW}📜 Приказ мастеру: {cmd}{RESET}")
                    history.append({"role": "system", "content": f"Прямой приказ мастеру: {cmd}"})
                    
                    col = model_color(expected_model(commands.forced_model), FAST_MODELS)
                    print(f"{col}DM:{RESET} ", end='', flush=True)
                    
                    text, mdl = ask_dm(history, memory, "", 
                                      commands.forced_model, commands.forced_detail_level)
                    
                    if not text:
                        print(f"{RED}❌ Модели недоступны{RESET}")
                        if history and history[-1]['role'] == 'system':
                            history.pop()
                        continue
                    history.append({"role": "assistant", "content": clean(text)})
                    slow_print(highlight(format_paragraphs(text)))
                    save_session(session_name, {"history": history, "memory": memory})
                continue

            dice, results = roll_dice(act)
            if dice is not None:
                act = f"{act} [Бросок d20: {dice}]"
                print(f"{BLUE}🎲 {dice}{RESET}")

            history.append({"role": "user", "content": act})

            if len(history) >= 20:
                print(f"{YELLOW}⏳ Автосжатие...{RESET}")
                history = compress_if_needed(history, session_name)

            col = model_color(expected_model(commands.forced_model), FAST_MODELS)
            print(f"{col}DM:{RESET} ", end='', flush=True)

            text, mdl = ask_dm(history, memory, act,
                              commands.forced_model, commands.forced_detail_level)

            if not text:
                print(f"{RED}❌ Модели недоступны{RESET}")
                history.pop()
                continue

            history.append({"role": "assistant", "content": clean(text)})
            slow_print(highlight(format_paragraphs(text)))

            if 'Теперь тебя зовут' in text:
                match = re.search(r'Теперь тебя зовут (\S+)', text)
                if match:
                    commands.PLAYER_NAME = match.group(1)

            save_session(session_name, {"history": history, "memory": memory})
            
    except Exception as e:
        error(f"Критическая ошибка: {e}")
        save_session(session_name, {"history": history, "memory": memory})
        raise


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        info("Принудительное завершение")
        sys.exit(0)
    except Exception as e:
        error(f"Необработанная ошибка: {e}")
        sys.exit(1)
