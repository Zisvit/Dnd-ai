#!/usr/bin/env python3
"""Состояние мира: локация, установленные факты, голоса NPC.

Хранится в сессии как dict `world`. Бот видит его в системном промпте,
поэтому помнит, где находится игрок, что уже установлено, и кто как "говорит".
"""

import re

from dndai.core.colors import CYAN, GREEN, RESET, YELLOW
from dndai.core.i18n import t

# Голоса NPC: какой стиль "озвучки". Бот задаёт стиль в промпте,
# чтобы DM играл голос разных персонажей.
VOICE_TAGS = {
    "циничный": "говорит сухо, цинично, короткими фразами",
    "поэтичный": "говорит возвышенно, метафорами, плавно",
    "грубый": "говорит резко, командирским тоном",
    "детский": "говорит наивно, с удивлением",
    "учёный": "говорит с фактами, терминами, вдумчиво",
    "таинственный": "говорит загадками, недосказанно",
}


class WorldState:
    def __init__(self, data=None):
        d = data or {}
        self.location = d.get("location", "")
        self.visited = d.get("visited", [])
        self.facts = d.get("facts", [])
        self.npc_voices = d.get("npc_voices", {})
        # Карта: граф связей между локациями
        self.connections = d.get("connections", {})  # loc -> [connected_locs]
        # Экономика: явные записи рынков и динамические товары (v1.2)
        self.markets = d.get("markets", {})
        self.trade_goods = d.get("trade_goods", {})

    def to_dict(self):
        return {
            "location": self.location,
            "visited": self.visited,
            "facts": self.facts,
            "npc_voices": self.npc_voices,
            "connections": self.connections,
            "markets": self.markets,
            "trade_goods": self.trade_goods,
        }

    def connect(self, a, b):
        """Соединяет две локации в графе (двунаправленно)."""
        a = a.strip().strip("<>").strip()
        b = b.strip().strip("<>").strip()
        if not a or not b or a == b:
            return False
        self.connections.setdefault(a, [])
        self.connections.setdefault(b, [])
        if b not in self.connections[a]:
            self.connections[a].append(b)
        if a not in self.connections[b]:
            self.connections[b].append(a)
        return True

    def neighbors(self, loc=None):
        loc = loc or self.location
        return self.connections.get(loc, [])

    def prompt_block(self):
        lines = []
        if self.location:
            lines.append(f"[МИР] Текущая локация: <<{self.location}>>")
            if self.visited:
                lines.append(f"Посещено: {', '.join('<<'+v+'>>' for v in self.visited)}")
        if self.facts:
            facts_str = "; ".join(self.facts)
            lines.append(f"Установленные факты мира: {facts_str}")
        if self.npc_voices:
            voices = ", ".join(f"{{{{{k}}}}} = {v}" for k, v in self.npc_voices.items())
            lines.append(f"Голоса NPC: {voices}")
        if self.connections:
            lines.append("КАРТА связей: " + "; ".join(
                f"{k} ↔ {', '.join(v)}" for k, v in self.connections.items()))
        if lines:
            return "\n".join(lines)
        return ""

    def add_fact(self, fact):
        fact = fact.strip().rstrip(".!")
        if fact and fact not in self.facts:
            self.facts.append(fact)
            return True
        return False

    def set_location(self, loc):
        loc = loc.strip()
        if not loc:
            return
        if self.location and self.location not in self.visited:
            self.visited.append(self.location)
        self.location = loc
        if loc not in self.visited:
            self.visited.append(loc)

    def set_voice(self, npc, tag):
        if npc and tag in VOICE_TAGS:
            self.npc_voices[npc] = tag
            return True
        return False


def show_world(world: WorldState):
    print(f"\n{CYAN}{t('world.show_title')}{RESET}")
    if world.location:
        print(f"  {GREEN}{t('world.location')}{RESET} <<{world.location}>>")
    if world.visited:
        print(f"  {GREEN}{t('world.visited')}{RESET} {', '.join(world.visited)}")
    if world.facts:
        print(f"  {GREEN}{t('world.facts')}{RESET}")
        for f in world.facts:
            print(f"    • {f}")
    else:
        print(f"  {YELLOW}{t('world.facts_empty')}{RESET}")
    if world.npc_voices:
        print(f"  {GREEN}{t('world.voices')}{RESET}")
        for npc, tag in world.npc_voices.items():
            print(f"    {{{npc}}} → {VOICE_TAGS.get(tag, tag)}")
    else:
        print(f"  {YELLOW}{t('world.voices_empty')}{RESET}")


def show_map(world: WorldState):
    """Выводит граф локаций в виде дерева/списка."""
    print(f"\n{CYAN}{t('world.map_title')}{RESET}")
    if not world.connections and not world.visited:
        print(f"  {YELLOW}{t('world.map_empty')}{RESET}")
        return
    # Текущая позиция всегда видна, даже если карта ещё без связей
    if world.location:
        here = t('world.map_you_are_here')
        print(f"  {GREEN}► {here}: <<{world.location}>>{RESET}")
    # посещённые
    visited_rest = [v for v in (world.visited or []) if v != world.location]
    if visited_rest:
        print(f"  {GREEN}{t('world.map_visited')}{RESET} "
              f"{', '.join('<<'+v+'>>' for v in visited_rest)}")
    if world.connections:
        print(f"  {CYAN}{t('world.map_links')}{RESET}")
        for loc, neigh in world.connections.items():
            mark = "►" if loc == world.location else " "
            print(f"  {mark} {loc} ↔ {', '.join(neigh)}")


def parse_world_command(text):
    """Парсит команды мира. Возвращает (action, data) или None."""
    text = text.strip()

    if re.match(r'(?i)^!\s*мир', text):
        return ("show", None)

    if re.match(r'(?i)^!\s*карта', text):
        return ("map", None)

    m = re.match(r'(?i)!?\s*связь\s+(\S+)\s+(.+)', text)
    if m:
        a = m.group(1).strip("<>").strip()
        b = m.group(2).strip("<>").strip()
        return ("connect", (a, b))

    m = re.match(r'(?i)!?\s*идти\s+(.+)', text)
    if m:
        loc = m.group(1).strip().strip("<>").strip()
        return ("goto", loc)

    m = re.match(r'(?i)!?\s*локация\s+(.+)', text)
    if m:
        loc = m.group(1).strip().strip("<>").strip()
        return ("goto", loc)

    m = re.match(r'(?i)!?\s*факт\s+(.+)', text)
    if m:
        return ("fact", m.group(1).strip())

    m = re.match(r'(?i)!?\s*голос\s+(\S+)\s+(.+)', text)
    if m:
        npc = m.group(1).strip("{}").strip()
        tag = m.group(2).strip().lower()
        return ("voice", (npc, tag))

    return None
