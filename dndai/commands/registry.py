"""Реестр команд и диспетчер.

dispatch(act, ctx) перебирает обработчики в заданном порядке, вызывает
первый совпавший и возвращает CommandResult (или None, если ни один
обработчик не среагировал — значит, это обычная реплика для мастера).

Порядок важен:
  1. мета-команды (помощь, откат, эмодзи, кости, история и т.п.)
  2. NPC — ДО parse_world_command, иначе !npc перехватывается миром
  3. команды мира (локации, факты, голоса, карта, связи)
  4. персонаж (создание/статус/урон/инвентарь)
  5. RPG-системы (закл, xp, квесты, время, макросы, тон, проверка...)
  6. бой/спасбросок — переписывают act и пропускают дальше к мастеру
"""

from dndai.commands.character_cmds import (
    character_create,
    character_modify,
    character_status,
    equip_command,
    gold_command,
    inventory_show,
    shop_command,
)
from dndai.commands.combat_cmds import (
    cast_command,
    fight_command,
    save_command,
    slots_command,
)
from dndai.commands.meta_cmds import (
    category_command,
    chronicle_command,
    classes_command,
    colors_command,
    detail_command,
    dice_command,
    dm_command,
    emoji_command,
    help_command,
    history_command,
    lang_command,
    memory_command,
    model_command,
    models_command,
    rollback_command,
    stats_command,
    summary_command,
)
from dndai.commands.party_cmds import (
    party_list,
    party_new,
    party_remove,
    party_rename,
    party_switch,
)
from dndai.commands.rpg_cmds import (
    check_command,
    enemy_add_command,
    journal_command,
    macro_command,
    quest_command,
    quiet_command,
    reputation_command,
    rest_command,
    spell_command,
    stabilize_command,
    status_command,
    style_command,
    time_command,
    weather_command,
    xp_command,
)
from dndai.commands.world_cmds import map_connect, map_show, npc_command, world_command

# Порядок имеет значение (см. docstring)
HANDLERS = [
    # мета
    help_command,
    colors_command,
    history_command,
    stats_command,
    memory_command,
    models_command,
    emoji_command,
    dice_command,
    rollback_command,
    dm_command,
    lang_command,
    classes_command,
    model_command,
    category_command,
    detail_command,
    summary_command,
    chronicle_command,
    # партия (до !персонаж, т.к. !персонажи начинается как !персонаж)
    party_list,
    party_switch,
    party_new,
    party_rename,
    party_remove,
    # npc до мира
    npc_command,
    # мир
    world_command,
    map_show,
    map_connect,
    # персонаж
    character_create,
    character_status,
    character_modify,
    inventory_show,
    equip_command,
    gold_command,
    shop_command,
    # rpg
    spell_command,
    xp_command,
    status_command,
    quest_command,
    time_command,
    weather_command,
    journal_command,
    macro_command,
    style_command,
    quiet_command,
    check_command,
    rest_command,
    reputation_command,
    # бой (переписывает act, не stop)
    save_command,
    fight_command,
    enemy_add_command,
    cast_command,
    slots_command,
    # умирающий персонаж
    stabilize_command,
]


def dispatch(act, ctx):
    """Возвращает CommandResult или None (нет совпадений)."""
    for handler in HANDLERS:
        result = handler(act, ctx)
        if result is not None:
            return result
    return None
