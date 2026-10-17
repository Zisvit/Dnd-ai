#!/usr/bin/env python3
"""Тесты для game/character.py — CharacterState"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.game.character import CharacterState, parse_character_command


def test_default_character():
    c = CharacterState()
    assert c.name == ""
    assert c.hp == 10
    assert c.max_hp == 10
    assert c.ac == 10
    assert c.level == 1


def test_from_dict():
    c = CharacterState({"name": "Герой", "class": "Воин", "hp": 30, "max_hp": 30, "ac": 18})
    assert c.name == "Герой"
    assert c.char_class == "Воин"
    assert c.hp == 30
    assert c.max_hp == 30
    assert c.ac == 18


def test_to_dict():
    c = CharacterState({"name": "Тест", "class": "Маг", "hp": 20, "max_hp": 20})
    d = c.to_dict()
    assert d["name"] == "Тест"
    assert d["class"] == "Маг"
    assert d["hp"] == 20


def test_modifier():
    c = CharacterState({"stats": {"STR": 16, "DEX": 10, "INT": 14}})
    assert c.modifier("STR") == 3
    assert c.modifier("DEX") == 0
    assert c.modifier("INT") == 2
    assert c.modifier("WIS") == 0  # default 10


def test_prompt_block_empty():
    c = CharacterState()
    assert c.prompt_block() == ""


def test_prompt_block_full():
    c = CharacterState({"name": "Герой", "class": "Воин", "hp": 25, "max_hp": 30, "ac": 16,
                        "stats": {"STR": 16}})
    block = c.prompt_block()
    assert "Герой" in block
    assert "Воин" in block
    assert "25/30" in block


def test_parse_damage():
    result = parse_character_command("!урон 5")
    assert result == ("damage", 5)


def test_parse_heal():
    result = parse_character_command("!лечение 10")
    assert result == ("heal", 10)


def test_parse_sethp():
    result = parse_character_command("!hp 20")
    assert result == ("sethp", 20)


def test_parse_inv_add():
    result = parse_character_command("!инвентарь добавить Меч, Щит")
    assert result[0] == "inv_add"
    assert "Меч" in result[1]
    assert "Щит" in result[1]


def test_parse_create_simple():
    result = parse_character_command("!персонаж Герой, Воин, 30, 16")
    assert result[0] == "create"
    c = result[1]
    assert c.name == "Герой"
    assert c.char_class == "Воин"
    assert c.hp == 30
    assert c.ac == 16


def test_parse_create_hp_ac():
    result = parse_character_command("!персонаж Маг | HP: 20/20 | КД: 12")
    assert result[0] == "create"
    c = result[1]
    assert c.name == "Маг"
    assert c.hp == 20
    assert c.max_hp == 20
    assert c.ac == 12


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
