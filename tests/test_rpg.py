#!/usr/bin/env python3
"""Тесты RPG-механик: заклинания, уровни, эффекты, враги, репутация,
квесты, NPC, время, журнал, макросы, стиль, парсеры команд."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.core.i18n import t
from dndai.game.rpg import (
    Enemies,
    Journal,
    Macros,
    NPCs,
    Progression,
    Quests,
    Reputation,
    SpellBook,
    StatusEffects,
    Style,
    TimeWeather,
    heal_dice,
    is_heal_spell,
    mob_attack_stats,
    parse_macro_command,
    parse_npc_command,
    parse_quest_command,
    parse_spell_command,
    parse_status_command,
)

# ── Хелперы ──

def test_heal_spell_detection_and_dice():
    assert is_heal_spell({"name": "Лечение ран"}) is True
    assert is_heal_spell({"name": "X", "effect": "heal 2d8"}) is True
    assert is_heal_spell({"name": "Огненный шар", "desc": "урон огнём"}) is False
    assert is_heal_spell({}) is False
    assert heal_dice({"dmg": " 4d6 "}) == "4d6"
    assert heal_dice({"dmg": "2"}) == "2d8"
    assert heal_dice({}) == "2d8"


def test_mob_attack_stats_scale_with_force():
    assert mob_attack_stats({}) == (3, "1d6")
    assert mob_attack_stats({"max_hp": 8}) == (3, "1d6")
    assert mob_attack_stats({"max_hp": 20}) == (4, "1d6+2")
    assert mob_attack_stats({"max_hp": 40}) == (7, "2d6+2")
    assert mob_attack_stats({"max_hp": 100}) == (8, "2d8+3")


# ── Заклинания ──

def test_spellbook_slots_lifecycle():
    sb = SpellBook([])
    assert sb.set_slots(3, "Маг") == 4
    assert sb.use_slot() is True
    assert sb.slots_left == 3
    sb.set_slots(1, "маг")  # ячейки ужались — used клампится
    assert sb.slots_max == 2 and sb.slots_used == 1
    assert sb.use_slot() is True and sb.use_slot() is False
    assert sb.restore_slots() == 2 and sb.slots_left == 2
    assert SpellBook([]).set_slots(5, "Воин") == 0


def test_spellbook_add_update_remove_find():
    sb = SpellBook([])
    assert sb.add("Огонь", desc="жгучий", dmg="2d6", save_dc=14) is True
    assert sb.find("огон")["name"] == "Огонь"
    assert sb.add("огонь", desc="новое описание") is True
    assert len(sb.spells) == 1
    assert sb.spells[0]["desc"] == "новое описание"
    assert sb.add("") is False
    assert sb.find("нет такого") is None
    assert sb.remove("ОГОНЬ") is True
    assert sb.remove("Огонь") is False


def test_spellbook_serialization_formats():
    sb = SpellBook({"spells": [], "slots_used": 2})
    assert sb.slots_used == 2
    assert sb.to_dict()["slots_used"] == 2
    legacy = SpellBook([{"name": "B", "desc": "d", "effect": "", "save_dc": 0, "dmg": ""}])
    assert legacy.spells[0]["name"] == "B" and legacy.slots_used == 0
    bad = SpellBook({"spells": [], "slots_used": "abc"})
    assert bad.slots_used == 0


def test_spellbook_prompt_block():
    assert SpellBook([]).prompt_block() == ""
    sb = SpellBook([])
    sb.set_slots(2, "маг")
    sb.add("Щит", effect="+2 КД")
    block = sb.prompt_block()
    assert "[ЗАКЛИНАНИЯ И СПОСОБНОСТИ ИГРОКА]" in block
    assert "осталось 3 из 3" in block
    assert "Щит" in block


# ── Уровни ──

def test_progression_levels_up_and_bonus():
    p = Progression({})
    assert p.add_xp(0) == [] and p.add_xp(-5) == []
    assert p.add_xp(299) == [] and p.level == 1
    assert p.add_xp(1) == [2]
    assert p.xp == 300 and p.xp_bonus == 1
    assert p.add_xp(600) == [3]
    assert p.xp_for_next == 2700


def test_progression_max_level():
    p = Progression({"level": 20})
    assert p.xp_for_next is None
    assert p.xp_for_current == 355000
    assert p.add_xp(10_000) == [] and p.level == 20
    assert "[ПРОГРЕСС ИГРОКА]" in p.prompt_block()


# ── Статус-эффекты ──

def test_status_normalization_and_merge():
    se = StatusEffects(["защита", {"name": "отравлен", "rounds": 3}])
    assert se.effects == [
        {"name": "защита", "rounds": 1, "magnitude": 0},
        {"name": "отравлен", "rounds": 3, "magnitude": 0},
    ]
    assert se.add("Защита", 2) is True
    assert se.effects[0]["rounds"] == 2  # max(1, 2)
    assert se.add("") is False


def test_status_tick_expiry():
    se = StatusEffects(["отравлен", {"name": "защита", "rounds": 2}])
    assert se.tick() == ["отравлен"]
    assert [e["name"] for e in se.effects] == ["защита"]
    assert se.effects[0]["rounds"] == 1


def test_status_tick_damage(monkeypatch):
    monkeypatch.setattr("dndai.game.rpg.random.randint", lambda a, b: 4)
    se = StatusEffects(["отравлен", "горит"])
    total, parts = se.tick_damage()
    assert total == 5
    assert parts == ["отравление 1", "горение 4"]


def test_status_bonuses():
    se = StatusEffects(["защита", "укрытие", "благословение", "проклятие"])
    assert se.ac_bonus() == 4
    assert se.save_bonus() == 0
    se.remove("проклятие")
    assert se.save_bonus() == 1
    assert se.remove("проклятие") is False


def test_status_prompt_block():
    assert StatusEffects([]).prompt_block() == ""
    block = StatusEffects(["оглушён"]).prompt_block()
    assert "[АКТИВНЫЕ ЭФФЕКТЫ ИГРОКА]" in block and "оглушён" in block


# ── Враги ──

def test_enemies_add_find_damage_kill():
    en = Enemies([])
    e = en.add("Гоблин", hp=10, ac=12, init=7)
    assert e and e["init"] == 7 and e["max_hp"] == 10
    assert en.add("гоблин", hp=5) is None  # дубликат (регистронезависимо)
    en.add("Волк", hp=20, ac=13, init=9)
    assert en.find("гобл")["name"] == "Гоблин"
    assert en.find("нет такого") is None
    assert en.damage("Гоблин", 4) == (4, False)
    assert en.find("Гоблин")["hp"] == 6
    assert en.damage("Гоблин", 100) == (6, True)
    assert en.find("Гоблин") is None and len(en) == 1
    assert en.damage("Гоблин", 5) == (0, False)


def test_enemies_attack_order():
    en = Enemies([])
    en.add("Медленный", hp=5, init=3)
    en.add("Быстрый", hp=5, init=15)
    en.add("Средний", hp=5, init=9)
    assert [e["name"] for e in en.attack_order()] == ["Быстрый", "Средний", "Медленный"]


def test_enemies_clamps_on_load():
    en = Enemies([
        {"name": "A", "hp": 5, "ac": 99, "init": 99},
        {"name": "B", "hp": -3, "ac": -9, "init": 0},
    ])
    assert en.enemies[0]["ac"] == 40 and en.enemies[0]["init"] == 30
    assert en.enemies[1]["hp"] == 1 and en.enemies[1]["ac"] == 0
    assert en.enemies[1]["init"] == 1
    assert en.to_dict()[0] == {"name": "A", "hp": 5, "max_hp": 5, "ac": 40, "init": 30}


def test_enemies_prompt_and_all_dead():
    en = Enemies([])
    assert en.all_dead() is True
    en.add("Гоблин", hp=10)
    assert not en.all_dead()
    block = en.prompt_block()
    assert "[ВРАГИ В АКТИВНОМ БОЮ]" in block
    assert "Гоблин: HP 10/10" in block


# ── Репутация ──

def test_reputation_change_clamps_and_labels():
    rep = Reputation({})
    assert rep.change("корпорация", -20) == -20
    assert rep.change("Корпорация", 500) == 100
    assert rep.change("", 5) is None
    assert rep.change("Гильдия", -500) == -100
    assert rep._label(-50) == "враждебно"
    assert rep._label(-49) == "недоверие"
    assert rep._label(0) == "нейтрально"
    assert rep._label(20) == "дружелюбно"
    assert rep._label(50) == "преданность"


def test_reputation_prompt_sorted():
    rep = Reputation({"Враг": -50, "Друг": 50})
    block = rep.prompt_block()
    assert block.index("Враг") < block.index("Друг")
    assert "- Враг: -50 (враждебно)" in block
    assert Reputation({}).prompt_block() == ""


# ── Квесты ──

def test_quests_add_complete_abandon_ids():
    q = Quests({})
    assert q.add("Найти кота") is True
    assert q.add("найти кота") is False
    assert q.add("Проводить караван", desc="до заката") is True
    assert q.add("   ") is False
    assert q.complete("НАЙТИ КОТА") == "Найти кота"
    assert q.abandon("проводить караван") == "Проводить караван"
    assert q.complete("нет такого") is None
    assert q.add("Третий") is True
    assert q.active[0]["id"] == 3  # id не переиспользуются после complete/abandon
    assert q.done[0]["title"] == "Найти кота"


def test_quests_prompt_block():
    q = Quests({})
    assert q.prompt_block() == ""
    q.add("Найти кота", desc="в подвале")
    block = q.prompt_block()
    assert "[АКТИВНЫЕ КВЕСТЫ]" in block and "Найти кота: в подвале" in block


# ── NPC ──

def test_npcs_add_merge_remove():
    npcs = NPCs({})
    assert npcs.add("{Бармен}", voice="циничный", note="знает слухи") is True
    assert npcs.npcs["Бармен"] == {
        "voice": "циничный", "note": "знает слухи", "relation": "нейтрально"}
    npcs.add("Бармен", note="женат")
    assert npcs.npcs["Бармен"]["voice"] == "циничный"  # merge не затирает голос
    assert npcs.npcs["Бармен"]["note"] == "женат"
    assert npcs.add("") is False
    assert npcs.remove("{Бармен}") is True
    assert npcs.remove("Бармен") is False


def test_npcs_prompt_block():
    npcs = NPCs({"Бармен": {"voice": "циничный", "relation": "дружелюбно", "note": "женат"}})
    block = npcs.prompt_block()
    assert "[ИЗВЕСТНЫЕ NPC]" in block
    assert "Бармен" in block and "голос=циничный" in block
    assert NPCs({}).prompt_block() == ""


# ── Время и погода ──

def test_timeweather_advance_and_weather():
    tw = TimeWeather({"hour": 23, "day": 1})
    tw.advance(2)
    assert (tw.day, tw.hour) == (2, 1)
    assert tw.set_weather("Дождь") is True and tw.weather == "дождь"
    assert tw.set_weather("Град") is False and tw.weather == "дождь"
    assert tw.to_dict() == {"hour": 1, "day": 2, "weather": "дождь"}


def test_timeweather_part_in_prompt():
    tw = TimeWeather({"hour": 8})
    assert t("rpg.time_part_morning") in tw.prompt_block()
    tw.hour = 3
    assert t("rpg.time_part_late_night") in tw.prompt_block()


# ── Журнал ──

def test_journal_add_cap_and_block():
    j = Journal([])
    assert j.add("  Начало похода  ", day=1, part="утро") is True
    assert j.entries[0] == {"day": 1, "part": "утро", "text": "Начало похода"}
    assert j.add("   ") is False
    for i in range(1, 106):
        j.add(f"запись {i:02d}")
    assert len(j.entries) == 100  # хвост из 100 записей
    assert j.entries[0]["text"] == "запись 06"
    block = j.prompt_block()
    assert "запись 105" in block and "запись 06" not in block  # в промпт — последние 8


# ── Макросы ──

def test_macros_add_expand_remove():
    m = Macros({})
    assert m.add("Бой", "  !атака Гоблин  ") is True
    assert m.macros == {"бой": "!атака Гоблин"}
    assert m.expand("БОЙ") == "!атака Гоблин"
    assert m.expand("нет") is None
    assert m.add("", "x") is False and m.add("x", "") is False
    assert m.remove("Бой") is True and m.remove("бой") is False
    assert m.prompt_block() == ""


# ── Стиль ──

def test_style_set_and_block():
    st = Style({})
    assert st.set_tone("Мрачный") is True and st.tone == "мрачный"
    assert st.set_tone("Хмурый") is False
    assert st.set_genre("Киберпанк") is True and st.genre == "киберпанк"
    assert st.set_genre("Мелодрама") is False
    assert Style({}).prompt_block() == ""
    st2 = Style({"tone": "мрачный", "genre": "киберпанк", "language_style": "рубленые фразы"})
    block = st2.prompt_block()
    assert "[СТИЛЬ ИСТОРИИ]" in block and "Жанр: киберпанк" in block
    assert "Стиль речи: рубленые фразы" in block


# ── Парсеры ──

def test_parse_spell_command():
    assert parse_spell_command("щит") is None
    assert parse_spell_command("!закл Щит") == ("spell_add", ("Щит", "", "", 0))
    assert parse_spell_command("!заклинание Огонь: жгучий | урон 2d6 | СЛ 14") == (
        "spell_add", ("Огонь", "жгучий", "2d6", 14))


def test_parse_quest_command_verbs():
    assert parse_quest_command("!квест Найти кота: в подвале") == (
        "quest_add", ("Найти кота", "в подвале"))
    assert parse_quest_command("!квест готово Найти кота") == ("quest_done", "Найти кота")
    assert parse_quest_command("!квест удалить Найти кота") == ("quest_del", "Найти кота")
    assert parse_quest_command("не квест") is None


def test_parse_npc_command_positional_and_voice():
    assert parse_npc_command("!npc Бармен | циничный | знает слухи") == (
        "npc_add", ("Бармен", "циничный", "знает слухи", ""))
    assert parse_npc_command("!npc Бармен голос: грубый")[1][1] == "грубый"
    assert parse_npc_command("просто текст") is None


def test_parse_npc_and_macro_delete_forms():
    # Регрессия: «удалить» — форма удаления, а не добавление
    assert parse_npc_command("!npc удалить Бармен") is None
    assert parse_npc_command("!npc удал Бармен") is None
    assert parse_macro_command("!макрос удалить бой") == ("macro_del", "бой")
    assert parse_macro_command("!макрос бой = !атака Гоблин") == (
        "macro_add", ("бой", "!атака Гоблин"))


def test_parse_status_command():
    assert parse_status_command("!статус-эффект отравлен 3") == (
        "status_add", ("отравлен", 3))
    assert parse_status_command("!статус-эффект Защита") == ("status_add", ("защита", 1))
    assert parse_status_command("!эффект Защита") is None
