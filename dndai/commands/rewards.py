"""Общие награды: синхронизация уровней персонажа с прогрессией.

Используется всеми источниками XP (бой, заклинания, квесты, команда !xp),
чтобы CharacterState.level никогда не отставал от Progression.level.
"""
from dndai.core.colors import GREEN, RESET
from dndai.core.text import emoji
from dndai.core.i18n import t


def sync_levels(ctx, leveled):
    """Поднимает персонажа до уровней из Progression (+HP, лечение).

    Возвращает строки сообщений о левел-апе."""
    from dndai.game.character import gain_level
    lines = []
    c = ctx.character
    for target in (leveled or []):
        while c.level < target:
            old_max = c.max_hp
            gain_level(c)
            lines.append(f"{GREEN}{emoji('🆙')} "
                         f"{t('rpg.level_up', level=c.level)}{RESET}")
            lines.append(f"{GREEN}  {t('rpg.hp_gain', amt=c.max_hp - old_max, hp=c.hp, max_hp=c.max_hp)}{RESET}")
    return lines
