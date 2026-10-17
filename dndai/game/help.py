#!/usr/bin/env python3
from dndai.core.colors import (
    BLUE,
    CYAN,
    GREEN,
    ORANGE,
    PURPLE,
    RED,
    RESET,
    YELLOW,
    colorize,
)
from dndai.core.i18n import t
from dndai.core.text import emoji


def show_color_legend():
    print(f"\n{YELLOW}{t('help.legend_title')}{RESET}")
    # Единая точка применения цвета — colors.colorize()
    for sample, color, key in (
        ("{{NPC}}", "cyan", "help.legend_npc"),
        ("<<Места>>", "yellow", "help.legend_loc"),
        ("[[Предметы]]", "orange", "help.legend_item"),
        ("__События__", "purple", "help.legend_event"),
        ("!!Эмоции!!", "green", "help.legend_emotion"),
    ):
        print(f"  {colorize(sample, color)} {t(key)}")
    print()


def _row(items):
    """Печатает группу команд одной строкой: cmd — desc · cmd — desc."""
    print("  " + f" {RESET}·{GREEN} ".join(items) + RESET)


def show_dm_help(full=False):
    """Компактная справка. Полная версия: /help всё"""
    print(f"{YELLOW}{t('help.title' if full else 'help.quick_title')}{RESET}")
    if not full:
        # ── Самое нужное, 4 строки ──
        print(f"{CYAN}{t('help.info_title')}{RESET}")
        _row(
            [
                f"/model авто{RESET} — {t('help.model_switch')}",
                f"детальнее/короче{RESET} — {t('help.detail_up')}/{t('help.detail_down')}",
            ]
        )
        _row(
            [
                f"!бой Моб КД [HP]{RESET} — {t('help.fight')}",
                f"!каст Закл [Цель]{RESET} — {t('help.cast')}",
            ]
        )
        _row(
            [
                f"!статус{RESET} — {t('help.char_status')}",
                f"!отдых{RESET} — {t('help.rest')}",
                f"!карта{RESET} — {t('help.map_show')}",
            ]
        )
        _row(
            [
                f"выход{RESET} — {t('help.quit')}",
                f"!перепиши{RESET} — {t('help.rewrite')}",
                f"!сводка{RESET} — {t('help.summary')}",
            ]
        )
        print(f"  {GREEN}/help всё{RESET} — {t('help.full_list')}")
        return

    # ── Полная версия ──
    print(
        f"  {GREEN}/model [провайдер[:модель]|auto]{RESET} — {t('help.model_switch')}"
    )
    print(f"  {GREEN}классы{RESET} — {t('help.classes')}")
    print(
        f"  {GREEN}детальнее / короче{RESET} — {t('help.detail_up')}/{t('help.detail_down')}"
    )
    print(f"  {GREEN}теперь меня зовут X{RESET} — {t('help.rename')}")
    print(f"  {GREEN}dm: <приказ>{RESET} — {t('help.dm_order')}")
    print()
    print(f"{CYAN}{t('help.info_title')}{RESET}")
    _row(
        [
            f"/models{RESET} — {t('help.models')}",
            f"/stats{RESET} — {t('help.stats')}",
            f"/history{RESET} — {t('help.history')}",
        ]
    )
    _row(
        [
            f"/colors{RESET} — {t('help.colors')}",
            f"красный|жёлтый|синий{RESET} — {t('help.categories')}",
            f"обнови память{RESET} — {t('help.memory')}",
        ]
    )
    _row(
        [
            f"/model{RESET} — {t('help.model_show')}",
            f"очистить / сброс{RESET} — {t('help.clear')}",
            f"выход / quit{RESET} — {t('help.quit')}",
        ]
    )
    print()
    print(f"{CYAN}{t('help.char_title')}{RESET}")
    _row(
        [
            f"!персонаж Имя,Класс,HP,КД{RESET} — {t('help.char_create')}",
            f"!статус{RESET} — {t('help.char_status')}",
        ]
    )
    _row(
        [
            f"!инвентарь{RESET} — {t('help.inv')}",
            f"!урон N{RESET}/{t('help.heal')}",
            f"!золото [+N|-N]{RESET} — {t('help.gold')}",
        ]
    )
    _row(
        [
            f"!спас STR 12{RESET} — {t('help.save')}",
            f"!кости 2d6{RESET} — {t('help.dice')}",
        ]
    )
    _row(
        [
            f"!бой Моб КД [HP]{RESET} — {t('help.fight')}",
            f"!атака Моб{RESET}",
            f"!враги{RESET}",
            f"!враг Имя HP КД{RESET}",
        ]
    )
    print(f"    {t('help.fight_ex')}")
    _row([f"!каст Закл [Цель]{RESET} — {t('help.cast')}", f"!ячейки{RESET}"])
    _row(
        [
            f"!отдых{RESET} — {t('help.rest')}",
            f"!перепиши{RESET} — {t('help.rewrite')}",
            f"!откат{RESET} — {t('help.rollback')}",
        ]
    )
    _row(
        [
            f"!надеть Меч{RESET} / !снять{RESET} — {t('help.equip')}",
            f"!купить Зелье{RESET} — {t('help.shop')}",
            f"!репутация{RESET} — {t('help.rep')}",
        ]
    )
    _row(
        [
            f"!сводка{RESET} — {t('help.summary')}",
            f"!хроника{RESET} — {t('help.chronicle')}",
        ]
    )
    print()
    print(f"{CYAN}{t('help.party_title')}{RESET}")
    _row(
        [
            f"!новый Имя,Класс,HP,КД{RESET} — {t('help.party_new')}",
            f"!партия{RESET} — {t('help.party_list')}",
            f"!играть Имя{RESET} — {t('help.party_switch')}",
        ]
    )
    _row(
        [
            f"!партия удалить Имя{RESET} — {t('help.party_remove')}",
        ]
    )
    print()
    print(f"{CYAN}{t('help.world_title')}{RESET}")
    _row(
        [
            f"!мир{RESET} — {t('help.world_show')}",
            f"!идти <<Локация>>{RESET} — {t('help.goto')}",
            f"!факт Текст{RESET} — {t('help.fact')}",
        ]
    )
    _row(
        [
            f"!голос Бармен тег{RESET} — {t('help.voice')}",
            f"!npc Имя | голос | заметка | отношение{RESET} — {t('help.npc_add')}",
        ]
    )
    print()
    print(f"{CYAN}{t('help.rpg_title')}{RESET}")
    _row(
        [
            f"!закл Имя: Описание | урон 3d6 | СЛ 13{RESET} — {t('help.spell_add')}",
            f"!xp N{RESET} — {t('help.xp')}",
        ]
    )
    _row(
        [
            f"!квест Имя: Описание{RESET} — {t('help.quest_add')}",
            f"!время +3{RESET} — {t('help.time_advance')}",
        ]
    )
    _row(
        [
            f"!статус-эффект Имя N{RESET} — {t('help.effect_add')}",
            f"!запись Текст{RESET} — {t('help.journal_add')}",
        ]
    )
    _row(
        [
            f"!макрос Имя: команда{RESET} — {t('help.macro_add')}",
            f"!тон мрачный{RESET} — {t('help.tone_set')}",
            f"!тихо вкл|выкл{RESET} — {t('help.quiet')}",
        ]
    )
    _row(
        [
            f"!карта{RESET} — {t('help.map_show')}",
            f"!проверка Текст{RESET} — {t('help.check')}",
        ]
    )
    print()
    show_color_legend()


def test_colors():
    print(f"{GREEN}{emoji('✅')} {t('help.test_green')}{RESET}")
    print(f"{BLUE}{emoji('✅')} {t('help.test_blue')}{RESET}")
    print(f"{RED}{emoji('✅')} {t('help.test_red')}{RESET}")
    print(f"{YELLOW}{emoji('✅')} {t('help.test_yellow')}{RESET}")
    print(f"{CYAN}{emoji('✅')} {t('help.test_cyan')}{RESET}")
    print(f"{ORANGE}{emoji('✅')} {t('help.test_orange')}{RESET}")
    print(f"{PURPLE}{emoji('✅')} {t('help.test_purple')}{RESET}")
    print()
    print(
        f"{GREEN}{emoji('🎲')} {YELLOW}D{RED}&{BLUE}D {CYAN}Cyberpunk {ORANGE}Master {PURPLE}Bot {RESET}{emoji('✅')}"
    )
    print()


def show_models():
    """Список провайдеров и моделей по категориям (tier-таблицы)."""
    from dndai.api.openrouter import BLACKLIST, is_blocked
    from dndai.core.config import PROVIDERS
    from dndai.core.task_types import (
        PROVIDER_MODELS_BY_TIER,
        TIER_PROVIDER_PREFERENCE,
        ModelTier,
    )
    from dndai.core.text import emoji

    active_names = {p["name"] for p in PROVIDERS}
    print(f"\n{CYAN}{emoji('🤖')} {t('help.providers_title')}{RESET}")
    tier_labels = [
        (ModelTier.SMART, "🔴", "cmd.mode_smart", RED),
        (ModelTier.BALANCED, "🟡", "cmd.mode_medium", YELLOW),
        (ModelTier.FAST, "🔵", "cmd.mode_fast", BLUE),
    ]
    for tier, icon, key, col in tier_labels:
        print(
            f"\n  {col}{icon} {t(key)}{RESET} "
            f"({t('meta.category_switch_hint', cats='красный|жёлтый|синий')})"
        )
        shown_any = False
        for provider_name in TIER_PROVIDER_PREFERENCE.get(tier, []):
            if provider_name not in active_names:
                continue
            models = PROVIDER_MODELS_BY_TIER.get(provider_name, {}).get(tier, [])
            if not models:
                continue
            parts = []
            for m in models[:4]:
                mark = (
                    f" {t('meta.blocked_mark')}" if is_blocked(provider_name, m) else ""
                )
                parts.append(m + mark)
            more = f" …+{len(models) - 4}" if len(models) > 4 else ""
            print(f"    {GREEN}{provider_name}{RESET}: {', '.join(parts)}{more}")
            shown_any = True
        if not shown_any:
            print(f"    {t('meta.no_models_for_tier')}")

    n_blocked = len(BLACKLIST)
    if n_blocked:
        print(f"\n{YELLOW}{t('meta.blacklist_size', n=n_blocked)}{RESET}")
