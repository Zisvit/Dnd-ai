#!/usr/bin/env python3
"""Расширенная RPG-механика: заклинания, уровни/XP, статус-эффекты,
квесты, NPC, время/погода, журнал событий, макросы, тон/жанр.

Всё хранится в сессии как dict `rpg` и сериализуется через to_dict/from_dict.
"""

import re
import random

from dndai.core.colors import GREEN, BLUE, RED, YELLOW, CYAN, RESET
from dndai.core.i18n import t


# ── Лечащие заклинания ──────────────────────────────────────────────────

HEAL_WORDS = ("леч", "исцел", "хил", "heal", "cure", "restore", "медицина")


def is_heal_spell(spell):
    """Определяет лечащее заклинание по имени/описанию/эффекту."""
    blob = " ".join((spell.get("name") or "", spell.get("desc") or "",
                     spell.get("effect") or "")).lower()
    return any(w in blob for w in HEAL_WORDS)


def heal_dice(spell):
    """Кость лечения заклинания: из поля dmg или дефолт 2d8."""
    dmg = (spell.get("dmg") or "").strip()
    if dmg and "d" in dmg:
        return dmg
    return "2d8"


# ── Атака врагов: параметры растут с их силой (max HP) ───────────────────

def mob_attack_stats(foe):
    """(бонус атаки, кость урона) врага — производные от его max_hp.

    Раньше все враги били одинаково (+5, 1d6+2) независимо от силы.
    """
    mhp = int(foe.get("max_hp", 10))
    bonus = 2 + min(6, mhp // 8)
    if mhp <= 10:
        dice = "1d6"
    elif mhp <= 25:
        dice = "1d6+2"
    elif mhp <= 50:
        dice = "2d6+2"
    else:
        dice = "2d8+3"
    return bonus, dice


# ─────────────────────────── Заклинания / способности ───────────────────────────

class SpellBook:
    """Книга заклинаний и способностей игрока + ячейки заклинаний."""

    # Классы, умеющие колдовать (паладин — хоумрул-полукаст)
    CASTER_CLASSES = {"маг", "чародей", "варлок", "друид", "жрец", "бард",
                      "паладин",
                      "wizard", "sorcerer", "warlock", "druid", "cleric",
                      "bard", "paladin"}

    def __init__(self, data=None):
        d = data or []
        self.slots_used = 0
        if isinstance(d, dict):
            # новый формат: {"spells": [...], "slots_used": N}
            self.spells = list(d.get("spells", []))
            try:
                self.slots_used = max(0, int(d.get("slots_used", 0)))
            except (TypeError, ValueError):
                self.slots_used = 0
        else:
            # старый формат: просто список заклинаний
            self.spells = list(d)
        self.slots_max = 0  # вычисляется от уровня/класса через set_slots()

    def set_slots(self, level, char_class=""):
        """Ячейки заклинаний: уровень+1 для магических классов, иначе 0."""
        is_caster = (char_class or "").strip().lower() in self.CASTER_CLASSES
        self.slots_max = (max(1, level) + 1) if is_caster else 0
        self.slots_used = min(self.slots_used, self.slots_max)
        return self.slots_max

    @property
    def slots_left(self):
        return max(0, self.slots_max - self.slots_used)

    def use_slot(self):
        if self.slots_left <= 0:
            return False
        self.slots_used += 1
        return True

    def restore_slots(self):
        used = self.slots_used
        self.slots_used = 0
        return used

    def to_dict(self):
        return {"spells": self.spells, "slots_used": self.slots_used}

    def add(self, name, desc="", effect="", save_dc=0, dmg=""):
        name = name.strip()
        if not name:
            return False
        for s in self.spells:
            if s["name"].lower() == name.lower():
                s.update({"desc": desc, "effect": effect, "save_dc": save_dc, "dmg": dmg})
                return True
        self.spells.append({
            "name": name, "desc": desc, "effect": effect,
            "save_dc": save_dc, "dmg": dmg,
        })
        return True

    def remove(self, name):
        before = len(self.spells)
        self.spells = [s for s in self.spells if s["name"].lower() != name.lower()]
        return len(self.spells) < before

    def find(self, name):
        for s in self.spells:
            if s["name"].lower() == name.lower():
                return s
        for s in self.spells:
            if name.lower() in s["name"].lower():
                return s
        return None

    def show(self):
        if not self.spells:
            print(f"{YELLOW}{t('rpg.spells_empty')}{RESET}")
            return
        print(f"\n{CYAN}{t('rpg.spells_title')}{RESET}")
        for s in self.spells:
            extra = []
            if s.get("dmg"):
                extra.append(t('rpg.spell_dmg', dmg=s['dmg']))
            if s.get("save_dc"):
                extra.append(t('rpg.spell_dc', dc=s['save_dc']))
            ex = f" ({', '.join(extra)})" if extra else ""
            print(f"  {GREEN}{s['name']}{RESET}{ex}")
            if s.get("effect") or s.get("desc"):
                print(f"    {s.get('effect') or s.get('desc')}")

    def prompt_block(self):
        if not self.spells and not self.slots_max:
            return ""
        lines = ["[ЗАКЛИНАНИЯ И СПОСОБНОСТИ ИГРОКА]"]
        if self.slots_max:
            lines.append(f"Ячейки заклинаний: осталось {self.slots_left} из {self.slots_max}")
        for s in self.spells:
            ex = []
            if s.get("dmg"):
                ex.append(f"урон {s['dmg']}")
            if s.get("save_dc"):
                ex.append(f"СЛ {s['save_dc']}")
            exs = f" ({', '.join(ex)})" if ex else ""
            lines.append(f"- {s['name']}{exs}: {s.get('effect') or s.get('desc')}")
        lines.append("[/ЗАКЛИНАНИЯ]")
        return "\n".join(lines)


# ─────────────────────────── Уровни и опыт ───────────────────────────

class Progression:
    """Уровень, XP, очки характеристик."""

    XP_TABLE = [0, 0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000,
                64000, 85000, 100000, 120000, 140000, 165000, 195000,
                225000, 265000, 305000, 355000]

    def __init__(self, data=None):
        d = data or {}
        self.level = d.get("level", 1)
        self.xp = d.get("xp", 0)
        self.xp_bonus = d.get("xp_bonus", 0)

    def to_dict(self):
        return {"level": self.level, "xp": self.xp, "xp_bonus": self.xp_bonus}

    @property
    def xp_for_next(self):
        if self.level >= len(self.XP_TABLE) - 1:
            return None
        return self.XP_TABLE[self.level + 1]

    @property
    def xp_for_current(self):
        return self.XP_TABLE[self.level]

    def add_xp(self, amount):
        if amount <= 0:
            return []
        self.xp += amount
        leveled = []
        while (self.xp_for_next is not None and self.xp >= self.xp_for_next):
            self.level += 1
            self.xp_bonus += 1
            leveled.append(self.level)
        return leveled

    def show(self):
        nxt = self.xp_for_next
        if nxt is None:
            prog = t('rpg.progression_max')
        else:
            cur = self.xp_for_current
            span = nxt - cur
            have = self.xp - cur
            prog = f"{have}/{span} {t('rpg.progression_to_next')}"
        print(f"  {GREEN}{t('rpg.progression_title')}{RESET} {self.level}  "
              f"{GREEN}XP:{RESET} {self.xp} ({prog})"
              f"  {GREEN}{t('rpg.progression_points')}{RESET} {self.xp_bonus}")

    def prompt_block(self):
        return (f"[ПРОГРЕСС ИГРОКА]\nУровень {self.level}, XP {self.xp}"
                f"{' (есть очки для улучшения характеристик)' if self.xp_bonus else ''}"
                f"\n[/ПРОГРЕСС]")


# ─────────────────────────── Статус-эффекты ───────────────────────────

class StatusEffects:
    """Временные эффекты с таймером в ходах."""

    KNOWN = {
        "оглушён": "не может действовать",
        "отравлен": "теряет 1 HP в конце хода",
        "горит": "теряет 1d4 HP в конце хода",
        "защита": "получает +2 к КД",
        "укрытие": "получает +2 к КД",
        "благословение": "+1 к спасброскам",
        "проклятие": "-1 к спасброскам",
        "ускорение": "получает доп. действие",
        "ослабление": "-2 к атакам",
    }

    def __init__(self, data=None):
        d = data or []
        self.effects = []
        # Нормализуем записи (старые сохранения могли не иметь rounds/magnitude)
        for e in d:
            if isinstance(e, str):
                self.effects.append({"name": e, "rounds": 1, "magnitude": 0})
            elif isinstance(e, dict) and e.get("name"):
                self.effects.append({
                    "name": e["name"],
                    "rounds": int(e.get("rounds", 1)),
                    "magnitude": e.get("magnitude", 0),
                })

    def to_dict(self):
        return self.effects

    def add(self, name, rounds=1, magnitude=0):
        name = name.strip().lower()
        if not name:
            return False
        for e in self.effects:
            if e["name"] == name:
                e["rounds"] = max(e.get("rounds", 1), rounds)
                if magnitude:
                    e["magnitude"] = magnitude
                return True
        self.effects.append({"name": name, "rounds": rounds, "magnitude": magnitude})
        return True

    def remove(self, name):
        before = len(self.effects)
        self.effects = [e for e in self.effects if e["name"] != name.lower()]
        return len(self.effects) < before

    def tick(self):
        expired = []
        for e in self.effects:
            e["rounds"] -= 1
        for e in list(self.effects):
            if e["rounds"] <= 0:
                expired.append(e["name"])
                self.effects.remove(e)
        return expired

    def ac_bonus(self):
        return sum(2 for e in self.effects if e["name"] in ("защита", "укрытие"))

    def save_bonus(self):
        bonus = 0
        for e in self.effects:
            if e["name"] == "благословение":
                bonus += 1
            elif e["name"] == "проклятие":
                bonus -= 1
        return bonus

    def tick_damage(self):
        total = 0
        parts = []
        for e in self.effects:
            if e["name"] == "отравлен":
                total += 1
                parts.append("отравление 1")
            elif e["name"] == "горит":
                d = random.randint(1, 4)
                total += d
                parts.append(f"горение {d}")
        return total, parts

    def show(self):
        if not self.effects:
            print(f"  {YELLOW}{t('rpg.effects_empty')}{RESET}")
            return
        print(f"  {GREEN}{t('rpg.effects_title')}{RESET}")
        for e in self.effects:
            desc = self.KNOWN.get(e["name"], "")
            txt = f"{e['name']} (ходов: {e['rounds']})"
            if desc:
                txt += f" — {desc}"
            print(f"    • {txt}")

    def prompt_block(self):
        if not self.effects:
            return ""
        lines = ["[АКТИВНЫЕ ЭФФЕКТЫ ИГРОКА]"]
        for e in self.effects:
            desc = self.KNOWN.get(e["name"], "")
            lines.append(f"- {e['name']} (ходов: {e['rounds']})"
                         + (f": {desc}" if desc else ""))
        lines.append("[/ЭФФЕКТЫ]")
        return "\n".join(lines)


# ─────────────────────────── Враги в бою ───────────────────────────

class Enemies:
    """Трекинг врагов в активном бою: HP, КД, полученный урон.

    Хранится в rpg-состоянии сессии, поэтому бой переживает перезапуск.
    """

    def __init__(self, data=None):
        d = data or []
        self.enemies = []
        for e in d:
            if isinstance(e, dict) and e.get("name"):
                hp = max(1, int(e.get("hp", 1)))
                try:
                    init = int(e.get("init", random.randint(1, 20) + 2))
                except (TypeError, ValueError):
                    init = random.randint(1, 20) + 2
                self.enemies.append({
                    "name": e["name"],
                    "hp": hp,
                    "max_hp": max(hp, int(e.get("max_hp", hp))),
                    "ac": max(0, min(40, int(e.get("ac", 10)))),
                    "init": max(1, min(30, init)),
                })

    def to_dict(self):
        return [dict(e) for e in self.enemies]

    def __len__(self):
        return len(self.enemies)

    def attack_order(self):
        """Живые враги в порядке инициативы (кто быстрее — тот раньше)."""
        return sorted(self.enemies, key=lambda e: -e.get("init", 10))

    def find(self, name):
        """Ищет врага по имени (точное или частичное совпадение)."""
        n = (name or "").strip().lower()
        for e in self.enemies:
            if e["name"].lower() == n:
                return e
        for e in self.enemies:
            if n in e["name"].lower():
                return e
        return None

    def add(self, name, hp=10, ac=10, init=None):
        name = name.strip()
        if not name or self.find(name):
            return None
        hp = max(1, int(hp))
        roll = random.randint(1, 20) + 2  # инициатива d20
        e = {"name": name, "hp": hp, "max_hp": hp,
             "ac": max(0, min(40, int(ac))),
             "init": max(1, min(30, roll)) if init is None
                     else max(1, min(30, int(init)))}
        self.enemies.append(e)
        return e

    def remove(self, name):
        e = self.find(name)
        if e:
            self.enemies.remove(e)
            return True
        return False

    def damage(self, name, dmg):
        """Наносит урон. Возвращает (урон_реально_применённый, убит_ли)."""
        e = self.find(name)
        if not e:
            return 0, False
        applied = min(max(0, int(dmg)), e["hp"])
        e["hp"] -= applied
        killed = e["hp"] <= 0
        if killed:
            self.enemies.remove(e)
        return applied, killed

    def all_dead(self):
        return not self.enemies

    def show(self):
        if not self.enemies:
            print(f"  {YELLOW}{t('combat.no_enemies')}{RESET}")
            return
        print(f"  {RED}{t('combat.enemies_title')}{RESET}")
        for e in self.attack_order():
            bar_len = 10
            filled = round(bar_len * e["hp"] / e["max_hp"])
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"    • {e['name']} — HP {e['hp']}/{e['max_hp']} {bar}  "
                  f"КД {e['ac']}  {t('combat.initiative')} {e['init']}")

    def prompt_block(self):
        if not self.enemies:
            return ""
        lines = ["[ВРАГИ В АКТИВНОМ БОЮ]"]
        for e in self.enemies:
            lines.append(f"- {e['name']}: HP {e['hp']}/{e['max_hp']}, КД {e['ac']}")
        lines.append("[/ВРАГИ]")
        return "\n".join(lines)


# ─────────────────────────── Репутация фракций ───────────────────────────

class Reputation:
    """Отношение фракций к партии: от -100 (враги) до +100 (свои).

    Мастер может менять маркером [[РЕПУТАЦИЯ: Корпорация -20]].
    """

    def __init__(self, data=None):
        d = data or {}
        self.scores = dict(d)

    def to_dict(self):
        return dict(self.scores)

    def change(self, faction, delta):
        faction = faction.strip().title()
        if not faction:
            return None
        cur = self.scores.get(faction, 0)
        self.scores[faction] = max(-100, min(100, cur + int(delta)))
        return self.scores[faction]

    @staticmethod
    def _label(score):
        if score <= -50:
            return "враждебно"
        if score <= -15:
            return "недоверие"
        if score < 15:
            return "нейтрально"
        if score < 50:
            return "дружелюбно"
        return "преданность"

    def prompt_block(self):
        if not self.scores:
            return ""
        lines = ["[РЕПУТАЦИЯ ФРАКЦИЙ]"]
        for f, s in sorted(self.scores.items(), key=lambda kv: kv[1]):
            lines.append(f"- {f}: {s:+d} ({self._label(s)})")
        lines.append("[/РЕПУТАЦИЯ]")
        return "\n".join(lines)

    def show(self):
        if not self.scores:
            print(f"  {YELLOW}{t('rep.empty')}{RESET}")
            return
        print(f"  {CYAN}{t('rep.title')}{RESET}")
        for f, s in sorted(self.scores.items(), key=lambda kv: kv[1]):
            col = RED if s < -15 else (GREEN if s >= 15 else YELLOW)
            bar = ("+" * (s // 10) if s > 0 else "-" * (-s // 10)) or "·"
            print(f"    {f}: {col}{s:+d}{RESET} [{bar}] {self._label(s)}")


# ─────────────────────────── Квесты ───────────────────────────

class Quests:
    def __init__(self, data=None):
        d = data or {"active": [], "done": []}
        self.active = d.get("active", [])
        self.done = d.get("done", [])
        # Счётчик ID: продолжаем с максимума существующих, чтобы
        # после abandon/complete ID не переиспользовались
        ids = [q.get("id", 0) for q in self.active + self.done]
        self._next_id = max(ids) + 1 if ids else 1

    def to_dict(self):
        return {"active": self.active, "done": self.done}

    def add(self, title, desc=""):
        title = title.strip()
        if not title:
            return False
        if any(q["title"].lower() == title.lower() for q in self.active):
            return False
        self.active.append({"title": title, "desc": desc, "id": self._next_id})
        self._next_id += 1
        return True

    def complete(self, title):
        title = title.strip().lower()
        for q in self.active:
            if q["title"].lower() == title:
                self.active.remove(q)
                self.done.append(q)
                return q["title"]
        return None

    def abandon(self, title):
        title = title.strip().lower()
        for q in self.active:
            if q["title"].lower() == title:
                self.active.remove(q)
                return q["title"]
        return None

    def show(self):
        print(f"\n{CYAN}{t('rpg.quests_title')}{RESET}")
        if self.active:
            print(f"  {GREEN}{t('rpg.quests_active')}{RESET}")
            for q in self.active:
                extra = f" — {q['desc']}" if q.get("desc") else ""
                print(f"    • [{q['id']}] {q['title']}{extra}")
        else:
            print(f"  {YELLOW}{t('rpg.quests_active_empty')}{RESET}")
        if self.done:
            print(f"  {BLUE}{t('rpg.quests_done')}{RESET}")
            for q in self.done:
                print(f"    ✓ {q['title']}")

    def prompt_block(self):
        if not self.active:
            return ""
        lines = ["[АКТИВНЫЕ КВЕСТЫ]"]
        for q in self.active:
            lines.append(f"- {q['title']}" + (f": {q['desc']}" if q.get("desc") else ""))
        lines.append("[/КВЕСТЫ]")
        return "\n".join(lines)


# ─────────────────────────── NPC ───────────────────────────

class NPCs:
    def __init__(self, data=None):
        d = data or {}
        self.npcs = dict(d)

    def to_dict(self):
        return self.npcs

    def add(self, name, voice="", note="", relation="нейтрально"):
        name = name.strip().strip("{}").strip()
        if not name:
            return False
        if name not in self.npcs:
            self.npcs[name] = {}
        if voice:
            self.npcs[name]["voice"] = voice
        if note:
            self.npcs[name]["note"] = note
        if relation:
            self.npcs[name]["relation"] = relation
        return True

    def remove(self, name):
        name = name.strip().strip("{}").strip()
        if name in self.npcs:
            del self.npcs[name]
            return True
        return False

    def show(self):
        print(f"\n{CYAN}{t('rpg.npcs_title')}{RESET}")
        if not self.npcs:
            print(f"  {YELLOW}{t('rpg.npcs_empty')}{RESET}")
            return
        for name, info in self.npcs.items():
            parts = []
            if info.get("voice"):
                parts.append(f"{t('rpg.npc_voice')}: {info['voice']}")
            if info.get("relation"):
                parts.append(f"{t('rpg.npc_relation')}: {info['relation']}")
            if info.get("note"):
                parts.append(info["note"])
            extra = f" ({', '.join(parts)})" if parts else ""
            print(f"  {GREEN}{{{name}}}{RESET}{extra}")

    def prompt_block(self):
        if not self.npcs:
            return ""
        lines = ["[ИЗВЕСТНЫЕ NPC]"]
        for name, info in self.npcs.items():
            tag = info.get("voice", "")
            rel = info.get("relation", "")
            note = info.get("note", "")
            desc = f"голос={tag}; отношение={rel}; {note}".strip("; ")
            lines.append(f"- {{{name}}}: {desc}")
        lines.append("[/NPC]")
        return "\n".join(lines)


# ─────────────────────────── Время и погода ───────────────────────────

class TimeWeather:
    WEATHERS = ["ясно", "пасмурно", "дождь", "туман", "снег", "гроза", "жара", "ураган"]

    def __init__(self, data=None):
        d = data or {}
        self.hour = d.get("hour", 8)
        self.day = d.get("day", 1)
        self.weather = d.get("weather", "ясно")

    def to_dict(self):
        return {"hour": self.hour, "day": self.day, "weather": self.weather}

    def _part(self):
        h = self.hour % 24
        if 5 <= h < 7:
            return t('rpg.time_part_dawn')
        if 7 <= h < 11:
            return t('rpg.time_part_morning')
        if 11 <= h < 13:
            return t('rpg.time_part_noon')
        if 13 <= h < 17:
            return t('rpg.time_part_afternoon')
        if 17 <= h < 19:
            return t('rpg.time_part_evening')
        if 19 <= h < 21:
            return t('rpg.time_part_sunset')
        if 21 <= h < 24:
            return t('rpg.time_part_night')
        return t('rpg.time_part_late_night')

    def advance(self, hours=1):
        self.hour += hours
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1

    def set_weather(self, w):
        w = w.strip().lower()
        if w in self.WEATHERS:
            self.weather = w
            return True
        return False

    def show(self):
        print(f"  {GREEN}{t('rpg.time_title')}{RESET} {t('rpg.day')} {self.day}, "
              f"{self._part()} ({self.hour:02d}:00), {t('rpg.weather')}: {self.weather}")

    def prompt_block(self):
        return (f"[ВРЕМЯ И ПОГОДА]\nТекущее: День {self.day}, {self._part()} "
                f"({self.hour:02d}:00), погода: {self.weather}\n"
                f"Учитывай время суток и погоду в описаниях.[/ВРЕМЯ]")


# ─────────────────────────── Журнал событий ───────────────────────────

class Journal:
    def __init__(self, data=None):
        d = data or []
        self.entries = list(d)

    def to_dict(self):
        return self.entries

    def add(self, text, day=1, part=""):
        text = text.strip()
        if not text:
            return False
        self.entries.append({"day": day, "part": part, "text": text})
        if len(self.entries) > 100:
            self.entries = self.entries[-100:]
        return True

    def show(self, n=10):
        print(f"\n{CYAN}{t('rpg.journal_title')}{RESET}")
        if not self.entries:
            print(f"  {YELLOW}{t('rpg.journal_empty')}{RESET}")
            return
        for e in self.entries[-n:]:
            tag = f"Д{e['day']}" + (f" {e['part']}" if e.get('part') else "")
            print(f"  {BLUE}[{tag}]{RESET} {e['text']}")

    def prompt_block(self):
        if not self.entries:
            return ""
        lines = ["[НЕДАВНИЕ СОБЫТИЯ ИЗ ДНЕВНИКА]"]
        for e in self.entries[-8:]:
            lines.append(f"- Д{e['day']} {e.get('part','')}: {e['text']}")
        lines.append("[/ДНЕВНИК]")
        return "\n".join(lines)


# ─────────────────────────── Макросы ───────────────────────────

class Macros:
    def __init__(self, data=None):
        d = data or {}
        self.macros = dict(d)

    def to_dict(self):
        return self.macros

    def add(self, name, command):
        name = name.strip().lower()
        command = command.strip()
        if not name or not command:
            return False
        self.macros[name] = command
        return True

    def remove(self, name):
        name = name.strip().lower()
        if name in self.macros:
            del self.macros[name]
            return True
        return False

    def expand(self, text):
        key = text.strip().lower()
        return self.macros.get(key)

    def show(self):
        print(f"\n{CYAN}{t('rpg.macros_title')}{RESET}")
        if not self.macros:
            print(f"  {YELLOW}{t('rpg.macros_empty')}{RESET}")
            return
        for name, cmd in self.macros.items():
            print(f"  {GREEN}{name}{RESET} → {cmd}")

    def prompt_block(self):
        return ""


# ─────────────────────────── Тон и жанр ───────────────────────────

class Style:
    TONES = ["мрачный", "весёлый", "серьёзный", "ироничный", "жестокий",
             "романтичный", "философский", "напряжённый"]
    GENRES = ["нуар", "киберпанк", "фэнтези", "хоррор", "вестерн",
              "постапокалипсис", "детектив", "слэшер"]

    def __init__(self, data=None):
        d = data or {}
        self.tone = d.get("tone", "")
        self.genre = d.get("genre", "")
        self.language_style = d.get("language_style", "")

    def to_dict(self):
        return {"tone": self.tone, "genre": self.genre,
                "language_style": self.language_style}

    def set_tone(self, t):
        t = t.strip().lower()
        self.tone = t
        return t in self.TONES

    def set_genre(self, g):
        g = g.strip().lower()
        self.genre = g
        return g in self.GENRES

    def prompt_block(self):
        parts = []
        if self.genre:
            parts.append(f"Жанр: {self.genre}")
        if self.tone:
            parts.append(f"Тон повествования: {self.tone}")
        if self.language_style:
            parts.append(f"Стиль речи: {self.language_style}")
        if not parts:
            return ""
        return "[СТИЛЬ ИСТОРИИ]\n" + "; ".join(parts) + "\n[/СТИЛЬ]"


# ─────────────────────────── Быстрые парсеры команд ───────────────────────────

def parse_spell_command(text):
    m = re.match(r'(?i)!?\s*закл(?:инание)?\s+(.+)', text)
    if not m:
        return None
    body = m.group(1).strip()
    name = body
    desc, dmg, dc = "", "", 0
    parts = [p.strip() for p in re.split(r'\|', body) if p.strip()]
    if parts:
        head = parts[0]
        # разделяем "Имя: Описание" в первой части
        if ':' in head:
            name, _, head_desc = head.partition(':')
            name = name.strip()
            head_desc = head_desc.strip()
            if not desc and head_desc:
                desc = head_desc
        else:
            name = head
        for p in parts[1:]:
            if re.match(r'(?i)урон|dmg|damage', p):
                mm = re.search(r'(\d*d\d+(?:\+\d+)?)', p)
                if mm:
                    dmg = mm.group(1)
            elif re.match(r'(?i)сл|dc|save', p):
                mm = re.search(r'(\d+)', p)
                if mm:
                    dc = int(mm.group(1))
            else:
                desc = p
    return ("spell_add", (name, desc, dmg, dc))


# Точные слова-глаголы подкоманд квеста (не префиксы!):
# «!квест Закрытие гейта: ...» не должен превращаться в завершение.
QUEST_DONE_VERBS = {"готов", "готово", "выполнено", "выполнить", "закрыть",
                    "done", "complete", "completed"}
QUEST_DEL_VERBS = {"удалить", "удал", "бросить", "abandon", "rm", "del"}


def parse_quest_command(text):
    m = re.match(r'(?i)!?\s*квест\s+(.+)', text)
    if not m:
        return None
    body = m.group(1).strip()
    first, _, rest = body.partition(' ')
    verb = first.lower().strip(',.!')
    if verb in QUEST_DONE_VERBS:
        # название может прийти вместе с описанием "Название: опис"
        title = rest.strip() or first
        title = title.split(':', 1)[0].strip()
        return ("quest_done", title)
    if verb in QUEST_DEL_VERBS:
        title = rest.strip() or first
        title = title.split(':', 1)[0].strip()
        return ("quest_del", title)
    # добавление: "Название: описание" или "Название | описание"
    body = re.split(r'\|', body, maxsplit=1)[0]
    if ':' in body:
        title, desc = body.split(':', 1)
        title, desc = title.strip(), desc.strip()
    else:
        title, desc = body.strip(), ""
    return ("quest_add", (title, desc))


def parse_npc_command(text):
    m = re.match(r'(?i)!?\s*npc\s+(\S+)\s*(.*)$', text)
    if not m:
        return None
    # исключаем команды удаления
    if re.match(r'(?i)!?\s*npc\s+(?:удал|del|rm)\b', text):
        return None
    name = m.group(1).strip("{}").strip()
    rest = m.group(2).strip()
    voice, note, relation = "", "", ""
    parts = [p.strip() for p in re.split(r'\|', rest) if p.strip()]
    if parts:
        for p in parts:
            if re.match(r'(?i)голос|voice', p):
                mm = re.search(r'(?i)(?:голос|voice)\s*:?\s*(\S+)', p)
                if mm:
                    voice = mm.group(1)
            elif re.match(r'(?i)отнош|rel', p):
                mm = re.search(r'(?i)(?:отнош|rel)\s*:?\s*(\S+)', p)
                if mm:
                    relation = mm.group(1)
            else:
                # позиционно: первый неразмеченный кусок — голос, второй — заметка, третий — отношение
                if not voice:
                    voice = p
                elif not note:
                    note = p
                elif not relation:
                    relation = p
    return ("npc_add", (name, voice, note, relation))


def parse_status_command(text):
    m = re.match(r'(?i)!?\s*статус-эффект\s+(\S+)(?:\s+(\d+))?', text)
    if not m:
        return None
    name = m.group(1).strip().lower()
    rounds = int(m.group(2)) if m.group(2) else 1
    return ("status_add", (name, rounds))


def parse_macro_command(text):
    m = re.match(r'(?i)!?\s*макрос\s+(\S+)\s*(?:=|:)\s*(.+)', text)
    if m:
        return ("macro_add", (m.group(1).strip(), m.group(2).strip()))
    m = re.match(r'(?i)!?\s*макрос\s+(?:удал|del|rm)\s+(\S+)', text)
    if m:
        return ("macro_del", m.group(1).strip())
    return None
