"""Мета-команды: справка, цвета, история, статистика, память,
модели, категории, детализация, прямой приказ мастеру, эмодзи,
бросок костей, откат сессии, язык."""

import re

import dndai.game.commands as commands_module
from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.core.colors import BLUE, CYAN, GREEN, ORANGE, RED, RESET, YELLOW
from dndai.core.i18n import set_lang, t
from dndai.core.text import emoji, set_emoji_enabled

# Предопределённые архетипы классов для подсказки
CLASS_ARCHETYPES = {
    "воин": "Ближний бой, броня, выносливость. Танк и дамагер.",
    "маг": "Заклинания, урон площадью, контроль. Стеклянная пушка.",
    "разбойник": "Скрытность, криты, замки, яды. Скаутер и дамагер.",
    "жрец": "Лечение, баффы, нежить. Поддержка и танк.",
    "паладин": "Ближний бой, аурки, лечение себя. Танк/саппорт.",
    "друид": "Превращения, природа, лечение. Универсал.",
    "бард": "Баффы, контроль, соц. интеракции. Саппорт/фейс.",
    "варлок": "Пакты, eldritch blast, утилиты. Дамагер/утилити.",
    "чародей": "Метамагия, врожденная магия. Бурст дамагер.",
    "монах": "Ки, скорость, станы. Мобильный дамагер/танк.",
    "следопыт": "Выживание, фаворит врага, дальний бой. Скаутер.",
    "инженер": "Гаджеты, турели, взрывчатка. Утилити/контроль.",
    "хакер": "Киберпространство, дроны, инфо. Саппорт/рекон.",
    "стрит-самурай": "Импланты, рефлексы, ближний бой. Кибер-танк.",
    "техношаман": "Техно-магия, духи машин. Гибрид маг/инженер.",
}


def classes_command(act, ctx: GameContext):
    """Показывает список доступных архетипов классов."""
    # Матчим слово целиком, чтобы не ловить обычную речь («Классная погода!»)
    if not re.match(
        r"(?i)!?\s*(?:классы|класс|архетипы|архетип|classes?|archetypes?)\s*[?.!]*\s*$",
        act.strip(),
    ):
        return None

    lines = [f"{CYAN}{emoji('📋')} {t('meta.classes_title')}{RESET}"]
    lines.append(f"  {YELLOW}{t('meta.classes_any_note')}{RESET}")
    lines.append("")
    for name, desc in CLASS_ARCHETYPES.items():
        lines.append(f"  {GREEN}{name}{RESET} — {desc}")
    lines.append("")
    lines.append(f"  {YELLOW}{t('meta.classes_hint_create')}{RESET}")
    return CommandResult("\n".join(lines))


def chronicle_command(act, ctx: GameContext):
    """`!хроника` — экспорт истории сессии в Markdown-файл."""
    if not re.match(r"(?i)!?\s*(?:хроника|chronicle|летопись)\s*$", act):
        return None
    from dndai.game.session import export_chronicle

    path = export_chronicle(
        ctx.session_name, ctx.history, player_name=ctx.player_name, summary=ctx.summary
    )
    return CommandResult(
        f"{GREEN}{emoji('📖')} {t('meta.chronicle_saved', path=path)}{RESET}"
    )


def summary_command(act, ctx: GameContext):
    """`!сводка` — вся игровая ситуация одной панелью."""
    if not re.match(r"(?i)!?\s*(?:сводка|summary|панель|обзор)\s*$", act):
        return None
    c = ctx.character
    L = []

    def bar(cur, mx, width=20, fill="█", empty="░"):
        n = round(width * max(0, cur) / max(1, mx))
        return fill * n + empty * (width - n)

    # Персонаж
    hp_col = RED if c.hp <= c.max_hp * 0.3 else GREEN
    hp_bar = f"{hp_col}{bar(c.hp, c.max_hp)}{RESET}"
    xp = getattr(ctx.prog, "xp", 0)
    L.append(f"{CYAN}{'─' * 34}{RESET}")
    L.append(
        f"{GREEN}{c.name or 'player'}{RESET} · {c.char_class} "
        f"{t('rpg.level_short', level=c.level)} · XP {xp}"
    )
    L.append(
        f"  {t('char.hp')} {hp_col}{c.hp}/{c.max_hp}{RESET} {hp_bar}"
        f"   КД {c.ac + c.equip_ac_bonus()}"
    )
    L.append(
        f"  💰 {ORANGE}{c.gold}{RESET}   "
        f"✨ {t('rpg.slots_left', left=ctx.spells.slots_left, max=ctx.spells.slots_max) if ctx.spells.slots_max else '—'}"
    )
    eq = [f"{k}:{v}" for k, v in c.equipped.items() if v]
    if eq:
        L.append(f"  🗡 {' · '.join(eq)}")
    # Эффекты
    if ctx.status.effects:
        effs = ", ".join(f"{e['name']} ({e['rounds']})" for e in ctx.status.effects)
        L.append(f"  🔮 {effs}")

    # Враги
    if ctx.enemies is not None and len(ctx.enemies):
        L.append(f"{RED}{t('combat.enemies_title')}{RESET}")
        for e in ctx.enemies.attack_order():
            filled = round(10 * e["hp"] / e["max_hp"])
            b = "█" * filled + "░" * (10 - filled)
            L.append(f"  • {e['name']} {e['hp']}/{e['max_hp']} {b}")

    # Квесты
    if ctx.quests.active:
        L.append(f"{YELLOW}{emoji('📜')} {t('help.quest_add')}:{RESET}")
        for q in ctx.quests.active[:5]:
            L.append(f"  ☐ {q['title']}")

    # Мир и время
    if ctx.world is not None:
        loc = f" <<{ctx.world.location}>>" if ctx.world.location else ""
        if loc:
            L.append(f"  📍{loc}")
    if ctx.timew is not None:
        part = ctx.timew._part()
        L.append(
            f"  ⏰ {t('rpg.day_n', day=ctx.timew.day)}, "
            f"{ctx.timew.hour:02d}:00 ({part}) · {ctx.timew.weather}"
        )
    L.append(f"{CYAN}{'─' * 34}{RESET}")
    return CommandResult("\n".join(L))


def help_command(act, ctx: GameContext):
    low = act.lower().strip()
    if low in ("/help", "помощь", "хелп", "help"):
        from dndai.game.help import show_dm_help

        show_dm_help()
        return CommandResult.silent()
    if re.match(r"(?i)^/help\s+(вс[её]|full|all)\s*$", low) or low in (
        "помощь всё",
        "полная справка",
    ):
        from dndai.game.help import show_dm_help

        show_dm_help(full=True)
        return CommandResult.silent()
    return None


def colors_command(act, ctx: GameContext):
    if act.lower() in ("/colors", "test colors", "тест цветов"):
        from dndai.game.help import test_colors

        test_colors()
        return CommandResult.silent()
    if act.lower() in (
        "/colors-legend",
        "цвета",
        "цветовая легенда",
        "colors",
        "color legend",
    ):
        from dndai.game.help import show_color_legend

        show_color_legend()
        return CommandResult.silent()
    return None


def history_command(act, ctx: GameContext):
    if act.lower() in ("история", "/history", "history"):
        from dndai.game.session import show_history

        show_history(ctx.history, ctx.player_name)
        return CommandResult.silent()
    return None


def stats_command(act, ctx: GameContext):
    low = act.lower().strip()
    if low in ("/stats", "статистика", "лимиты", "stats"):
        from dndai.game.stats import show_stats

        show_stats()
        return CommandResult.silent()
    # Сброс счётчиков: /stats сброс | статистика сброс | /stats reset
    if low in (
        "/stats сброс",
        "статистика сброс",
        "/stats reset",
        "stats reset",
        "/stats сбросить",
    ):
        from dndai.game.stats import reset_stats

        reset_stats()
        return CommandResult(f"{GREEN}{emoji('🧮')} {t('stats.reset_ok')}{RESET}")
    return None


def memory_command(act, ctx: GameContext):
    if act.lower() in ("обнови память", "update memory", "/memory", "/память"):
        ctx.history, ctx.summary = ctx.compress(
            ctx.history, ctx.session_name, ctx.character, ctx.summary
        )
        ctx.persist()
        return CommandResult(f"{CYAN}{t('meta.memory_updated')}{RESET}")
    return None


CATEGORY_WORDS = {
    "красный": "red",
    "red": "red",
    "жёлтый": "yellow",
    "желтый": "yellow",
    "yellow": "yellow",
    "синий": "blue",
    "blue": "blue",
}


def category_command(act, ctx: GameContext):
    """`красный` / `жёлтый` / `синий` — переключение категории моделей
    (умные / средние / быстрые). См. TIER_FOR_COLOR в task_types."""
    word = act.lower().strip()
    if word not in CATEGORY_WORDS:
        return None
    color = CATEGORY_WORDS[word]
    commands_module.forced_model = color
    key = {
        "red": "cmd.mode_smart",
        "yellow": "cmd.mode_medium",
        "blue": "cmd.mode_fast",
    }[color]
    return CommandResult(
        f"{GREEN}{emoji('🎚')} {t('meta.category_set', label=t(key))}{RESET}"
    )


def detail_command(act, ctx: GameContext):
    """`детальнее` / `короче` — уровень детализации ответов мастера."""
    low = act.lower().strip()
    up = low in ("детальнее", "подробнее", "more detail")
    down = low in ("короче", "кратче", "less detail")
    if not up and not down:
        return None
    if up:
        commands_module.forced_detail_level = min(
            2, commands_module.forced_detail_level + 1
        )
    else:
        commands_module.forced_detail_level = max(
            0, commands_module.forced_detail_level - 1
        )
    lvl = commands_module.forced_detail_level
    stars = "★" * lvl if lvl else t("cmd.detail_custom")
    return CommandResult(
        f"{GREEN}{emoji('📝')} {t('meta.detail_now', level=stars)}{RESET}"
    )


def models_command(act, ctx: GameContext):
    if act.lower() in ("/models", "модели", "показать модели", "models"):
        from dndai.game.help import show_models

        show_models()
        return CommandResult.silent()
    return None


def dm_command(act, ctx: GameContext):
    m = re.match(r"(?i)(?:(?:dm|дм)(?::|\s+|$))(.*)$", act)
    if not m:
        return None
    cmd = m.group(1).strip()
    if not cmd:
        return CommandResult.silent()
    return CommandResult(
        f"{YELLOW}{t('meta.dm_order', cmd=cmd)}{RESET}",
        stop=False,
        rewrite_act=f"__DM_ORDER__{cmd}",
    )


def emoji_command(act, ctx: GameContext):
    m = re.match(r"(?i)!?\s*(?:эмодзи|emoji)\s+(вкл|on|выкл|off)", act)
    if m:
        on = m.group(1).lower() in ("вкл", "on")
        set_emoji_enabled(on)
        key = "meta.emoji_on" if on else "meta.emoji_off"
        return CommandResult(f"{GREEN}{emoji('✅')} {t(key)}{RESET}")
    return None


def dice_command(act, ctx: GameContext):
    m = re.match(r"(?i)!?\s*(?:кости|dice)\s+(\d+d\d+(?:[+\-]\d+)?)", act)
    if m:
        from dndai.core.dice import roll_dice

        total, detail = roll_dice(m.group(1))
        return CommandResult(
            f"{BLUE}{t('meta.dice_roll', expr=m.group(1), detail=detail, total=total)}{RESET}"
        )
    return None


def rollback_command(act, ctx: GameContext):
    if act.lower() in ("!откат", "!rollback", "!undo"):
        if ctx.rollback():
            return CommandResult(
                f"{GREEN}{emoji('↩️')} {t('meta.rollback_ok', session=ctx.session_name)}{RESET}",
                exit_loop=True,
                skip_persist=True,
            )
        return CommandResult(f"{YELLOW}{t('meta.no_backup')}{RESET}")
    return None


def lang_command(act, ctx: GameContext):
    m = re.match(
        r"(?i)!?\s*(?:язык|lang)\s+(ru|en|русский|английский|russian|english)", act
    )
    if m:
        code = m.group(1).lower()
        if code in ("русский", "russian"):
            code = "ru"
        elif code in ("английский", "english"):
            code = "en"
        set_lang(code)
        return CommandResult(f"{GREEN}{t('lang.switched')}{RESET}")
    return None


def model_command(act, ctx: GameContext):
    """Переключение модели/провайдера: /model ollama, /model groq,
    /model auto, /model <provider[:model]>, /model (показать текущую)"""
    import dndai.game.commands as commands_module
    from dndai.api.openrouter import get_current_model, set_current_model
    from dndai.core.config import PROVIDERS

    m = re.match(r"(?i)^(?:/model|/модель)(?:\s+(.+))?$", act.strip())
    if not m:
        return None

    arg = m.group(1).strip().lower() if m.group(1) else ""

    # Если аргументов нет - показываем текущую модель
    if not arg:
        current = get_current_model()
        if current:
            return CommandResult(
                f"{GREEN}{emoji('🤖')} {t('meta.current_model')}: "
                f"{CYAN}{current}{RESET}"
            )
        return CommandResult(f"{YELLOW}{t('meta.model_none_auto')}{RESET}")

    # Сброс к авто (также снимаем игровую категорию)
    if arg in ("auto", "авто", "автомат", "default"):
        commands_module.forced_model = None
        return CommandResult(f"{GREEN}{t('meta.model_auto')}{RESET}")

    # Парсим provider[:model]
    parts = arg.split(":", 1)
    provider_name = parts[0].strip()
    model_name = parts[1].strip() if len(parts) > 1 else None

    # Маппинг алиасов
    provider_aliases = {
        "ollama": "Ollama-Server",
        "оллома": "Ollama-Server",
        "groq": "Groq",
        "грок": "Groq",
        "gemini": "Gemini",
        "джемини": "Gemini",
        "openrouter": "OpenRouter",
        "опенроутер": "OpenRouter",
    }

    provider_name = provider_aliases.get(provider_name, provider_name)

    # Ищем провайдера
    provider = next(
        (p for p in PROVIDERS if p["name"].lower() == provider_name.lower()), None
    )
    if not provider:
        available = ", ".join([p["name"] for p in PROVIDERS])
        return CommandResult(
            f"{RED}{emoji('❌')} {t('meta.provider_not_found', list=available)}{RESET}"
        )

    # Проверяем доступность
    if not (provider.get("api_key") or provider["name"] in ("Ollama", "Ollama-Server")):
        return CommandResult(
            f"{YELLOW}{emoji('⚠️')} {t('meta.provider_unavailable', name=provider['name'])}{RESET}"
        )

    # Определяем модель
    model_name_final = None
    if model_name:
        from dndai.api.openrouter import _get_models_for_tier
        from dndai.core.task_types import ModelTier

        known = set(provider.get("models", []))
        for tier in (ModelTier.FAST, ModelTier.BALANCED, ModelTier.SMART):
            known.update(_get_models_for_tier(provider["name"], tier))
        if model_name in known:
            model_name_final = model_name
        else:
            hint = ", ".join(sorted(known)[:5]) or "—"
            return CommandResult(
                f"{YELLOW}{emoji('⚠️')} {t('meta.model_unavailable_at', model=model_name, provider=provider['name'], list=hint)}{RESET}"
            )
    else:
        # Берём первую предпочтительную модель для NARRATIVE (BALANCED tier)
        from dndai.api.openrouter import _get_models_for_tier
        from dndai.core.task_types import ModelTier

        models = _get_models_for_tier(provider["name"], ModelTier.BALANCED)
        if models:
            model_name_final = models[0]
        elif provider.get("models"):
            model_name_final = provider["models"][0]

    if not model_name_final:
        return CommandResult(
            f"{RED}{emoji('❌')} {t('meta.model_switch_failed', provider=provider['name'])}{RESET}"
        )

    # Устанавливаем форсированную модель И факт текущей модели
    commands_module.forced_model = model_name_final
    full = f"{provider['name']}:{model_name_final}"
    set_current_model(full)

    return CommandResult(
        f"{GREEN}{emoji('✅')} {t('meta.model_switched', model=full)}{RESET}"
    )
