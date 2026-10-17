#!/usr/bin/env python3
"""Главный игровой цикл D&D Cyberpunk Master Bot"""

import sys
import os
import re
import atexit
import argparse
import shutil

# Стрелки ↑↓ и редактирование строки ввода (история переживает перезапуск)
try:
    import readline
except ImportError:
    readline = None

# Гарантируем UTF-8 вывод (кириллица) даже если локаль/pipe не UTF-8
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from dndai import __version__
from dndai.core.config import (
    API_KEYS,
    DATA_DIR,
    app_home,
    ensure_home,
    get_prompts_dir,
    migrate_legacy_data,
    package_prompts_dir,
)
from dndai.core.colors import GREEN, BLUE, RED, YELLOW, CYAN, ORANGE, PURPLE, RESET
from dndai.core.output import slow_print, StreamingPrinter
from dndai.core.text import clean, highlight, format_paragraphs, emoji
from dndai.core.dice import roll_dice
from dndai.core.models import shutdown_models
from dndai.core.shutdown import shutdown_handler
from dndai.core.logger import info, error, critical
from dndai.core.i18n import t
from dndai.api.openrouter import init_models, ask_dm, get_current_model
from dndai.api.prompts import SYSTEM_PROMPT_TEMPLATE
from dndai.core.config import STREAM_MODE
from dndai.core.task_types import TaskType
from dndai.game.session import (
    load_game_session,
    get_player_name_from_history,
    compress_if_needed,
    save_game_session,
    rollback_session,
    backup_session,
    archive_log,
)
from dndai.game.commands import set_globals, show_dm_status, clear_history_and_exit
from dndai.game.character import CharacterState, sync_with_progression
from dndai.game.world import WorldState
from dndai.game.party import Party
from dndai.game.rpg import (
    SpellBook,
    Progression,
    StatusEffects,
    Quests,
    NPCs,
    TimeWeather,
    Journal,
    Macros,
    Style,
    Enemies,
    Reputation,
)
from dndai.commands import dispatch, GameContext
import dndai.game.commands as commands

shutdown_handler.register(shutdown_models)


def setup_input_history():
    """История ввода: стрелки ↑↓ работают и между запусками игры."""
    if readline is None:
        return
    histfile = DATA_DIR / "input_history"
    readline.set_history_length(500)
    try:
        readline.read_history_file(str(histfile))
    except (FileNotFoundError, OSError):
        pass

    def _dump_history():
        try:
            readline.write_history_file(str(histfile))
        except OSError:
            pass  # каталог мог исчезнуть — не шумим на выходе

    atexit.register(_dump_history)


def show_logo():
    print(f"\n{ORANGE}╔════════════════════════════════════════════╗")
    print(
        f"{YELLOW}              {RED}DnD_AI{YELLOW}-{CYAN}by-{PURPLE}AxemaN{RESET}     "
    )
    print(f"{ORANGE}╚════════════════════════════════════════════╝{RESET}\n")


def check_api_keys():
    if API_KEYS:
        return True
    # Явно заданная локальная/своя Ollama — облачные ключи не обязательны.
    if os.getenv("OLLAMA_SERVER_URL") or os.getenv("OLLAMA_BASE_URL"):
        return True
    print(f"{RED}❌ {t('main.no_keys')}{RESET}")
    print(f"{YELLOW}{t('main.no_keys_hint', home_env=app_home() / '.env')}{RESET}")
    print(f"{CYAN}{t('main.no_keys_url')}{RESET}")
    return False


def show_startup_hint():
    print(f"{CYAN}{t('main.startup_hint')}{RESET}")
    print()


def print_welcome(session_name, history, player_name, summary, journal=None):
    print(
        f"{GREEN}{emoji('📂')} {t('main.session_loaded', session=session_name)}{RESET}"
    )
    # «Ранее в кампании»: для длинных сессий — выжимка вместо сырых сообщений
    if len(history) >= 20 and (summary or journal):
        print(f"{CYAN}{emoji('📖')} {t('main.recap_title')}{RESET}")
        if summary:
            for line in summary.strip().splitlines()[:4]:
                line = line.strip()
                if line:
                    print(f"  {line[:200]}")
        if journal is not None:
            entries = getattr(journal, "entries", [])[-3:]
            for e in entries:
                text = re.sub(
                    r"\s+", " ", e.get("text", "") if isinstance(e, dict) else str(e)
                )
                print(f"  {YELLOW}•{RESET} {text[:150]}")
        print()
    elif summary:
        print(
            f"{CYAN}{t('main.memory_preview', text=summary[:120] + ('...' if len(summary) > 120 else ''))}{RESET}"
        )
    print(f"{YELLOW}{t('main.recent_events')}{RESET}")
    for m in history[-5:]:
        role = (
            f"{GREEN}{player_name}{RESET}"
            if m["role"] == "user"
            else f"{BLUE}DM{RESET}"
        )
        print(f"{role}: {highlight(m['content'])}")
    print()
    show_startup_hint()


def start_new_game(session_name, party, world=None):
    print(f"{GREEN}{t('main.new_session', session=session_name)}{RESET}")
    show_startup_hint()
    show_dm_status()

    print(f"{BLUE}DM{RESET}: ", end="", flush=True)

    character = party.active_character
    # Память для первого сообщения: состояние персонажа + мир
    # Стартовая локация известна сразу — карта не пустая с первого хода,
    # и модель с первого ответа привязывает события к таверне.
    if world is not None and not world.location:
        world.set_location(t("world.start_location"))
        world.add_fact(t("world.start_fact"))
    mem_parts = []
    char_block = character.prompt_block()
    if char_block:
        mem_parts.append(char_block)
    party_block = party.prompt_block()
    if party_block:
        mem_parts.append(party_block)
    if world is not None:
        world_block = world.prompt_block()
        if world_block:
            mem_parts.append(world_block)
    mem = "\n".join(mem_parts)
    history = [{"role": "user", "content": t("main.first_prompt_tavern")}]
    text, mdl, err, _ = ask_dm(
        history,
        mem,
        t("main.first_prompt_tavern"),
        commands.forced_model,
        commands.forced_detail_level,
        is_first=True,
        task_type=TaskType.NARRATIVE,
    )

    if not text:
        print(f"{RED}{err or t('main.models_unavailable')}{RESET}")
        print(f"{YELLOW}{t('main.switch_model_hint')}{RESET}")
        return None, ""

    history.append({"role": "assistant", "content": clean(text)})
    save_game_session(
        session_name,
        history,
        summary="",
        state=party.to_dict(),
        world=world.to_dict() if world is not None else None,
        rpg={},
    )
    slow_print(highlight(format_paragraphs(clean(text))))

    return history, ""


def safe_input(prompt=""):
    """Безопасный ввод с обработкой UTF-8 ошибок."""
    try:
        return input(prompt)
    except UnicodeDecodeError:
        # Пробуем прочитать как байты и декодировать с заменой ошибок
        import sys

        try:
            data = sys.stdin.buffer.readline()
            return data.decode("utf-8", errors="replace").rstrip("\n\r")
        except Exception:
            return ""
    except EOFError:
        raise
    except KeyboardInterrupt:
        raise


def roll_stat():
    """Классическая генерация характеристики: 4d6, худший кубик отбрасывается."""
    import random as _r

    rolls = sorted((_r.randint(1, 6) for _ in range(4)), reverse=True)
    return sum(rolls[:3])


def select_or_create_character():
    """Меню выбора/создания персонажа при первом запуске сессии."""
    from dndai.game.character import RACES, apply_race_bonuses, apply_class_kit

    print(f"{CYAN}{t('main.char_creation')}{RESET}")
    print(f"  {YELLOW}{t('main.char_name_prompt')}{RESET}")
    name = safe_input(f"{GREEN}{t('main.char_name_input')}{RESET} ").strip()
    if not name or name.lower() in ("готов", "skip", "нет", "ready"):
        name = "player"
    char_class = safe_input(
        f"{GREEN}{t('main.char_class_input')}{RESET} "
    ).strip() or t("main.char_default_class")
    races_hint = "/".join(sorted(RACES)[:3]) + "..."
    race = (
        safe_input(f"{GREEN}{t('main.char_race_input', examples=races_hint)}{RESET} ")
        .strip()
        .lower()
    )
    if not any(race == r or race in r for r in RACES):
        race = t("main.char_default_race").lower()
    try:
        hp = int(
            safe_input(f"{GREEN}{t('main.char_hp_input')}{RESET} ").strip() or "24"
        )
    except ValueError:
        hp = 24
    try:
        ac = int(
            safe_input(f"{GREEN}{t('main.char_ac_input')}{RESET} ").strip() or "15"
        )
    except ValueError:
        ac = 15
    # Характеристики генерируются по правилам D&D: 4d6, худший кубик вон.
    stats = {s: roll_stat() for s in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}
    stats, bonuses = apply_race_bonuses(stats, race)
    bonus_str = ", ".join(f"{k}+{v}" for k, v in bonuses.items()) if bonuses else ""
    if bonus_str:
        print(
            f"  {CYAN}{t('main.char_race_bonus', race=race.title(), bonuses=bonus_str)}{RESET}"
        )
    stats_str = ", ".join(f"{k}:{v}" for k, v in stats.items())
    print(f"  {CYAN}{t('main.char_stats_rolled', stats=stats_str)}{RESET}")
    con_mod = (stats["CON"] - 10) // 2
    hp = max(1, hp + con_mod)  # CON влияет на здоровье
    c = CharacterState(
        {
            "name": name,
            "class": char_class,
            "race": race,
            "hp": hp,
            "max_hp": hp,
            "ac": ac,
            "stats": stats,
            "inventory": [],
            "gold": 30,
            "xp": 0,
            "level": 1,
        }
    )
    # Стартовый набор класса: предметы, экипировка, заклинание
    kit_lines = apply_class_kit(c)
    if kit_lines:
        print(f"  {CYAN}{t('char.kit_given', items=', '.join(kit_lines))}{RESET}")
    print(f"{GREEN}{t('main.char_created', name=name, cls=char_class)}{RESET}")
    return c


def trim_memory_blocks(parts, max_chars):
    """Умная обрезка памяти: сохраняет целые блоки [СЕКЦИЯ]...[/СЕКЦИЯ].

    Приоритет: персонаж > враги > квесты/факты мира > остальное.
    Журнал и стиль жертвуются первыми; ни один блок не режется посередине,
    кроме случая, когда один блок сам больше лимита.
    """

    def priority(p):
        head = p[:60]
        if "СОСТОЯНИЕ ИГРОКА" in head:
            return 0
        if "ВРАГИ" in head:
            return 1
        if "ПАМЯТЬ СЮЖЕТА" in head or "КВЕСТЫ" in head:
            return 2
        if "ФАКТЫ" in head or "МИР]" in head:
            return 3
        if "ЭФФЕКТЫ" in head or "ЗАКЛИНАНИЯ" in head:
            return 4
        return 5  # журнал, макросы, время — жертвы

    kept = []
    total = 2  # запас на "\n".join + финальный маркер
    for p in sorted(parts, key=priority):
        cost = len(p) + (1 if kept else 0)
        if total + cost <= max_chars - 20:
            kept.append((priority(p), p))
            total += cost
        elif p.startswith("[СОСТОЯНИЕ ИГРОКА]") and len(p) > max_chars - 20:
            # критичный блок слишком велик — единственный случай внутреннего среза
            cut = max_chars - total - 30
            kept.append((-1, p[: max(100, cut)] + "\n...[обрезано]"))
            total = max_chars
    kept.sort(key=lambda x: x[0])
    out = "\n".join(p for _, p in kept)
    return out + "\n...[память сокращена до лимита]"


_SESSION_NAME_RE = re.compile(r"[\w\-. ]{1,64}", re.UNICODE)


def _parse_args(argv=None):
    """CLI-аргументы. --version обрабатывается до любой инициализации."""
    parser = argparse.ArgumentParser(
        prog="dndd",
        description="DnD AI Master — текстовый ИИ-мастер D&D в терминале",
    )
    parser.add_argument(
        "session",
        nargs="?",
        default="default",
        help="имя сессии (по умолчанию: default)",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"dndd {__version__}"
    )
    parser.add_argument(
        "--copy-prompts",
        action="store_true",
        help="скопировать промпты пакета в ~/.dnd_ai/prompts для правки",
    )
    return parser.parse_args(argv)


def _valid_session_name(name):
    """Имя сессии: до 64 символов, без разделителей пути и '..'."""
    if not _SESSION_NAME_RE.fullmatch(name):
        return False
    return ".." not in name and name.strip() != ""


def _copy_prompts():
    """Копирует промпты пакета в ~/.dnd_ai/prompts (существующие не трогает)."""
    src = package_prompts_dir()
    dst = app_home() / "prompts"
    try:
        dst.mkdir(parents=True, exist_ok=True)
        copied = 0
        for f in sorted(src.glob("*.txt")):
            target = dst / f.name
            if not target.exists():
                shutil.copy2(f, target)
                copied += 1
    except OSError as e:
        print(f"{RED}Не удалось скопировать промпты: {e}{RESET}")
        return 1
    print(f"{GREEN}Промпты: {dst} (новых файлов: {copied}){RESET}")
    print("Приложение читает этот каталог в приоритете над пакетным.")
    return 0


def main(argv=None):
    """Точка входа.

    Коды возврата: 0 — ОК, 1 — фатальная ошибка, 2 — нет ключей или
    недопустимое имя сессии, 130 — прерывание с клавиатуры.
    """
    args = _parse_args(argv)

    if args.copy_prompts:
        return _copy_prompts()

    show_logo()

    if not ensure_home():
        return 1
    migrated = migrate_legacy_data()
    if migrated:
        print(f"{CYAN}📦 Перенесено файлов: {migrated} → {DATA_DIR}{RESET}")

    setup_input_history()
    # Сигналы регистрируем явно в точке входа (не при импорте модулей)
    shutdown_handler.register_signals()

    if not SYSTEM_PROMPT_TEMPLATE:
        print(
            f"{YELLOW}⚠️  Промпт мастера не найден — проверьте каталог: "
            f"{get_prompts_dir()}{RESET}"
        )

    if not check_api_keys():
        return 2

    if not _valid_session_name(args.session):
        print(f"{RED}Недопустимое имя сессии: {args.session!r}{RESET}")
        print(
            f"{YELLOW}Разрешены буквы, цифры, пробел, дефис и точка "
            f"(до 64 символов).{RESET}"
        )
        return 2

    try:
        return _game(args.session) or 0
    except KeyboardInterrupt:
        info("Принудительное завершение")
        return 130
    except Exception as e:
        critical("Необработанная ошибка: %s", e, exc_info=True)
        print(f"{RED}{t('main.fatal_error', hint=e)}{RESET}")
        return 1


def _game(session_name):
    """Игровой цикл сессии (окружение проверено и создано в main())."""
    init_models()

    history, memory, summary, state_raw, world_raw, rpg_raw = load_game_session(
        session_name
    )
    party = Party(state_raw)
    # Если партия пуста — запускаем выбор/создание персонажа.
    # Флаг created_new: стартовый набор класса (kit_spells) выдаётся
    # ТОЛЬКО свежесозданному персонажу, иначе повторный вход в сессию
    # падал с NameError и дублировал заклинания.
    created_new_character = False
    if not party.chars:
        character = select_or_create_character()
        party.add(character)
        created_new_character = True
    world = WorldState(world_raw)
    spells = SpellBook(rpg_raw.get("spells", []))
    prog = Progression(rpg_raw.get("progression", {}))
    status = StatusEffects(rpg_raw.get("status", []))
    quests = Quests(rpg_raw.get("quests", {}))
    npcs = NPCs(rpg_raw.get("npcs", {}))
    timew = TimeWeather(rpg_raw.get("time", {}))
    journal = Journal(rpg_raw.get("journal", []))
    macros = Macros(rpg_raw.get("macros", {}))
    style = Style(rpg_raw.get("style", {}))
    enemies = Enemies(rpg_raw.get("enemies", []))
    reputation = Reputation(rpg_raw.get("reputation", {}))
    if created_new_character:
        for kit_spell in getattr(character, "kit_spells", []):
            name_, desc_, effect_, dc_, dmg_ = (list(kit_spell) + ["", "", 0, ""])[:5]
            spells.add(
                name_, desc=desc_ or desc_, effect=effect_, save_dc=dc_, dmg=dmg_
            )
    character = party.active_character
    # Уровень персонажа не должен отставать от прогрессии (лечит старые
    # сохранения: начисляет пропущенные HP за уровни)
    sync_with_progression(character, prog.level)
    player_name = get_player_name_from_history(history) or character.name or "player"
    if not character.name:
        character.name = player_name
    commands.PLAYER_NAME = character.name
    set_globals(
        commands.forced_model, commands.forced_detail_level, commands.PLAYER_NAME
    )

    # Собираем "память" для DM: вечный summary + состояние персонажа + мир
    memory_parts = []
    if summary:
        memory_parts.append(f"[ПАМЯТЬ СЮЖЕТА]\n{summary}\n[/ПАМЯТЬ СЮЖЕТА]")
    char_block = character.prompt_block()
    if char_block:
        memory_parts.append(char_block)
    party_block = party.prompt_block()
    if party_block:
        memory_parts.append(party_block)
    world_block = world.prompt_block()
    if world_block:
        memory_parts.append(world_block)
    # RPG-системы
    for blk in (
        spells.prompt_block(),
        prog.prompt_block(),
        status.prompt_block(),
        enemies.prompt_block(),
        reputation.prompt_block(),
        quests.prompt_block(),
        npcs.prompt_block(),
        timew.prompt_block(),
        journal.prompt_block(),
        style.prompt_block(),
    ):
        if blk:
            memory_parts.append(blk)
    memory = "\n".join(memory_parts)
    # Ограничиваем размер system-промпта: режем ПО БЛОКАМ [СЕКЦИЯ]...[/СЕКЦИЯ]
    # от наименее важных к наиболее, а не жёстким срезом посередине строки.
    MAX_MEMORY_CHARS = 6000
    if len(memory) > MAX_MEMORY_CHARS:
        memory = trim_memory_blocks(memory_parts, MAX_MEMORY_CHARS)

    if history:
        history, summary = compress_if_needed(history, session_name, character, summary)
        print_welcome(session_name, history, player_name, summary, journal=journal)
    else:
        history, summary = start_new_game(session_name, party, world=world)
        if history is None:
            return 1

    PROVIDER_COLORS = {
        "OpenRouter": CYAN,
        "Gemini": YELLOW,
        "Groq": GREEN,
        "Ollama": ORANGE,
        "Ollama-Server": ORANGE,
    }

    def dm_prefix(model_name):
        # model_name — ФАКТИЧЕСКАЯ модель последнего ответа
        # ("Provider:model" из api.openrouter.get_current_model()),
        # а не предположение.
        prov = ""
        if model_name:
            for pname in PROVIDER_COLORS:
                if pname.lower() in model_name.lower():
                    prov = pname
                    break
        col = PROVIDER_COLORS.get(prov, RESET)
        return f"{col}DM{RESET}"

    # Снимок сессии ДО начала игры (для отката к состоянию на входе)
    backup_session(session_name)

    quiet_mode = {"on": False}

    def persist():
        rpg_state = {
            "spells": spells.to_dict(),
            "progression": prog.to_dict(),
            "status": status.to_dict(),
            "quests": quests.to_dict(),
            "npcs": npcs.to_dict(),
            "time": timew.to_dict(),
            "journal": journal.to_dict(),
            "macros": macros.to_dict(),
            "style": style.to_dict(),
            "enemies": enemies.to_dict(),
            "reputation": reputation.to_dict(),
        }
        save_game_session(
            session_name,
            history,
            summary=summary,
            state=party.to_dict(),
            world=world.to_dict(),
            rpg=rpg_state,
        )

    try:
        while True:
            try:
                act = safe_input(f"{GREEN}{commands.PLAYER_NAME} >_{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                persist()
                shutdown_models()
                print()
                break

            if not act:
                continue

            # ── !перепиши: регенерация последнего ответа мастера ──
            redo = act.lower() in ("!перепиши", "!rewrite", "!заново")
            if redo:
                if history and history[-1]["role"] == "assistant":
                    history.pop()  # убираем неудачный ответ
                last_user = next(
                    (
                        m["content"]
                        for m in reversed(history)
                        if m.get("role") == "user"
                    ),
                    None,
                )
                if not last_user:
                    print(f"{YELLOW}{t('main.nothing_to_rewrite')}{RESET}")
                    continue
                act = last_user

            # Раскрываем макросы (команда = имя макроса)
            expanded = macros.expand(act)
            if expanded:
                act = expanded

            if act.lower() in ("выход", "exit", "quit", "/quit"):
                persist()
                shutdown_models()
                print(f"{GREEN}{t('main.session_saved')}{RESET}")
                break

            if re.search(r"^(/)?(очистить|сброс|clear|reset)$", act, re.IGNORECASE):
                clear_history_and_exit(session_name)
                shutdown_models()
                break

            # ── Диспетчеризация команд через commands/ ──
            # Текущий управляемый персонаж — активный в партии
            character = party.active_character
            commands.PLAYER_NAME = character.name if character.name else "player"
            # Ячейки заклинаний зависят от уровня/класса — пересчитываем каждый ход
            spells.set_slots(character.level, character.char_class)
            ctx = GameContext(
                character=character,
                world=world,
                spells=spells,
                prog=prog,
                status=status,
                quests=quests,
                npcs=npcs,
                timew=timew,
                journal=journal,
                macros=macros,
                style=style,
                session_name=session_name,
                persist=persist,
                rollback=lambda: rollback_session(session_name),
                quiet_mode=quiet_mode,
                history=history,
                summary=summary,
                player_name=commands.PLAYER_NAME,
                compress=compress_if_needed,
                shutdown=shutdown_models,
                party=party,
                enemies=enemies,
                reputation=reputation,
            )

            # Оригинальная реплика игрока (до rewrite боем/приказом) —
            # её и пишем в историю и журнал, технический мусор не попадает.
            original_act = act

            result = dispatch(act, ctx)

            # Команды (напр. /memory) могут сжать историю — забираем
            # изменения обратно в локальные переменные игрового цикла.
            history = ctx.history
            summary = ctx.summary

            if result is not None:
                if result.text:
                    print(result.text)
                if result.exit_loop:
                    if not result.skip_persist:
                        persist()
                    shutdown_models()
                    return
                if result.stop:
                    continue
                # команда подготовила act для мастера (спасбросок/бой/приказ)
                if result.rewrite_act:
                    if result.rewrite_act.startswith("__DM_ORDER__"):
                        order = result.rewrite_act[len("__DM_ORDER__") :]
                        history.append(
                            {
                                "role": "system",
                                "content": f"{t('meta.dm_order', cmd=order)}",
                            }
                        )
                        print(f"{dm_prefix(get_current_model())} ", end="", flush=True)
                        _printer = StreamingPrinter()
                        text, mdl, err, streamed = ask_dm(
                            history,
                            memory,
                            "",
                            commands.forced_model,
                            commands.forced_detail_level,
                            task_type=TaskType.NARRATIVE,
                            on_token=_printer.on_token if STREAM_MODE else None,
                        )
                        _printer.finish()
                        if not text:
                            print(f"{RED}{err or t('main.models_unavailable')}{RESET}")
                            if history and history[-1]["role"] == "system":
                                history.pop()
                            continue
                        if not _printer._printed:
                            slow_print(highlight(format_paragraphs(clean(text))))
                        persist()
                        continue
                    act = result.rewrite_act
                # иначе пропускаем act дальше к мастеру (без continue)

            # Бросок кубика — только если вся строка является dice-выражением
            # (2d6, d20, 1d20+5...), иначе обычный текст уходит мастеру как есть.
            m_roll = re.match(r"(?i)^\s*!?\s*(\d*d\d+(?:\s*[+-]\s*\d+)?)\s*$", act)
            if m_roll:
                expr = m_roll.group(1).replace(" ", "")
                dice, results = roll_dice(expr)
                if dice is not None:
                    act = (
                        f"{act} [МЕХАНИКА: брошен {expr}, итог = {dice}. "
                        f"Используй в повествовании именно этот результат, "
                        f"свой бросок не выполняй]"
                    )
                    print(f"{BLUE}{emoji('🎲')} {expr}: {dice}{RESET}")

            # В историю и журнал пишем оригинальную реплику игрока,
            # а не технический rewrite (например [Бой: ...]).
            if not redo:
                history.append({"role": "user", "content": original_act})
                archive_log(session_name, "user", original_act)

            # Автосжатие истории при накоплении сообщений (порог — компромисс
            # между частотой вызовов LLM и размером контекста).
            # Сообщение о сжатии печатает compress_if_needed.
            COMPRESS_THRESHOLD = 30
            if len(history) > COMPRESS_THRESHOLD:
                history, summary = compress_if_needed(
                    history, session_name, character, summary
                )

            print(f"{dm_prefix(get_current_model())} ", end="", flush=True)

            _printer = StreamingPrinter()
            text, mdl, err, streamed = ask_dm(
                history,
                memory,
                act,
                commands.forced_model,
                commands.forced_detail_level,
                is_first=False,
                task_type=TaskType.NARRATIVE,
                on_token=_printer.on_token if STREAM_MODE else None,
            )
            _printer.finish()

            if not text:
                # Gracefully handle when all providers fail
                print(f"{RED}{err or t('main.models_unavailable')}{RESET}")
                print(f"{YELLOW}{t('main.switch_model_hint')}{RESET}")
                history.pop()
                continue

            history.append({"role": "assistant", "content": clean(text)})
            archive_log(session_name, "assistant", clean(text))
            if not _printer._printed:
                slow_print(highlight(format_paragraphs(clean(text))))

            if t("main.name_change_marker") in text:
                match = re.search(t("main.name_change_pattern"), text)
                if match:
                    commands.PLAYER_NAME = match.group(1)

            # ── Авто-факты (16): извлекаем маркеры [[ФАКТ: ...]] из ответа ──
            fact_marks = re.findall(t("main.fact_marker_pattern"), text, re.IGNORECASE)
            new_facts = 0
            for fm in fact_marks:
                fact = fm.strip()
                if fact and fact not in world.facts:
                    world.facts.append(fact)
                    new_facts += 1
            if new_facts and not quiet_mode["on"]:
                print(f"{CYAN}{t('main.facts_recorded', n=new_facts)}{RESET}")

            # ── Награды от мастера: [[ЗОЛОТО: +25]] / [[ЗОЛОТО: -10]] ──
            gold_marks = re.findall(
                r"\[\[ЗОЛОТО:\s*([+-]?\d+)\]\]", text, re.IGNORECASE
            )
            for gm in gold_marks:
                try:
                    delta = int(gm)
                except ValueError:
                    continue
                character.gold = max(0, character.gold + delta)
                if not quiet_mode["on"]:
                    col = GREEN if delta >= 0 else RED
                    sign = f"+{delta}" if delta >= 0 else str(delta)
                    print(
                        f"{col}{emoji('💰')} "
                        f"{t('char.gold_changed', delta=sign, gold=character.gold)}{RESET}"
                    )

            # ── Журнал: краткая запись хода (18) ──
            summary_line = re.sub(r"\s+", " ", clean(text)).strip()
            if len(summary_line) > 180:
                summary_line = summary_line[:177] + "..."
            author = party.active_name if party.active_name else "player"
            journal.add(
                f"[{author}: {original_act}] -> {summary_line}",
                day=timew.day,
                part=timew._part(),
            )

            # ── Тик статус-эффектов (3): урон за ход ──
            dmg_total, dmg_parts = status.tick_damage()
            if dmg_total:
                character.hp = max(0, character.hp - dmg_total)
                if not quiet_mode["on"]:
                    print(
                        f"{RED}{t('main.effect_damage', dmg=dmg_total, parts=', '.join(dmg_parts), hp=character.hp, max_hp=character.max_hp)}{RESET}"
                    )
                if character.hp <= 0:
                    print(f"{RED}{t('main.you_died')}{RESET}")
            # ── Репутация от мастера: [[РЕПУТАЦИЯ: Фракция ±N]] ──
            rep_marks = re.findall(
                r"\[\[РЕПУТАЦИЯ:\s*([^+–\-0-9][^\]0-9]*?)\s*([+-]\d+)\s*\]\]",
                text,
                re.IGNORECASE,
            )
            for faction, delta in rep_marks:
                new_score = reputation.change(faction, int(delta))
                if new_score is not None and not quiet_mode["on"]:
                    col = GREEN if int(delta) >= 0 else RED
                    print(
                        f"{col}{emoji('🤝')} "
                        f"{t('rep.changed', faction=faction.strip().title(), delta=delta, score=new_score)}{RESET}"
                    )

            # ── Квесты от мастера: [[КВЕСТ: Название | описание]] ──
            quest_marks = re.findall(r"\[\[КВЕСТ:\s*(.+?)\]\]", text, re.IGNORECASE)
            for qm in quest_marks:
                title, _, qdesc = qm.partition("|")
                if quests.add(title.strip(), desc=qdesc.strip()):
                    if not quiet_mode["on"]:
                        print(
                            f"{CYAN}{emoji('📜')} "
                            f"{t('rpg.quest_added', title=title.strip())}{RESET}"
                        )

            expired = status.tick()
            if expired and not quiet_mode["on"]:
                print(
                    f"{YELLOW}{t('main.effect_expired', names=', '.join(expired))}{RESET}"
                )

            # ── Смертельные ранения: бросок смерти в конце хода при 0 HP ──
            if character.hp <= 0 and not character.death_saves["stabilized"]:
                outcome, roll = character.death_save_roll()
                if outcome == "rise":
                    print(
                        f"{GREEN}{emoji('🌟')} {t('combat.death_nat20', roll=roll)}{RESET}"
                    )
                elif outcome == "stabilize":
                    print(
                        f"{GREEN}{emoji('✚')} {t('combat.death_stabilized', roll=roll)}{RESET}"
                    )
                elif outcome == "dead":
                    print(f"{RED}{emoji('💀')} {t('main.you_died')}{RESET}")
                    persist()
                    break
                else:
                    s = character.death_saves
                    msg = t(
                        "combat.death_save_result",
                        roll=roll,
                        ok=s["successes"],
                        fail=s["failures"],
                    )
                    print(f"{RED}{emoji('☠')} {msg}{RESET}")

            persist()

    except (KeyboardInterrupt, SystemExit):
        # Сигнал/прерывание в произвольной точке — сохраняем сессию
        persist()
        raise

    except Exception as e:
        error(f"Критическая ошибка: {e}")
        persist()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
