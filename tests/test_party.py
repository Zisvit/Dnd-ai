#!/usr/bin/env python3
"""Тесты партии: форматы данных, активный персонаж, управление."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.game.character import CharacterState
from dndai.game.party import Party


def _char(name, cls="Воин", hp=20):
    return CharacterState(
        {"name": name, "class": cls, "hp": hp, "max_hp": hp, "ac": 14}
    )


def test_empty_data_gives_empty_party():
    for data in (None, {}, []):
        p = Party(data)
        assert p.chars == []
        assert p.active_character is None
        assert p.active_name == "player"


def test_legacy_single_character_format():
    p = Party({"name": "Герой", "class": "Маг", "hp": 10, "max_hp": 10})
    assert len(p.chars) == 1
    assert p.chars[0].name == "Герой"
    assert p.active == 0


def test_list_format_starts_from_first():
    p = Party([{"name": "Аня"}, {"name": "Боря"}])
    assert [c.name for c in p.chars] == ["Аня", "Боря"]
    assert p.active == 0


def test_roundtrip_preserves_active_index():
    p = Party([{"name": "Аня"}, {"name": "Боря"}])
    p.switch("Боря")
    data = p.to_dict()
    assert data["__party__"] is True
    p2 = Party(data)
    assert [c.name for c in p2.chars] == ["Аня", "Боря"]
    assert p2.active == 1
    assert p2.active_name == "Боря"


def test_active_index_clamped_on_load():
    p = Party({"__party__": True, "active": 99, "chars": [{"name": "Аня"}]})
    assert p.active == 0
    p2 = Party({"__party__": True, "active": -5, "chars": [{"name": "Аня"}]})
    assert p2.active == 0


def test_add_switch_and_names():
    p = Party({})
    p.add(_char("Аня"))
    p.add(_char("Боря", cls="Маг"))
    assert p.active == 1 and p.active_name == "Боря"
    assert p.switch("аня").name == "Аня"
    assert p.active == 0
    assert p.switch("бор").name == "Боря"  # частичное совпадение
    assert p.switch("никого") is None
    assert p.switch("") is None


def test_names_placeholder_for_unnamed():
    p = Party([{"name": ""}])
    assert p.names() == ["Безымянный1"]


def test_rename_active():
    p = Party({})
    assert p.rename_active("Кто-то") is False
    p.add(_char("Аня"))
    assert p.rename_active("Анюта") is True
    assert p.active_name == "Анюта"


def test_replace_active():
    p = Party({})
    assert p.replace_active(_char("Нов")) is True
    assert p.active_name == "Нов"
    p.replace_active(_char("Замена"))
    assert len(p.chars) == 1 and p.active_name == "Замена"


def test_remove_before_active_shifts_pointer():
    p = Party([{"name": "А"}, {"name": "Б"}, {"name": "В"}])
    p.switch("В")
    assert p.remove("А") is True
    assert [c.name for c in p.chars] == ["Б", "В"]
    assert p.active_name == "В"
    assert p.remove("нет такого") is False


def test_remove_active_last_moves_pointer_back():
    p = Party([{"name": "А"}, {"name": "Б"}])
    p.switch("Б")
    assert p.remove("Б") is True
    assert p.active == 0 and p.active_name == "А"


def test_prompt_block_marks_active():
    p = Party([{"name": "Аня"}, {"name": "Боря"}])
    p.switch("Боря")
    block = p.prompt_block()
    assert "[ПАРТИЯ ИГРОКОВ]" in block
    assert "Боря" in block and "▶" in block
    assert Party({}).prompt_block() == ""
