#!/usr/bin/env python3
"""Тесты для game/session.py, game/party.py, game/world.py, game/rpg.py"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.game.session import (
    load_game_session,
    save_game_session,
    compress_if_needed,
    get_player_name_from_history,
)
from dndai.game.party import Party
from dndai.game.world import WorldState
from dndai.game.character import CharacterState
from dndai.game.rpg import (
    SpellBook,
    Progression,
    StatusEffects,
    Quests,
    TimeWeather,
    Macros,
    parse_spell_command,
    parse_quest_command,
    parse_macro_command,
)


# ── Party ──


def test_party_empty():
    p = Party()
    assert p.chars == []
    assert p.active == 0
    assert p.active_character is None
    assert p.active_name == "player"


def test_party_single_char():
    c = CharacterState({"name": "Герой", "class": "Воин"})
    p = Party()
    p.add(c)
    assert len(p.chars) == 1
    assert p.active_character.name == "Герой"


def test_party_switch():
    c1 = CharacterState({"name": "Герой"})
    c2 = CharacterState({"name": "Маг"})
    p = Party()
    p.add(c1)
    p.add(c2)
    result = p.switch("Маг")
    assert result is not None
    assert result.name == "Маг"
    assert p.active == 1


def test_party_switch_partial():
    c1 = CharacterState({"name": "Герой Воин"})
    p = Party()
    p.add(c1)
    result = p.switch("Воин")
    assert result is not None


def test_party_switch_not_found():
    c1 = CharacterState({"name": "Герой"})
    p = Party()
    p.add(c1)
    result = p.switch("Несуществующий")
    assert result is None


def test_party_to_dict():
    c = CharacterState({"name": "Тест", "class": "Маг"})
    p = Party()
    p.add(c)
    d = p.to_dict()
    assert d["__party__"] is True
    assert len(d["chars"]) == 1
    assert d["active"] == 0


def test_party_from_dict():
    d = {
        "__party__": True,
        "active": 0,
        "chars": [{"name": "А", "class": "В"}, {"name": "Б", "class": "М"}],
    }
    p = Party(d)
    assert len(p.chars) == 2
    assert p.active == 0


def test_party_old_format():
    d = {"name": "Старый", "class": "Воин", "hp": 10}
    p = Party(d)
    assert len(p.chars) == 1
    assert p.chars[0].name == "Старый"


def test_party_remove():
    c1 = CharacterState({"name": "А"})
    c2 = CharacterState({"name": "Б"})
    p = Party()
    p.add(c1)
    p.add(c2)
    p.active = 0
    assert p.remove("А") is True
    assert len(p.chars) == 1
    assert p.chars[0].name == "Б"


def test_party_remove_last():
    p = Party()
    p.add(CharacterState({"name": "Один"}))
    assert p.remove("Один") is True
    assert len(p.chars) == 0
    assert p.active == 0


def test_party_remove_not_found():
    p = Party()
    p.add(CharacterState({"name": "А"}))
    assert p.remove("Нет такой") is False
    assert len(p.chars) == 1


def test_party_rename():
    c = CharacterState({"name": "Старое"})
    p = Party()
    p.add(c)
    assert p.rename_active("Новое") is True
    assert p.chars[0].name == "Новое"


# ── World ──


def test_world_empty():
    w = WorldState()
    assert w.location == ""
    assert w.facts == []


def test_world_set_location():
    w = WorldState()
    w.set_location("Таверна")
    assert w.location == "Таверна"
    assert "Таверна" in w.visited


def test_world_set_location_old_visited():
    w = WorldState({"location": "Лес"})
    w.set_location("Город")
    assert w.location == "Город"
    assert "Лес" in w.visited
    assert "Город" in w.visited


def test_world_add_fact():
    w = WorldState()
    assert w.add_fact("Факт 1") is True
    assert "Факт 1" in w.facts
    assert w.add_fact("Факт 1") is False  # duplicate


def test_world_connect():
    w = WorldState()
    assert w.connect("Таверна", "Лес") is True
    assert "Лес" in w.connections["Таверна"]
    assert "Таверна" in w.connections["Лес"]


def test_world_connect_same():
    w = WorldState()
    assert w.connect("Таверна", "Таверна") is False


def test_world_neighbors():
    w = WorldState(
        {"location": "Таверна", "connections": {"Таверна": ["Лес", "Город"]}}
    )
    assert w.neighbors() == ["Лес", "Город"]


def test_world_to_dict():
    w = WorldState({"location": "Таверна", "facts": ["Факт"]})
    d = w.to_dict()
    assert d["location"] == "Таверна"
    assert "Факт" in d["facts"]


# ── SpellBook ──


def test_spellbook_add():
    sb = SpellBook()
    assert sb.add("Огонь", "Урон", dmg="2d6") is True
    assert len(sb.spells) == 1


def test_spellbook_duplicate():
    sb = SpellBook()
    sb.add("Огонь", "Урон")
    assert sb.add("Огонь", "Новый") is True
    assert sb.spells[0]["desc"] == "Новый"


def test_spellbook_remove():
    sb = SpellBook()
    sb.add("Огонь")
    assert sb.remove("Огонь") is True
    assert len(sb.spells) == 0


def test_spellbook_find():
    sb = SpellBook()
    sb.add("Огненный шар")
    s = sb.find("шар")
    assert s is not None
    assert s["name"] == "Огненный шар"


def test_spellbook_to_dict():
    sb = SpellBook()
    sb.add("Тест")
    d = sb.to_dict()
    assert isinstance(d, dict)
    assert len(d["spells"]) == 1
    assert d["spells"][0]["name"] == "Тест"


def test_spellbook_slots():
    sb = SpellBook(
        {"spells": [{"name": "Огненный шар", "dmg": "8d6"}], "slots_used": 2}
    )
    assert sb.set_slots(3, "маг") == 4  # маг 3 уровня → 4 ячейки
    assert sb.slots_used <= sb.slots_max
    assert sb.use_slot() and sb.slots_left == sb.slots_max - sb.slots_used
    sb.restore_slots()
    assert sb.slots_left == sb.slots_max
    non_caster = SpellBook([])
    assert non_caster.set_slots(5, "воин") == 0


# ── Progression ──


def test_progression_default():
    p = Progression()
    assert p.level == 1
    assert p.xp == 0


def test_progression_add_xp():
    p = Progression()
    leveled = p.add_xp(300)
    assert leveled == [2]
    assert p.level == 2
    assert p.xp_bonus == 1


def test_progression_add_xp_no_level():
    p = Progression()
    leveled = p.add_xp(100)
    assert leveled == []
    assert p.level == 1


def test_progression_max_level():
    p = Progression({"level": 20, "xp": 355000})
    leveled = p.add_xp(100000)
    assert leveled == []
    assert p.level == 20


# ── StatusEffects ──


def test_status_add():
    s = StatusEffects()
    assert s.add("оглушён", 2) is True
    assert len(s.effects) == 1


def test_status_tick():
    s = StatusEffects()
    s.add("оглушён", 1)
    expired = s.tick()
    assert "оглушён" in expired
    assert len(s.effects) == 0


def test_status_tick_damage():
    s = StatusEffects()
    s.add("отравлен", 3)
    total, parts = s.tick_damage()
    assert total == 1
    assert "отравление" in parts[0]


def test_status_ac_bonus():
    s = StatusEffects()
    s.add("защита", 3)
    assert s.ac_bonus() == 2


def test_status_save_bonus():
    s = StatusEffects()
    s.add("благословение", 5)
    assert s.save_bonus() == 1


# ── Quests ──


def test_quest_add():
    q = Quests()
    assert q.add("Убить дракона", "Найти и убить") is True
    assert len(q.active) == 1


def test_quest_complete():
    q = Quests()
    q.add("Убить дракона")
    title = q.complete("убить дракона")
    assert title == "Убить дракона"
    assert len(q.active) == 0
    assert len(q.done) == 1


def test_quest_abandon():
    q = Quests()
    q.add("Найти меч")
    title = q.abandon("найти меч")
    assert title == "Найти меч"
    assert len(q.active) == 0


# ── TimeWeather ──


def test_time_advance():
    tw = TimeWeather({"hour": 23})
    tw.advance(2)
    assert tw.hour == 1
    assert tw.day == 2


def test_weather_set():
    tw = TimeWeather()
    assert tw.set_weather("дождь") is True
    assert tw.weather == "дождь"
    assert tw.set_weather("хрен") is False


# ── Macros ──


def test_macro_add():
    m = Macros()
    assert m.add("атака", "!бой Гоблин 12") is True
    assert m.expand("атака") == "!бой Гоблин 12"


def test_macro_expand_unknown():
    m = Macros()
    assert m.expand("несуществующий") is None


def test_macro_remove():
    m = Macros()
    m.add("тест", "!мир")
    assert m.remove("тест") is True
    assert m.expand("тест") is None


# ── Parsers ──


def test_parse_spell():
    result = parse_spell_command("!заклинание Огонь: Жгёт | урон 2d6 | сл 15")
    assert result[0] == "spell_add"
    name, desc, dmg, dc = result[1]
    assert name == "Огонь"
    assert dmg == "2d6"
    assert dc == 15


def test_parse_quest():
    result = parse_quest_command("!квест Дракон: Убить старого дракона")
    assert result[0] == "quest_add"
    assert result[1][0] == "Дракон"


def test_parse_quest_complete():
    result = parse_quest_command("!квест готов Дракон")
    assert result[0] == "quest_done"
    assert result[1] == "Дракон"


def test_parse_quest_prefix_not_verb():
    """Название квеста, начинающееся с глагольного префикса, — это
    СОЗДАНИЕ квеста, а не завершение (регрессия жадных префиксов)."""
    result = parse_quest_command("!квест Закрытие гейта: найти ключ")
    assert result[0] == "quest_add"
    assert result[1][0] == "Закрытие гейта"
    result2 = parse_quest_command("!квест Готовое оружие забрать у кузнеца")
    assert result2[0] == "quest_add"
    assert result2[1][0] == "Готовое оружие забрать у кузнеца"


def test_parse_macro():
    result = parse_macro_command("!макрос бой = !бой Гоблин 12")
    assert result[0] == "macro_add"
    assert result[1][0] == "бой"


# ── Session ──


def test_session_roundtrip(tmp_path=None, monkeypatch=None):
    """roundtrip сохранения; пишем во временную папку, не в dnd_sessions."""
    import dndai.game.session as session_mod

    real_tmp = tmp_path or __import__("pathlib").Path(
        tempfile.mkdtemp(prefix="dnd_test_")
    )
    if monkeypatch:
        monkeypatch.setattr(session_mod, "SESSION_DIR", real_tmp)
        old = None
    else:
        old = session_mod.SESSION_DIR
        session_mod.SESSION_DIR = real_tmp
    try:
        history = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Мир"},
        ]
        save_game_session("test_session", history, summary="Тест", state={"hp": 10})
        h2, mem, summ, state, world, rpg = load_game_session("test_session")
        assert len(h2) == 2
        assert h2[0]["content"] == "Привет"
        assert summ == "Тест"
        assert state["hp"] == 10
    finally:
        if monkeypatch is None:
            session_mod.SESSION_DIR = old


def test_session_corrupt_history(tmp_path=None, monkeypatch=None):
    import dndai.game.session as session_mod

    real_tmp = tmp_path or __import__("pathlib").Path(
        tempfile.mkdtemp(prefix="dnd_test_")
    )
    if monkeypatch:
        monkeypatch.setattr(session_mod, "SESSION_DIR", real_tmp)
        old = None
    else:
        old = session_mod.SESSION_DIR
        session_mod.SESSION_DIR = real_tmp
    try:
        history = ["not a dict", 42, None, {"role": "user", "content": "OK"}]
        save_game_session("test_corrupt", history)
        h2, *_ = load_game_session("test_corrupt")
        assert len(h2) == 4
        assert h2[3]["content"] == "OK"
    finally:
        if monkeypatch is None:
            session_mod.SESSION_DIR = old


def test_player_name_from_history():
    history = [
        {"role": "user", "content": "Привет"},
        {"role": "assistant", "content": "Теперь тебя зовут Артур"},
    ]
    name = get_player_name_from_history(history)
    assert name == "Артур"


def test_player_name_default():
    history = [{"role": "user", "content": "Привет"}]
    name = get_player_name_from_history(history, "hero")
    assert name == "hero"


def test_compress_threshold():
    """compress_if_needed не сжимает при <= 30 сообщений."""
    history = [{"role": "user", "content": f"msg {i}"} for i in range(30)]
    h2, s = compress_if_needed(history, "test", None, "old_summary")
    assert len(h2) == 30
    assert s == "old_summary"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
