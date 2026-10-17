"""Команды мира, локаций, карты и NPC."""

import re

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.core.colors import CYAN, GREEN, RESET, YELLOW
from dndai.core.i18n import t
from dndai.game import economy
from dndai.game.rpg import parse_npc_command
from dndai.game.world import (
    SCALE_LADDER,
    VOICE_TAGS,
    current_view_scale,
    parse_scale,
    parse_world_command,
    scale_choices,
    scale_display,
    show_map,
    show_map_all,
    show_world,
)


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
        target = data
        known = target in w.nodes or target in w.connections
        # `!идти` — один шаг: соседи ∪ родитель ∪ дети; новые точки растут деревом
        if known and w.location and target != w.location:
            allowed = w.move_options()
            if target not in allowed:
                moves = ", ".join(f"<<{o}>>" for o in allowed[:6])
                if len(allowed) > 6:
                    moves += f" … +{len(allowed) - 6}"
                if moves:
                    return CommandResult(
                        f"{YELLOW}"
                        f"{t('world.goto_blocked', target=target, list=moves)}"
                        f"{RESET}"
                    )
                return CommandResult(
                    f"{YELLOW}{t('world.goto_no_exits', target=target)}{RESET}"
                )
        if not known:
            w.auto_parent(target, w.location)
        w.set_location(target)
        w.map_view = None  # обзор сбрасывается на уровень новой локации
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
    if action == "place":
        a, b = data
        if w.set_parent(a, b):
            ctx.persist()
            label = scale_display(parse_scale(w.scale_of(a))) or "—"
            return CommandResult(
                f"{GREEN}{t('world.place_set', a=a, b=b, scale=label)}{RESET}"
            )
        return CommandResult(f"{YELLOW}{t('world.place_cycle', a=a, b=b)}{RESET}")
    if action == "place_level":
        a, label = data
        scale = parse_scale(label)
        if w.set_scale(a, scale):
            ctx.persist()
            return CommandResult(
                f"{GREEN}"
                f"{t('world.place_level_set', a=a, scale=scale_display(scale))}"
                f"{RESET}"
            )
        return CommandResult(f"{YELLOW}{t('world.place_bad')}{RESET}")
    if action == "connect":
        a, b = data
        w.connect(a, b)
        ctx.persist()
        return CommandResult(f"{GREEN}{t('world.map_linked', a=a, b=b)}{RESET}")
    return None


def _map_zoom(ctx: GameContext, step: int):
    """Шаг обзора карты: ±1 по лестнице уровней."""

    w = ctx.world
    if w.zoom_map(step):
        ctx.persist()
        show_map(w)
        return CommandResult.silent()
    cur = current_view_scale(w)
    key = "world.map_zoom_edge" if cur in SCALE_LADDER else "world.map_zoom_none"
    return CommandResult(f"{YELLOW}{t(key)}{RESET}")


def map_show(act, ctx: GameContext):
    m = re.match(r"(?i)!?\s*(?:карта|map)(?:\s+(.*))?\s*$", act)
    if not m:
        return None
    arg = (m.group(1) or "").strip().lower()
    w = ctx.world
    if not arg:
        show_map(w)
        return CommandResult.silent()
    if arg in ("вверх", "up", "+"):
        return _map_zoom(ctx, 1)
    if arg in ("вниз", "down", "-"):
        return _map_zoom(ctx, -1)
    if arg in ("всё", "все", "all"):
        show_map_all(w)
        return CommandResult.silent()
    scale = parse_scale(arg)
    if scale in SCALE_LADDER:
        w.map_view = scale
        ctx.persist()
        show_map(w)
        return CommandResult.silent()
    return CommandResult(
        f"{YELLOW}"
        f"{t('world.map_level_unknown', value=arg, list=scale_choices())}"
        f"{RESET}"
    )


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
