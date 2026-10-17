#!/usr/bin/env python3
"""Состояние персонажа: HP, класс, инвентарь, модификаторы.

Хранится в сессии как dict `state`. Бот видит его в системном промпте,
поэтому может учитывать характеристики при описании событий.
"""

import re

from dndai.core.colors import CYAN, GREEN, ORANGE, RED, RESET, YELLOW
from dndai.core.i18n import t

# ── База известного снаряжения (частичное совпадение по имени) ──
WEAPONS = {
    "кинжал": "1d4", "нож": "1d4", "посох": "1d6", "копьё": "1d6",
    "меч": "1d8", "топор": "1d8", "булава": "1d8", "молот": "1d8",
    "лук": "1d8", "арбалет": "1d10", "секира": "1d10", "катана": "1d10",
    "моноклинок": "2d4", "виброклинок": "1d10",
}
ARMORS = {
    "щит": 2,
    "стёганая куртка": 1, "кожаная броня": 1, "куртка": 1,
    "кираса": 2, "кольчуга": 3, "броня": 3, "латы": 5,
    "армор": 3, "имплант": 1,
}


def _lookup(db, item):
    """Ищет предмет в базе по подстроке. Возвращает значение или None."""
    it = (item or "").lower()
    best = None
    for name, val in db.items():
        if name in it and (best is None or len(name) > len(best[0])):
            best = (name, val)
    return best[1] if best else None


# ── Расы: бонусы к характеристикам при создании ──
RACES = {
    "человек": {"STR": 1, "DEX": 1, "CON": 1, "INT": 1, "WIS": 1, "CHA": 1},
    "эльф": {"DEX": 2},
    "дварф": {"CON": 2},
    "полурослик": {"DEX": 2, "CHA": 1},
    "полуэльф": {"CHA": 1, "DEX": 1},
    "гном": {"INT": 1},
    "полуорк": {"STR": 2, "CON": 1},
    "драконорождённый": {"STR": 2, "CHA": 1},
}

# ── Стартовые наборы по классу: предметы в инвентарь + заклинание ──
CLASS_KITS = {
    "воин": {"items": ["Меч", "Щит"], "equip": ["Меч", "Щит"]},
    "маг": {"items": ["Посох"], "equip": ["Посох"],
            "spell": ("Волшебная стрела", "стрела магической энергии", "", 0, "1d4+1")},
    "жрец": {"items": ["Булава", "Щит"], "equip": ["Булава"],
             "spell": ("Малое лечение", "исцеляет раны", "", 0, "")},
    "разбойник": {"items": ["Кинжал", "Отмычки"], "equip": ["Кинжал"]},
    "следопыт": {"items": ["Лук"], "equip": ["Лук"]},
    "бард": {"items": ["Кинжал"], "equip": ["Кинжал"]},
    "варлок": {"items": ["Кинжал"], "equip": ["Кинжал"],
               "spell": ("Порча", "сглаз противника", "", 0, "1d6")},
    "друид": {"items": ["Посох"], "equip": ["Посох"],
              "spell": ("Лечение", "природная целительная магия", "", 0, "")},
    "паладин": {"items": ["Меч", "Щит"], "equip": ["Меч", "Щит"]},
    "монах": {"items": [], "equip": []},
    "чародей": {"items": ["Кинжал"], "equip": ["Кинжал"],
                "spell": ("Огненный снаряд", "огненный шар в цель", "", 0, "1d6")},
}

# Классы с ячейками заклинаний (см. SpellBook.CASTER_CLASSES) получают
# стартовое заклинание автоматически через CLASS_KITS["spell"].

# Кость хитов по классу (d6..d12); средний прирост = die//2 + 1
HIT_DIE_BY_CLASS = {
    "маг": 6, "чародей": 6, "wizard": 6, "sorcerer": 6,
    "варлок": 8, "бард": 8, "друид": 8, "жрец": 8, "монах": 8,
    "разбойник": 8, "warlock": 8, "bard": 8, "druid": 8, "cleric": 8,
    "monk": 8, "rogue": 8,
    "воин": 10, "паладин": 10, "следопыт": 10,
    "fighter": 10, "paladin": 10, "ranger": 10,
    "варвар": 12, "barbarian": 12,
}

# Оружие, атакующее ловкостью (finesse) или дальнобойное
FINESSE_OR_RANGED = ("кинжал", "нож", "лук", "арбалет", "дротик",
                     "праща", "рапира", "короткий меч", "виброклинок")


def hit_die_avg(char_class):
    """Средний прирост HP за уровень для класса (округление вверх)."""
    die = HIT_DIE_BY_CLASS.get((char_class or "").lower(), 8)
    return die // 2 + 1


def gain_level(character):
    """Поднимает персонажа на уровень: +max_hp (кость хитов + CON), лечение.

    Возвращает новый уровень."""
    character.level = getattr(character, "level", 1) + 1
    gain = max(1, hit_die_avg(character.char_class)
               + ((character.stats.get("CON", 10) - 10) // 2))
    character.max_hp += gain
    character.hp = min(character.max_hp, character.hp + gain)
    return character.level


def sync_with_progression(character, prog_level):
    """Догоняет уровень персонажа до уровня прогрессии (при загрузке сессии).

    Лечит старые сохранения, где CharacterState.level отставал от
    Progression.level: начисляет пропущенные HP и лечит на них же.
    """
    prog_level = max(1, int(prog_level or 1))
    char_level = max(1, int(getattr(character, "level", 1) or 1))
    if prog_level <= char_level:
        character.level = max(character.level, char_level)
        return False
    while character.level < prog_level:
        gain_level(character)
    return True


def apply_race_bonuses(stats, race):
    """Применяет бонусы расы к статам. Возвращает (stats, применённые_бонусы)."""
    bonuses = RACES.get((race or "").lower(), {})
    for stat, bonus in bonuses.items():
        stats[stat] = stats.get(stat, 10) + bonus
    return stats, bonuses


def apply_class_kit(character):
    """Выдаёт стартовый набор класса: предметы, экипировка, заклинание.

    Заклинания кладутся в character.kit_spells (добавит SpellBook позже).
    Возвращает список строк-описаний выданного."""
    kit = CLASS_KITS.get((character.char_class or "").lower())
    if not kit:
        return []
    granted = []
    for item in kit.get("items", []):
        character.inventory.append(item)
    for item in kit.get("equip", []):
        slot, _old = character.equip(item)
        granted.append(f"{item} → {slot}")
    spell = kit.get("spell")
    if spell:
        character.kit_spells = getattr(character, "kit_spells", []) + [spell]
        granted.append(f"{t('char.kit_spell')}: {spell[0]}")
    return granted


class CharacterState:
    def __init__(self, data=None):
        d = data or {}
        self.name = d.get("name", "")
        self.char_class = d.get("class", "")
        self.race = d.get("race", "")
        self.level = d.get("level", 1)
        self.hp = d.get("hp", 10)
        self.max_hp = d.get("max_hp", 10)
        self.ac = d.get("ac", 10)  # класс брони
        self.stats = d.get("stats", {})  # STR DEX CON INT WIS CHA -> значение
        self.inventory = d.get("inventory", [])
        self.gold = max(0, int(d.get("gold", 0)))
        self.notes = d.get("notes", "")
        # Смертельные ранения (D&D 5e): 3 успеха = стабилизирован,
        # 3 провала = смерть. Нат 20 поднимает на ноги, нат 1 = 2 провала.
        ds = d.get("death_saves") or {}
        self.death_saves = {
            "successes": int(ds.get("successes", 0)),
            "failures": int(ds.get("failures", 0)),
            "stabilized": bool(ds.get("stabilized", False)),
        }
        # Экипировка: {"weapon": "Меч" | None, "shield": "Щит" | None,
        #              "armor": "Кольчуга" | None}
        eq = d.get("equipped") or {}
        self.equipped = {
            "weapon": eq.get("weapon"),
            "shield": eq.get("shield"),
            "armor": eq.get("armor"),
        }

    def to_dict(self):
        return {
            "name": self.name,
            "class": self.char_class,
            "race": self.race,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "stats": self.stats,
            "inventory": self.inventory,
            "gold": self.gold,
            "notes": self.notes,
            "death_saves": dict(self.death_saves),
            "equipped": dict(self.equipped),
        }

    # ── Экипировка ──
    def weapon_damage_dice(self):
        """Кость урона экипированного оружия (или кулаки 1d2)."""
        w = self.equipped.get("weapon")
        if w:
            return _lookup(WEAPONS, w) or "1d6"
        return None  # нет оружия — кулак

    def equip_ac_bonus(self):
        """Бонус КД от брони и щита."""
        bonus = 0
        a = self.equipped.get("armor")
        if a:
            bonus += _lookup(ARMORS, a) or 0
        s = self.equipped.get("shield")
        if s:
            bonus += _lookup(ARMORS, s) or 0
        return bonus

    @staticmethod
    def item_slot(item):
        """Определяет слот предмета: shield / armor / weapon."""
        it = (item or "").lower()
        if "щит" in it:
            return "shield"
        if _lookup(ARMORS, it) is not None:
            return "armor"
        if _lookup(WEAPONS, it) is not None or any(w in it for w in
                ("клинок", "меч", "лук", "нож")):
            return "weapon"
        # неизвестное — считаем оружием по умолчанию
        return "weapon"

    def equip(self, item):
        """Надевает предмет из инвентаря. Возвращает (слот, снятое_имя)."""
        slot = self.item_slot(item)
        old = self.equipped.get(slot)
        self.equipped[slot] = item
        return slot, old

    def unequip(self, item=None):
        """Снимает предмет (по имени или всё). Возвращает список снятого."""
        removed = []
        if item:
            for slot, cur in list(self.equipped.items()):
                if cur and (item.lower() in cur.lower()):
                    self.equipped[slot] = None
                    removed.append(cur)
        else:
            for slot, cur in self.equipped.items():
                if cur:
                    removed.append(cur)
                    self.equipped[slot] = None
        return removed

    @property
    def is_dying(self):
        return self.hp <= 0 and not self.death_saves["stabilized"]

    def reset_death_saves(self):
        self.death_saves = {"successes": 0, "failures": 0, "stabilized": False}

    def death_save_roll(self):
        """Один смертельный спасбросок. Возвращает ('rise'|'stabilize'|'success'|'fail'|'dead', бросок)."""
        import random as _r
        roll = _r.randint(1, 20)
        if roll == 20:
            # Натуральная 20: мгновенно встаёшь с 1 HP
            self.hp = 1
            self.reset_death_saves()
            return "rise", roll
        if roll == 1:
            self.death_saves["failures"] += 2
        elif roll >= 10:
            self.death_saves["successes"] += 1
        else:
            self.death_saves["failures"] += 1
        if self.death_saves["failures"] >= 3:
            return "dead", roll
        if self.death_saves["successes"] >= 3:
            self.death_saves["stabilized"] = True
            return "stabilize", roll
        return ("fail" if roll < 10 else "success"), roll

    def stabilize(self):
        """Стабилизация проверкой (медицина/помощь союзника)."""
        self.death_saves["stabilized"] = True

    def modifier(self, stat):
        """Модификатор характеристики: (значение-10)//2"""
        val = self.stats.get(stat.upper(), 10)
        return (val - 10) // 2

    def attack_modifier(self):
        """Модификатор атаки: DEX для finesse/дальнего оружия, иначе STR."""
        w = (self.equipped.get("weapon") or "")
        if any(k in w.lower() for k in FINESSE_OR_RANGED):
            return self.modifier("DEX")
        return self.modifier("STR")

    def prompt_block(self):
        """Блок для системного промпта — бот видит состояние игрока."""
        if not self.name and not self.char_class:
            return ""
        lines = ["[СОСТОЯНИЕ ИГРОКА]"]
        if self.name:
            lines.append(f"Имя: {self.name}")
        if self.char_class:
            race_part = f", {self.race}" if self.race else ""
            lines.append(f"Класс: {self.char_class}{race_part} (ур. {self.level})")
        lines.append(f"HP: {self.hp}/{self.max_hp}  КД: {self.ac}")
        if self.stats:
            stats_str = ", ".join(f"{k}:{v}({self.modifier(k):+d})"
                                  for k, v in self.stats.items())
            lines.append(f"Характеристики: {stats_str}")
        if self.inventory:
            items = ", ".join(self.inventory)
            lines.append(f"Инвентарь: {items}")
        eq = []
        if self.equipped.get("weapon"):
            eq.append(f"{self.equipped['weapon']} ({self.weapon_damage_dice()})")
        if self.equipped.get("armor"):
            eq.append(self.equipped["armor"])
        if self.equipped.get("shield"):
            eq.append(f"{self.equipped['shield']} (+{_lookup(ARMORS, self.equipped['shield']) or 0} КД)")
        if eq:
            lines.append(f"Экипировка: {', '.join(eq)}")
        lines.append(f"Золото: {self.gold} монет")
        if self.notes:
            lines.append(f"Заметки: {self.notes}")
        lines.append("[/СОСТОЯНИЕ ИГРОКА]")
        return "\n".join(lines)


def show_character(state: CharacterState):
    print(f"\n{CYAN}{t('char.status_title')}{RESET}")
    if not state.name and not state.char_class:
        print(f"{YELLOW}{t('char.not_created')}{RESET}")
        print(f"{YELLOW}{t('char.not_created_ex')}{RESET}")
        return
    if state.name:
        print(f"  {GREEN}{t('char.name')}{RESET} {state.name}")
    if state.char_class:
        print(f"  {GREEN}{t('char.class')}{RESET} {state.char_class} (ур. {state.level})")
    hp_col = RED if state.hp < state.max_hp * 0.3 else GREEN
    print(f"  {GREEN}{t('char.hp')}{RESET} {hp_col}{state.hp}/{state.max_hp}{RESET}  "
          f"{GREEN}{t('char.ac')}{RESET} {state.ac}")
    if state.stats:
        stats_str = ", ".join(f"{k}:{v}({state.modifier(k):+d})"
                              for k, v in state.stats.items())
        print(f"  {GREEN}{t('char.stats')}{RESET} {stats_str}")
    if state.inventory:
        print(f"  {GREEN}{t('char.inventory')}{RESET} {', '.join(state.inventory)}")
    if any(state.equipped.values()):
        eq_parts = []
        if state.equipped.get("weapon"):
            eq_parts.append(f"{state.equipped['weapon']} ({state.weapon_damage_dice()})")
        if state.equipped.get("armor"):
            eq_parts.append(state.equipped["armor"])
        if state.equipped.get("shield"):
            eq_parts.append(f"{state.equipped['shield']} (+{_lookup(ARMORS, state.equipped['shield']) or 0})")
        print(f"  {GREEN}{t('char.equipment')}{RESET} {', '.join(eq_parts)}")
    print(f"  {GREEN}{t('char.gold')}{RESET} {ORANGE}{state.gold} 💰{RESET}")
    if state.notes:
        print(f"  {GREEN}{t('char.notes')}{RESET} {state.notes}")


def parse_character_command(text):
    """Парсит команду !персонаж. Возвращает tuple (action, data) или None."""
    text = text.strip()

    m = re.match(r'(?i)!?\s*(урон|damage|ранение)\s+(\d+)', text)
    if m:
        return ("damage", int(m.group(2)))

    m = re.match(r'(?i)!?\s*(лечение|heal|хилл?)\s+(\d+)', text)
    if m:
        return ("heal", int(m.group(2)))

    m = re.match(r'(?i)!?\s*(hp|здоровье)\s+(\d+)', text)
    if m:
        return ("sethp", int(m.group(2)))

    m = re.match(r'(?i)!?\s*инвентарь\s+(добавить|add)\s+(.+)', text)
    if m:
        raw = m.group(2)
        items = [i.strip().strip('«"»') for i in re.split(r'[,\n]', raw) if i.strip()]
        return ("inv_add", items)

    m = re.match(r'(?i)!?\s*инвентарь\s+(удалить|rm|remove)\s+(.+)', text)
    if m:
        raw = m.group(2)
        items = [i.strip().strip('«"»') for i in re.split(r'[,\n]', raw) if i.strip()]
        return ("inv_del", items)

    m = re.match(r'(?i)!?\s*персонаж\s+(.+)', text)
    if m:
        body = m.group(1)
        cs = CharacterState()
        if "|" in body or "," in body:
            parts = re.split(r'[|,]', body)
            parts = [p.strip() for p in parts if p.strip()]
            # Простой формат: Имя, Класс, HP, КД  (если 4 части и 2 последние — числа)
            nums = [p for p in parts if p.lstrip('-').isdigit()]
            if len(parts) >= 2 and len(nums) >= 2 and not any(':' in p for p in parts):
                cs.name = parts[0]
                if len(parts) >= 2:
                    cs.char_class = parts[1]
                cs.hp = max(1, min(9999, int(nums[0])))
                cs.max_hp = cs.hp
                if len(nums) >= 2:
                    cs.ac = max(0, min(40, int(nums[1])))
            else:
                for p in parts:
                    if re.match(r'(?i)hp\s*:', p) or re.match(r'\d+/\d+', p):
                        mm = re.search(r'(\d+)\s*/\s*(\d+)', p)
                        if mm:
                            cs.hp = max(1, min(9999, int(mm.group(1))))
                            cs.max_hp = max(1, min(9999, int(mm.group(2))))
                        continue
                    if re.match(r'(?i)кд\s*:|ac\s*:', p):
                        mm = re.search(r'(\d+)', p)
                        if mm:
                            cs.ac = max(0, min(40, int(mm.group(1))))
                        continue
                    if re.match(r'(?i)(str|dex|con|int|wis|cha)\s*:', p):
                        for stat in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
                            sm = re.search(rf'(?i){stat}\s*:\s*(\d+)', p)
                            if sm:
                                cs.stats[stat] = max(1, min(40, int(sm.group(1))))
                        continue
                    if not cs.name:
                        cs.name = p
                    elif not cs.char_class:
                        cs.char_class = p
        return ("create", cs)

    return None
