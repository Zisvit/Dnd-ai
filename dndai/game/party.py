"""Партия игроков в одной сессии.

Позволяет нескольким людям играть в одном мире: у каждого свой
персонаж со своим именем, характеристиками и инвентарём. Активный
персонаж (чья сейчас очередь) определяет имя в промпте и в выводе.

Состояние сериализуется как список dict'ов персонажей + индекс активного.
Для обратной совместимости принимает и один dict (старый формат).
"""
from dndai.game.character import CharacterState


class Party:
    def __init__(self, data=None):
        if isinstance(data, dict):
            if data.get("__party__"):
                # новый формат: партия с сохранённым активным индексом
                self.chars = [CharacterState(d) for d in data.get("chars", [])]
                self.active = max(0, min(data.get("active", 0), len(self.chars) - 1)) \
                    if self.chars else 0
            elif data:
                # старый формат: один персонаж
                self.chars = [CharacterState(data)]
                self.active = 0
            else:
                # пустой dict = новая сессия, партия пуста
                self.chars = []
                self.active = 0
        elif isinstance(data, list):
            self.chars = [CharacterState(d) for d in data]
            self.active = 0
        else:
            self.chars = []
            self.active = 0

    # ── доступ ──
    @property
    def active_character(self):
        if not self.chars:
            return None
        return self.chars[self.active]

    @property
    def active_name(self):
        c = self.active_character
        return c.name if c else "player"

    def names(self):
        return [c.name or f"Безымянный{i+1}" for i, c in enumerate(self.chars)]

    # ── управление ──
    def add(self, character: CharacterState):
        self.chars.append(character)
        self.active = len(self.chars) - 1
        return True

    def switch(self, name):
        """Переключить активного по имени. Возвращает персонажа или None.

        Сначала точное совпадение, затем — частичное (подстрока),
        чтобы можно было переключать имя из нескольких слов одним словом.
        """
        name_l = (name or "").lower().strip()
        if not name_l:
            return None
        # точное совпадение
        for i, c in enumerate(self.chars):
            if (c.name or "").lower() == name_l:
                self.active = i
                return c
        # частичное совпадение (подстрока)
        for i, c in enumerate(self.chars):
            if name_l in (c.name or "").lower():
                self.active = i
                return c
        return None

    def rename_active(self, new_name):
        c = self.active_character
        if c:
            c.name = new_name
            return True
        return False

    def replace_active(self, character):
        """Заменить активного персонажа новым (используется командой !персонаж)."""
        if not self.chars:
            self.chars.append(character)
            self.active = 0
            return True
        self.chars[self.active] = character
        return True

    def remove(self, name):
        for i, c in enumerate(self.chars):
            if (c.name or "").lower() == name.lower():
                self.chars.pop(i)
                # Удалили персонажа ПЕРЕД активным — указатель смещается
                if i < self.active:
                    self.active -= 1
                # Активный был последним — сдвигаем к новому концу
                if self.active >= len(self.chars):
                    self.active = max(0, len(self.chars) - 1)
                return True
        return False

    def to_dict(self):
        return {"__party__": True, "active": self.active,
                "chars": [c.to_dict() for c in self.chars]}

    def prompt_block(self):
        if not self.chars:
            return ""
        lines = ["[ПАРТИЯ ИГРОКОВ]"]
        for i, c in enumerate(self.chars):
            mark = " ▶" if i == self.active else ""
            lines.append(f"{i+1}. {c.name or 'Безымянный'} "
                         f"({c.char_class}, ур. {c.level}, HP {c.hp}/{c.max_hp}){mark}")
        lines.append("[/ПАРТИЯ]")
        return "\n".join(lines)
