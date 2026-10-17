"""Команды управления партией: переключение активного игрока,
добавление союзников, переименование."""

import re

from dndai.commands.context import GameContext
from dndai.commands.result import CommandResult
from dndai.game.character import parse_character_command
from dndai.core.colors import GREEN, YELLOW, CYAN, RESET

from dndai.core.i18n import t


def party_list(act, ctx: GameContext):
    if re.match(r"(?i)!?\s*(?:персонажи|партия|party)\s*$", act):
        if not ctx.party or not ctx.party.chars:
            return CommandResult(f"{YELLOW}{t('party.empty')}{RESET}")
        lines = [f"{CYAN}{t('party.list_title')}{RESET}"]
        for i, c in enumerate(ctx.party.chars):
            mark = " ▶" if i == ctx.party.active else ""
            member = t(
                "party.member",
                n=i + 1,
                name=c.name or "Безымянный",
                cls=c.char_class,
                level=c.level,
                hp=c.hp,
                max_hp=c.max_hp,
                mark=mark,
            )
            lines.append(f"  {member}")
        return CommandResult("\n".join(lines))
    return None


def party_switch(act, ctx: GameContext):
    m = re.match(r"(?i)!?\s*(?:играть|switch|игрок)\s+(.+)", act)
    if not m:
        return None
    if not ctx.party:
        return CommandResult(f"{YELLOW}{t('party.empty')}{RESET}")
    name = m.group(1).strip("{}").strip()
    c = ctx.party.switch(name)
    if c:
        ctx.persist()
        return CommandResult(
            f"{GREEN}{t('party.switched', name=c.name, cls=c.char_class)}{RESET}"
        )
    # Подсказка: кого вообще можно выбрать (Party.names())
    available = ", ".join(ctx.party.names())
    return CommandResult(
        f"{YELLOW}{t('party.not_found_named', name=name, list=available)}{RESET}"
    )


def party_new(act, ctx: GameContext):
    # !новый Имя, Класс, HP, КД  (через parse_character_command)
    if not act.lower().startswith("!новый") and not act.lower().startswith("!new"):
        return None
    if not ctx.party:
        return CommandResult(f"{YELLOW}{t('party.empty')}{RESET}")
    parts = act.split(None, 1)
    parsed = (
        parse_character_command("!персонаж " + parts[1]) if len(parts) > 1 else None
    )
    if parsed and parsed[0] == "create":
        new_char = parsed[1]
        if not new_char.name:
            new_char.name = "player"
        ctx.party.add(new_char)
        ctx.persist()
        return CommandResult(
            f"{GREEN}{t('party.added', name=new_char.name, cls=new_char.char_class)}{RESET}"
        )
    return CommandResult(f"{YELLOW}{t('party.add_fail')}{RESET}")


def party_rename(act, ctx: GameContext):
    m = re.match(r"(?i)!?\s*(?:переименовать|rename)\s+(\S+)", act)
    if not m:
        return None
    if not ctx.party:
        return CommandResult(f"{YELLOW}{t('party.empty')}{RESET}")
    new_name = m.group(1).strip("{}").strip()
    if ctx.party.rename_active(new_name):
        ctx.persist()
        return CommandResult(f"{GREEN}{t('party.renamed', name=new_name)}{RESET}")
    return CommandResult(f"{YELLOW}{t('party.rename_fail')}{RESET}")


def party_remove(act, ctx: GameContext):
    """`!партия удалить Имя` / `!party remove Name` — убрать союзника.

    Последнего персонажа удалить нельзя: без него некому играть.
    Использует Party.remove() и Party.names() для подсказки оставшихся."""
    m = re.match(
        r"(?i)!?\s*(?:партия\s+(?:удалить|удал|remove)|party\s+remove)\s+(.+)", act
    )
    if not m:
        return None
    if not ctx.party or not ctx.party.chars:
        return CommandResult(f"{YELLOW}{t('party.empty')}{RESET}")
    name = m.group(1).strip("{}").strip()
    if len(ctx.party.chars) <= 1:
        return CommandResult(
            f"{YELLOW}{t('party.remove_last', names=', '.join(ctx.party.names()))}{RESET}"
        )
    if ctx.party.remove(name):
        ctx.character = ctx.party.active_character
        ctx.persist()
        remaining = ", ".join(ctx.party.names())
        return CommandResult(
            f"{GREEN}{t('party.removed', name=name)}{RESET}\n"
            f"  {YELLOW}{t('party.now_playing', list=remaining)}{RESET}"
        )
    available = ", ".join(ctx.party.names())
    return CommandResult(
        f"{YELLOW}{t('party.not_found_named', name=name, list=available)}{RESET}"
    )
