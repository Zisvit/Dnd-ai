#!/usr/bin/env python3
"""Рисованный рендер карты: рамки локаций, линии связей, маркеры.

Модуль не зависит от WorldState: принимает готовые точки и связи.
Так граф можно рисовать и для иерархии, и для плоских карт старых сессий.
"""

import re

from dndai.core.colors import CYAN, GREEN, RESET, YELLOW
from dndai.core.i18n import t

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Ширина полотна карты (с отступом в 2 пробела получается ≤ 80 колонок).
MAP_WIDTH = 76

# Направления связи в битовой маске: удобно склеивать пересечения линий.
UP, DOWN, LEFT, RIGHT = 1, 2, 4, 8

_LINE_GLYPHS = {
    1: "╵",
    2: "╷",
    3: "│",
    4: "╴",
    5: "╯",
    6: "╮",
    7: "┤",
    8: "╶",
    9: "╰",
    10: "╭",
    11: "├",
    12: "─",
    13: "┴",
    14: "┬",
    15: "┼",
}

_GLYPH_BITS = {
    "─": LEFT | RIGHT,
    "│": UP | DOWN,
    "╭": DOWN | RIGHT,
    "╮": DOWN | LEFT,
    "╰": UP | RIGHT,
    "╯": UP | LEFT,
    "├": UP | DOWN | RIGHT,
    "┤": UP | DOWN | LEFT,
    "┬": DOWN | LEFT | RIGHT,
    "┴": UP | LEFT | RIGHT,
    "┼": UP | DOWN | LEFT | RIGHT,
}

_BORDER_GLYPHS = set(_GLYPH_BITS)


def visible_len(text):
    """Длина строки без ANSI-кодов."""
    return len(ANSI_RE.sub("", text))


def clip(text, width):
    """Обрезка строки до width символов с многоточием."""
    text = str(text)
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


class Canvas:
    """Символьное полотно: хранит символ и цвет каждой клетки."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.cells = [[None] * width for _ in range(height)]
        self.wires = {}
        self.arrows = set()

    def put(self, x, y, ch, color=""):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = (ch, color)

    def text(self, x, y, text, color=""):
        for i, ch in enumerate(text):
            self.put(x + i, y, ch, color)

    def wire(self, x, y, bits):
        """Добавляет направление связи в клетку (линии склеиваются)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.wires[(x, y)] = self.wires.get((x, y), 0) | bits

    def arrow(self, x, y):
        self.arrows.add((x, y))

    def _apply_wires(self):
        for (x, y), bits in self.wires.items():
            cell = self.cells[y][x]
            char = cell[0] if cell else " "
            color = (cell[1] if cell else "") or CYAN
            base = _GLYPH_BITS.get(char)

            if char in _BORDER_GLYPHS:
                merged = base | bits
            elif char == " ":
                merged = bits
            else:
                continue  # не затираем текст локации

            glyph = _LINE_GLYPHS.get(merged)
            if glyph:
                self.cells[y][x] = (glyph, color)

    def render(self):
        """Строки полотна с ANSI-цветами; хвостовые пробелы обрезаны."""
        self._apply_wires()
        for x, y in self.arrows:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.cells[y][x] = ("↔", CYAN)

        lines = []
        for row in self.cells:
            last = -1
            for i, cell in enumerate(row):
                if cell and cell[0] != " ":
                    last = i
            if last < 0:
                lines.append("")
                continue

            out = []
            active = ""
            for cell in row[: last + 1]:
                char, color = cell if cell else (" ", "")
                if color != active:
                    if active:
                        out.append(RESET)
                    if color:
                        out.append(color)
                    active = color
                out.append(char)
            if active:
                out.append(RESET)
            lines.append("".join(out))
        return lines


def _marker(name, current, focus, visited):
    if name == current:
        return "►", GREEN
    if name == focus:
        return "◈", GREEN
    if name in visited:
        return "●", CYAN
    return "○", YELLOW


def _box(canvas, x, y, width, label, color):
    canvas.text(x, y, "╭" + "─" * (width - 2) + "╮", color)
    canvas.text(x, y + 1, "│", color)
    canvas.text(x + 2, y + 1, label.ljust(width - 4), color)
    canvas.text(x + width - 1, y + 1, "│", color)
    canvas.text(x, y + 2, "╰" + "─" * (width - 2) + "╯", color)


def _route_horizontal(canvas, x1, y, x2):
    """Линия между соседними рамками одной строки."""
    canvas.wire(x1, y, RIGHT)
    canvas.wire(x2, y, LEFT)
    for x in range(x1 + 1, x2):
        canvas.wire(x, y, LEFT | RIGHT)
    if x2 - x1 >= 4:
        canvas.arrow((x1 + x2) // 2, y)


def _route_vertical(canvas, sx, sy, tx, ty):
    """Маршрут из низа одной рамки в верх другой (через коридор)."""
    if sx == tx:
        canvas.wire(sx, sy, DOWN)
        for y in range(sy + 1, ty):
            canvas.wire(sx, y, UP | DOWN)
        canvas.wire(tx, ty, UP)
        return

    corridor = sy + 2
    if corridor >= ty:  # слишком близко — рисуем прямую вертикаль
        canvas.wire(sx, sy, DOWN)
        for y in range(sy + 1, ty):
            canvas.wire(sx, y, UP | DOWN)
        canvas.wire(tx, ty, UP)
        return

    canvas.wire(sx, sy, DOWN)
    for y in range(sy + 1, corridor):
        canvas.wire(sx, y, UP | DOWN)

    if tx > sx:
        canvas.wire(sx, corridor, UP | RIGHT)
        for x in range(sx + 1, tx):
            canvas.wire(x, corridor, LEFT | RIGHT)
        canvas.wire(tx, corridor, LEFT | DOWN)
    else:
        canvas.wire(sx, corridor, UP | LEFT)
        for x in range(tx + 1, sx):
            canvas.wire(x, corridor, LEFT | RIGHT)
        canvas.wire(tx, corridor, RIGHT | DOWN)

    for y in range(corridor + 1, ty):
        canvas.wire(tx, y, UP | DOWN)
    canvas.wire(tx, ty, UP)


def _pack_items(label, items, width):
    """Упаковка списка в строки с меткой; хвост переносится с отступом."""
    out = []
    prefix = label + " " if label else ""
    current = prefix
    first = True
    for item in items:
        candidate = current + ("" if first else "   ") + item
        if current.strip() and visible_len(candidate) > width:
            out.append(current)
            current = " " * len(prefix) + item
        else:
            current = candidate
        first = False
    if current.strip():
        out.append(current)
    return out


def graph_lines(points, edges, current=None, focus=None, visited=None,
                children=None, width=MAP_WIDTH, legend=True):
    """Рисует граф уровня: рамки, связи, маркеры.

    points   — имена локаций уровня (порядок сохраняется);
    edges    — пары имён, между которыми есть проход;
    current  — локация игрока (маркер ►);
    focus    — точка ветки на этом уровне (маркер ◈);
    visited  — посещённые локации (маркер ●);
    children — {имя: сколько локаций внутри} для подписи ↓N.
    """
    points = [p for i, p in enumerate(points) if p and p not in points[:i]]
    if not points:
        return []

    visited = set(visited or ())
    children = children or {}
    width = max(24, width)

    entries = []
    for name in points:
        marker, color = _marker(name, current, focus, visited)
        suffix = f" ↓{children[name]}" if children.get(name) else ""
        label = f"{marker} {clip(name, 22)}"
        inner_limit = 20
        if len(label) + len(suffix) > inner_limit:
            label = clip(label, max(4, inner_limit - len(suffix)))
        label += suffix
        box_w = max(14, min(24, len(label) + 4))
        entries.append(
            {
                "name": name,
                "label": label.ljust(box_w - 4),
                "width": box_w,
                "color": color,
            }
        )

    gap = 6
    rows = []
    row, used = [], 0
    for entry in entries:
        need = entry["width"] + (gap if row else 0)
        if row and used + need > width:
            rows.append(row)
            row, used = [], 0
            need = entry["width"]
        row.append(entry)
        used += need
    if row:
        rows.append(row)

    row_step = 7
    positions = {}
    canvas = Canvas(width, row_step * len(rows) - 4)
    for row_index, row in enumerate(rows):
        total = sum(e["width"] for e in row) + gap * (len(row) - 1)
        x = max(0, (width - total) // 2)
        y = row_index * row_step
        for entry in row:
            _box(canvas, x, y, entry["width"], entry["label"], entry["color"])
            positions[entry["name"]] = (x, y, entry["width"], row_index)
            x += entry["width"] + gap

    drawn = set()
    loose = []
    for a, b in edges:
        if a == b or (a, b) in drawn or (b, a) in drawn:
            continue
        if a not in positions or b not in positions:
            continue
        drawn.add((a, b))
        ax, ay, aw, arow = positions[a]
        bx, by, bw, brow = positions[b]
        if ay == by:
            if abs(ax - bx) == aw + gap:
                if ax > bx:
                    ax, bx, aw, bw = bx, ax, bw, aw
                _route_horizontal(canvas, ax + aw - 1, ay + 1, bx)
            else:
                loose.append((a, b))
        elif abs(arow - brow) == 1:
            sx, sy = ax + aw // 2, ay + 2
            tx, ty = bx + bw // 2, by
            _route_vertical(canvas, sx, sy, tx, ty)
        else:
            loose.append((a, b))

    lines = canvas.render()
    while lines and not lines[-1]:
        lines.pop()

    # Связи, которые не поместились в сетку, показываем отдельной строкой.
    if loose:
        normal = []
        for a, b in loose:
            normal.append(f"{clip(a, 18)} ↔ {clip(b, 18)}")
        lines.append("")
        lines.extend(_pack_items(t("world.map_extra_links"), normal, width))

    if legend:
        lines.append("")
        marks = [t("world.map_legend")]
        if any(children.get(p) for p in points):
            marks.append(t("world.map_children_hint"))
        lines.extend(_pack_items("", marks, width))
    return lines


def tree_lines(nodes, roots, children_map, labels, current, visited,
               here_text, width=MAP_WIDTH, max_nodes=80, max_depth=18):
    """Дерево мира с рамками-ветками: корень сверху, текущая точка снизу.

    Возвращает (строки, сколько_точек_скрыто). Строки уже с ANSI-цветами.
    """
    nodes = nodes or {}
    roots = [r for i, r in enumerate(roots) if r and r not in roots[:i]]
    if not roots:
        return [], 0

    visited = set(visited or ())

    reachable = 0
    seen_count = set()

    def count(name):
        nonlocal reachable
        if name in seen_count:
            return
        seen_count.add(name)
        reachable += 1
        for kid in children_map.get(name, []):
            count(kid)

    for root in roots:
        count(root)
    # Точки, не достижимые из корней (циклы/осиротевшие), тоже считаем.
    for name in nodes:
        if name not in seen_count:
            count(name)

    shown = [0]
    hidden = [0]
    lines = []

    def emit(name, prefix, connector, depth):
        if name in seen_set:
            return
        seen_set.add(name)
        if shown[0] >= max_nodes or depth > max_depth:
            hidden[0] += 1
            return

        raw_scale = labels.get(name, "")
        tag = f" [{raw_scale}]" if raw_scale else ""
        if name == current:
            marker, color, suffix = "►", GREEN, f" {here_text}"
        elif name in visited:
            marker, color, suffix = "●", CYAN, ""
        else:
            marker, color, suffix = "○", YELLOW, ""

        base = width - len(prefix) - len(connector) - 2  # маркер и пробел
        visible = base - len(tag) - len(suffix)
        if visible < 6:
            suffix = ""
            visible = base - len(tag)
        if visible < 6:
            tag = ""
            visible = base
        title = clip(name, max(6, visible))
        line = prefix + connector + marker + " " + title + tag + suffix
        lines.append(color + line + RESET)
        shown[0] += 1

        kids = [k for k in children_map.get(name, []) if k not in seen_set]
        if connector == "":
            child_prefix = ""
        else:
            child_prefix = prefix + ("   " if connector.startswith("└") else "│  ")
        for index, kid in enumerate(kids):
            is_last = index == len(kids) - 1
            emit(kid, child_prefix, "└─ " if is_last else "├─ ", depth + 1)

    seen_set = set()
    for root in roots:
        emit(root, "", "", 0)
    # Осиротевшие точки (например, цикл в старых данных) — отдельными корнями.
    for name in nodes:
        if name not in seen_set:
            emit(name, "", "", 0)

    hidden[0] = max(hidden[0], reachable - shown[0])
    return lines, hidden[0]
