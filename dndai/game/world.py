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

# Карта v1: лестница уровней от мелкого к крупному. Узлы хранят уровень
# строкой — вставка/перестановка уровней не ломает старые сессии.
SCALE_LADDER = [
    "строение",
    "квартал",
    "город",
    "страна",
    "планета",
    "система",
    "галактика",
]

# RU/EN-слова уровней → каноническая метка (строка из SCALE_LADDER).
SCALE_ALIASES = {
    "строение": "строение",
    "building": "строение",
    "квартал": "квартал",
    "quarter": "квартал",
    "город": "город",
    "city": "город",
    "страна": "страна",
    "country": "страна",
    "планета": "планета",
    "planet": "планета",
    "система": "система",
    "system": "система",
    "галактика": "галактика",
    "galaxy": "галактика",
}

# Ключи локализации названий уровней (хранение — канон, показ — перевод).
SCALE_I18N = {
    "строение": "world.scale_building",
    "квартал": "world.scale_quarter",
    "город": "world.scale_city",
    "страна": "world.scale_country",
    "планета": "world.scale_planet",
    "система": "world.scale_system",
    "галактика": "world.scale_galaxy",
}

MAP_ROW_WIDTH = 78  # видимая ширина строк рендера карты (≤ 80 колонок)

# Бюджет карт-секции промпта мастера (≈900 символов, из дизайна)
MAP_PROMPT_PATH_LIMIT = 125
MAP_PROMPT_MOVES_LIMIT = 345
MAP_PROMPT_LINKS_LIMIT = 345


def parse_scale(word):
    """Слово уровня (RU/EN) → каноническая метка; неизвестное — как есть."""
    value = (word or "").strip().lower()
    if not value:
        return None
    return SCALE_ALIASES.get(value, value)


def scale_display(label):
    """Отображаемое имя уровня: перевод для известных, иначе строка как есть."""
    if not label:
        return ""
    key = SCALE_I18N.get(parse_scale(label))
    return t(key) if key else label


def scale_choices():
    """Доступные уровни для подсказок: «строение, квартал, ...»."""
    return ", ".join(scale_display(s) for s in SCALE_LADDER)


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
        # Карта v1: иерархия точек (parent/scale) и уровень обзора
        self.nodes = d.get("nodes", {}) or {}
        self.map_view = d.get("map_view") or None

    def to_dict(self):
        out = {
            "location": self.location,
            "visited": self.visited,
            "facts": self.facts,
            "npc_voices": self.npc_voices,
            "connections": self.connections,
            "markets": self.markets,
            "trade_goods": self.trade_goods,
        }
        # Ленивая миграция: новые ключи появляются только когда есть данные
        if self.nodes:
            out["nodes"] = self.nodes
        if self.map_view:
            out["map_view"] = self.map_view
        return out

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
            chain = self.chain()
            if len(chain) > 1:
                path = _fit_crumbs(list(reversed(chain)), MAP_PROMPT_PATH_LIMIT)
                lines.append(f"Путь: {path}")
            moves, seen = [], set()
            for n in self.neighbors():
                if n not in seen:
                    seen.add(n)
                    moves.append(f"<<{n}>>")
            parent = self.parent_of(self.location)
            if parent and parent not in seen:
                seen.add(parent)
                moves.append(f"<<{parent}>> (вверх)")
            for child in self.children_of(self.location):
                if child not in seen:
                    seen.add(child)
                    moves.append(f"<<{child}>> (вниз)")
            if moves:
                lines.append("Можно идти: " + _cap_list(moves, MAP_PROMPT_MOVES_LIMIT))
        if self.facts:
            facts_str = "; ".join(self.facts)
            lines.append(f"Установленные факты мира: {facts_str}")
        if self.npc_voices:
            voices = ", ".join(f"{{{{{k}}}}} = {v}" for k, v in self.npc_voices.items())
            lines.append(f"Голоса NPC: {voices}")
        if self.connections:
            entries = [f"{k} ↔ {', '.join(v)}" for k, v in self.connections.items()]
            lines.append(
                "КАРТА связей: " + _cap_list(entries, MAP_PROMPT_LINKS_LIMIT, "; ")
            )
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

    # ── Карта v1: иерархия точек ─────────────────────────────────────────

    def parent_of(self, name):
        node = self.nodes.get(name) or {}
        return node.get("parent") or None

    def scale_of(self, name):
        node = self.nodes.get(name) or {}
        return node.get("scale") or None

    def children_of(self, name):
        return [
            n
            for n, node in self.nodes.items()
            if (node or {}).get("parent") == name
        ]

    def chain(self, name=None):
        """Путь точки вверх до корня (защита от циклов)."""

        name = name or self.location
        out, seen = [], set()
        while name and name not in seen:
            out.append(name)
            seen.add(name)
            name = self.parent_of(name)
        return out

    def move_options(self, loc=None):
        """Куда можно шагнуть: соседи ∪ родитель ∪ дети (один шаг)."""

        loc = loc or self.location
        opts = list(self.neighbors(loc))
        extras = [self.parent_of(loc), *self.children_of(loc)]
        for extra in extras:
            if extra and extra != loc and extra not in opts:
                opts.append(extra)
        return opts

    def _infer_scale(self, child, parent):
        """Уровень как у братьев, иначе на ступень ниже родителя."""

        for sib in self.children_of(parent):
            if sib != child and self.scale_of(sib):
                return self.scale_of(sib)
        parent_scale = self.scale_of(parent)
        if parent_scale in SCALE_LADDER:
            idx = SCALE_LADDER.index(parent_scale)
            if idx > 0:
                return SCALE_LADDER[idx - 1]
        return None

    def set_parent(self, child, parent, scale=None):
        """`!место`: родитель + уровень (явный → братья → ступень ниже)."""

        child = (child or "").strip()
        parent = (parent or "").strip()
        if not child or not parent or child == parent:
            return False
        # защита от циклов: родитель не может быть потомком ребёнка
        cur, seen = parent, set()
        while cur and cur not in seen:
            if cur == child:
                return False
            seen.add(cur)
            cur = self.parent_of(cur)
        node = self.nodes.setdefault(child, {})
        node["parent"] = parent
        if scale:
            node["scale"] = scale
        elif not node.get("scale"):
            inferred = self._infer_scale(child, parent)
            if inferred:
                node["scale"] = inferred
        return True

    def set_scale(self, name, scale):
        """`!место ... уровень <метка>`: явная запись уровня."""

        name = (name or "").strip()
        scale = (scale or "").strip()
        if not name or not scale:
            return False
        self.nodes.setdefault(name, {})["scale"] = scale
        return True

    def auto_parent(self, new_loc, origin):
        """Авто-родитель: новая точка получает parent = текущая локация."""

        new_loc = (new_loc or "").strip()
        origin = (origin or "").strip()
        if not new_loc or new_loc in self.nodes:
            return False
        self.nodes[new_loc] = {}
        if origin and origin != new_loc:
            self.set_parent(new_loc, origin)
        return True

    def zoom_map(self, step):
        """Шаг обзора ±1 по лестнице. Возвращает метку или None (край/нет уровней)."""

        cur = current_view_scale(self)
        if cur not in SCALE_LADDER:
            return None
        idx = SCALE_LADDER.index(cur) + step
        if not 0 <= idx < len(SCALE_LADDER):
            return None
        self.map_view = SCALE_LADDER[idx]
        return self.map_view


def current_view_scale(world: WorldState):
    """Уровень обзора: map_view, иначе уровень локации. None — не задан."""

    scale = world.map_view or world.scale_of(world.location)
    return parse_scale(scale) if scale else None


def level_branch(world: WorldState, scale):
    """Точка ветки игрока на уровне scale (ближайшая от локации вверх)."""

    if not scale:
        return None
    for name in world.chain():
        if parse_scale(world.scale_of(name)) == scale:
            return name
    return None


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


def _clip(text, width):
    """Обрезка строки до width символов с многоточием."""

    text = str(text)
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def _cap_list(items, limit, sep=", "):
    """Список в бюджет символов; остаток сворачивается в «… и ещё N» (RU, промпт)."""

    out, used = [], 0
    for i, item in enumerate(items):
        add = len(item) + (len(sep) if out else 0)
        if out and used + add > limit:
            out.append(f"… и ещё {len(items) - i}")
            break
        out.append(item)
        used += add
    return sep.join(out)


def _fit_crumbs(names, limit):
    """Путь до ветки: хвост важнее, верх сворачивается в «…»."""

    text = " ▸ ".join(names)
    if len(text) <= limit:
        return text
    out = []
    for name in reversed(names):
        cand = " ▸ ".join([name, *out])
        if len(cand) > limit:
            if out:
                break
            return "… ▸ " + _clip(name, max(1, limit - 4))
        out.insert(0, name)
    return "… ▸ " + " ▸ ".join(out)


def _print_row(label, items, color, width=MAP_ROW_WIDTH):
    """Строка «Метка элементы» с обрезкой по ширине и «… и ещё N»."""

    sep = "   "
    reserve = 14  # запас под «… и ещё N»
    budget = width - 3 - len(label)
    shown = []
    for item in items:
        used = sum(len(s) + len(sep) for s in shown)
        add = (len(sep) if shown else 0) + len(item)
        if shown and used + add > budget - reserve:
            break
        shown.append(item)
    text = sep.join(shown)
    rest = len(items) - len(shown)
    if rest:
        text += f" {t('world.map_more', n=rest)}"
    print(f"  {color}{label}{RESET} {text}")


def _show_flat_map(world: WorldState):
    """Плоский вид без иерархии: как один уровень (старые сессии)."""

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


def show_map(world: WorldState):
    """Уровень обзора: точки уровня, связи, путь. Без nodes — плоский вид."""

    if not world.nodes:
        _show_flat_map(world)
        return
    scale = current_view_scale(world)
    if not scale:
        show_map_all(world)
        return
    branch = level_branch(world, scale)
    here = t('world.map_here')
    print(f"\n{CYAN}{t('world.map_level_title', level=scale_display(scale))}{RESET}")
    chain = world.chain()
    rev = list(reversed(chain))  # корень → локация
    if branch and branch in chain:
        path = rev[: len(rev) - chain.index(branch)]  # корень → ветка
    else:
        path = rev
    if path:
        print(f"  {_fit_crumbs(path, MAP_ROW_WIDTH - 3 - len(here))} {here}")
    if not branch:
        print(
            f"  {YELLOW}"
            f"{t('world.map_level_missing', level=scale_display(scale))}{RESET}"
        )
        print(f"  {YELLOW}{t('world.map_hint')}{RESET}")
        return
    parent = world.parent_of(branch)
    siblings = []
    if parent:
        siblings = [
            n
            for n in world.children_of(parent)
            if n != branch
            and (
                world.scale_of(n) is None
                or parse_scale(world.scale_of(n)) == scale
            )
        ]
    points = [branch] + siblings
    _print_row(
        t('world.map_points'),
        [f"● {_clip(n, 40)}" + (" ◂" if n == branch else "") for n in points],
        GREEN,
    )
    pset = set(points)
    links = [
        (a, b)
        for i, a in enumerate(points)
        for b in world.neighbors(a)
        if b in pset and points.index(b) > i
    ]
    if links:
        _print_row(
            t('world.map_links'),
            [f"{_clip(a, 24)} ↔ {_clip(b, 24)}" for a, b in links],
            CYAN,
        )
    cross = []
    for a in points:
        for b in world.neighbors(a):
            if b not in pset and (b, a) not in cross:
                cross.append((a, b))
    if cross:
        items = []
        for a, b in cross:
            label = scale_display(parse_scale(world.scale_of(b)))
            item = f"{_clip(a, 20)} ↔ {_clip(b, 20)}"
            if label:
                item += f" [{label}]"
            items.append(item)
        _print_row(t('world.map_cross'), items, CYAN)
    # футер: ↑ родитель, ↓ дети, подсказка по зум-командам
    parts = []
    if parent:
        up = f"↑ {_clip(parent, 28)}"
        parent_scale = scale_display(parse_scale(world.scale_of(parent)))
        parts.append(f"{up} [{parent_scale}]" if parent_scale else up)
    kids = world.children_of(branch)
    if kids:
        parts.append(t('world.map_down', n=len(kids)))
    parts.append(t('world.map_hint'))
    while len(parts) > 1 and len("   ".join(parts)) + 2 > MAP_ROW_WIDTH:
        parts.pop(0)
    tail = f"{YELLOW}{parts[-1]}{RESET}"
    print("  " + "   ".join(parts[:-1] + [tail]))


def show_map_all(world: WorldState):
    """Вся ветка игрока: от корня до текущей локации."""

    if not world.nodes:
        _show_flat_map(world)
        return
    print(f"\n{CYAN}{t('world.map_all_title')}{RESET}")
    scale = current_view_scale(world)
    branch = level_branch(world, scale) if scale else None

    def row(name):
        raw = world.scale_of(name)
        label = scale_display(parse_scale(raw)) if raw else ""
        mark = ""
        if name == world.location:
            mark = f" {t('world.map_here')}"
        elif branch and name == branch:
            mark = " ◂"
        print(f"  {label:<10} {_clip(name, 54)}{mark}")

    chain_names = list(reversed(world.chain()))
    if len(chain_names) > 22:
        head, tail = chain_names[:6], chain_names[-12:]
        for name in head:
            row(name)
        hidden = len(chain_names) - len(head) - len(tail)
        print(f"  {t('world.map_more', n=hidden)}")
        for name in tail:
            row(name)
    else:
        for name in chain_names:
            row(name)


def parse_world_command(text):
    """Парсит команды мира. Возвращает (action, data) или None."""
    text = text.strip()

    if re.match(r'(?i)^!\s*мир', text):
        return ("show", None)

    m = re.match(r'(?i)^!\s*карта\b\s*(.*)$', text)
    if m:
        arg = m.group(1).strip()
        return ("map", arg or None)

    m = re.match(r'(?i)^!\s*место\s+(.+?)\s+(?:уровень|level)\s+(\S+)\s*$', text)
    if m:
        return ("place_level", (m.group(1).strip(), m.group(2).strip()))

    m = re.match(r'(?i)^!\s*место\s+(.+)\s+в\s+(.+?)\s*$', text)
    if m:
        return ("place", (m.group(1).strip(), m.group(2).strip()))

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
