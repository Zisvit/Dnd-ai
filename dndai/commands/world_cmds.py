"""Команды мира, локаций, карты и NPC."""

import re

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.core.colors import CYAN, GREEN, RESET, YELLOW
from dndai.core.i18n import t
from dndai.game import economy
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


def _market_profile_line(profile, sources):
    """Строка профиля рынка с источником каждого поля."""
    parts = []
    if profile.get("size"):
        parts.append(
            f"{t('market.size_' + profile['size'])} "
            f"({t('market.src_' + (sources.get('size') or 'auto'))})"
        )
    if profile.get("wealth"):
        parts.append(
            t(
                "market.wealth_part",
                wealth=t("market.wealth_" + profile["wealth"]),
                src=t("market.src_" + (sources.get("wealth") or "auto")),
            )
        )
    if profile.get("tags"):
        tag_sources = sources.get("tags") or {}
        tags = ", ".join(
            f"{t('market.tag_' + tag)} ({t('market.src_' + tag_sources.get(tag, 'auto'))})"
            for tag in profile["tags"]
        )
        parts.append(t("market.tags_part", tags=tags))
    return ", ".join(parts) if parts else t("market.profile_neutral")


def _print_market(ctx: GameContext):
    """Печать рынка текущей локации: профиль, условия, покупка/скупка."""
    world = ctx.world
    location = world.location or "?"
    profile, sources = economy.profile_for(world, location)
    cond, matched = economy.conditions_factor(world)
    print(f"\n{CYAN}{t('market.title', loc=location)}{RESET}")
    print(f"  {_market_profile_line(profile, sources)}")
    if matched:
        conds = ", ".join(f"{label} {economy.fmt_mult(perm)}" for label, perm in matched)
        print(f"  {t('market.conditions_line', conds=conds, total=economy.fmt_mult(cond))}")
    else:
        print(f"  {t('market.conditions_none')}")
    print(f"  {t('market.prices_header')}")
    for name, buy, sell, over in economy.price_rows(world):
        mark = t("market.mark_dm") if over else ""
        print(f"    {name} — {buy} / {sell}{mark}")
    print(f"  {YELLOW}{t('market.hint')}{RESET}")


def market_command(act, ctx: GameContext):
    """`!рынок` — цены и профиль локации; настройка: тип/достаток/сброс."""
    text = act.strip()
    if re.match(r"(?i)!?\s*(?:рынок|market)\s*$", text):
        _print_market(ctx)
        return CommandResult.silent()
    m = re.match(
        r"(?i)!?\s*(?:рынок|market)\s+(тип|type|достаток|wealth|сброс|reset)\b\s*(.*)$",
        text,
    )
    if m:
        kind, value = m.group(1).lower(), (m.group(2) or "").strip()
        world = ctx.world
        location = world.location
        if not location:
            return CommandResult(f"{YELLOW}{t('market.no_location')}{RESET}")
        value = value.strip(" ,.;«»<>").lower()
        if kind in ("тип", "type"):
            size = economy.parse_size(value)
            if not size:
                return CommandResult(
                    f"{YELLOW}"
                    f"{t('market.unknown_value', value=value, options=t('market.size_options'))}"
                    f"{RESET}"
                )
            record = economy.ensure_market(world, location)
            record["size"] = size
            record.setdefault("src", {})["size"] = "manual"
            ctx.persist()
            label = t("market.size_" + size)
            return CommandResult(f"{GREEN}{t('market.type_set', loc=location, size=label)}{RESET}")
        if kind in ("достаток", "wealth"):
            wealth = economy.parse_wealth(value)
            if not wealth:
                return CommandResult(
                    f"{YELLOW}"
                    f"{t('market.unknown_value', value=value, options=t('market.wealth_options'))}"
                    f"{RESET}"
                )
            record = economy.ensure_market(world, location)
            record["wealth"] = wealth
            record.setdefault("src", {})["wealth"] = "manual"
            ctx.persist()
            label = t("market.wealth_" + wealth)
            return CommandResult(
                f"{GREEN}{t('market.wealth_set', loc=location, wealth=label)}{RESET}"
            )
        # сброс
        if economy.reset_market(world, location):
            ctx.persist()
            return CommandResult(f"{GREEN}{t('market.reset_done', loc=location)}{RESET}")
        return CommandResult(f"{YELLOW}{t('market.reset_none', loc=location)}{RESET}")
    if re.match(r"(?i)!\s*(?:рынок|market)\b", text):
        return CommandResult(f"{YELLOW}{t('market.hint')}{RESET}")
    return None
