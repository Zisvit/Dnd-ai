"""Команды мира, локаций, карты и NPC."""

import re

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.core.colors import CYAN, GREEN, RESET, YELLOW
from dndai.core.i18n import t
from dndai.game.rpg import parse_npc_command
from dndai.game.world import VOICE_TAGS, parse_world_command, show_map, show_world


def npc_command(act, ctx: GameContext):
    # Добавление (позиционное: имя | голос | заметка | отношение)
    parsed = parse_npc_command(act)
    if parsed:
        action, data = parsed
        if action == "npc_add":
            name, voice, note, relation = data
            if ctx.npcs.add(name, voice, note, relation):
                ctx.persist()
                return CommandResult(f"{GREEN}{t('world.npc_added', name=name)}{RESET}")
            return CommandResult(f"{YELLOW}{t('world.npc_add_fail')}{RESET}")
        return None

    # Удаление
    m_del = re.match(r"(?i)!?\s*npc\s+(?:удал(?:ить)?|del|rm)\s+(\S+)", act)
    if m_del:
        if ctx.npcs.remove(m_del.group(1)):
            ctx.persist()
            return CommandResult(f"{GREEN}{t('world.npc_removed')}{RESET}")
        return CommandResult(f"{YELLOW}{t('world.npc_not_found')}{RESET}")

    # Показ
    if re.match(r"(?i)!?\s*npc\s*$", act):
        ctx.npcs.show()
        return CommandResult.silent()
    return None


def world_command(act, ctx: GameContext):
    parsed = parse_world_command(act)
    if not parsed:
        return None
    action, data = parsed
    w = ctx.world
    if action == "show":
        show_world(w)
        return CommandResult.silent()
    if action == "goto":
        w.set_location(data)
        ctx.timew.advance(1)
        ctx.persist()
        outs = w.neighbors()  # пути из текущей локации (граф карты)
        exits = (
            f" {t('world.exits_from', list=', '.join('<<' + o + '>>' for o in outs))}"
            if outs
            else ""
        )
        return CommandResult(
            f"{CYAN}{t('world.location_changed', loc=w.location)}{exits}{RESET}"
        )
    if action == "fact":
        if w.add_fact(data):
            ctx.persist()
            return CommandResult(f"{GREEN}{t('world.fact_added', fact=data)}{RESET}")
        return CommandResult(f"{YELLOW}{t('world.fact_exists')}{RESET}")
    if action == "voice":
        npc, tag = data
        if w.set_voice(npc, tag):
            ctx.persist()
            return CommandResult(
                f"{GREEN}{t('world.voice_set', npc=npc, tag=tag)}{RESET}"
            )
        voices = ", ".join(VOICE_TAGS.keys())
        return CommandResult(f"{YELLOW}{t('world.voice_unknown', list=voices)}{RESET}")
    if action == "connect":
        a, b = data
        w.connect(a, b)
        ctx.persist()
        return CommandResult(f"{GREEN}{t('world.map_linked', a=a, b=b)}{RESET}")
    return None


def map_show(act, ctx: GameContext):
    if re.match(r"(?i)!?\s*(?:карта|map)\s*$", act):
        show_map(ctx.world)
        return CommandResult.silent()
    return None


def map_connect(act, ctx: GameContext):
    m = re.match(r"(?i)!?\s*связь\s+<<(.+?)>>\s+<<(.+?)>>", act)
    if m:
        a, b = m.group(1).strip(), m.group(2).strip()
        ctx.world.connect(a, b)
        ctx.persist()
        return CommandResult(f"{GREEN}{t('world.map_linked', a=a, b=b)}{RESET}")
    return None
