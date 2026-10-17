#!/usr/bin/env python3
"""Тесты мира: WorldState, показ, парсер команд."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.core.i18n import t
from dndai.game.world import WorldState, parse_world_command, show_map, show_world


def test_world_roundtrip_preserves_all_fields():
    data = {
        "location": "Лагерь",
        "visited": ["Лагерь"],
        "facts": ["Врата закрыты"],
        "npc_voices": {"Иван": "грубый"},
        "connections": {"Лагерь": ["Пещера"]},
    }
    assert WorldState(data).to_dict() == data


def test_set_location_tracks_visited_without_duplicates():
    w = WorldState({})
    w.set_location("Лагерь")
    w.set_location("Пещеры")
    assert w.location == "Пещеры"
    assert w.visited == ["Лагерь", "Пещеры"]
    w.set_location("Лагерь")
    assert w.visited == ["Лагерь", "Пещеры"]  # возврат не дублирует
    w.set_location("   ")
    assert w.location == "Лагерь"  # пустая локация игнорируется


def test_add_fact_strips_punctuation_and_dedups():
    w = WorldState({})
    assert w.add_fact("  Дракон мёртв. ") is True
    assert w.facts == ["Дракон мёртв"]
    assert w.add_fact("Дракон мёртв") is False
    assert w.add_fact("   ") is False


def test_connect_is_bidirectional_and_guards():
    w = WorldState({})
    assert w.connect("<<Лагерь>>", "<Пещера>") is True
    assert w.neighbors("Лагерь") == ["Пещера"]
    assert w.neighbors("Пещера") == ["Лагерь"]
    assert w.connect("Лагерь", "Лагерь") is False
    assert w.connect("", "Пещера") is False
    assert w.connect("Лагерь", "Пещера") is True  # повтор без дублей
    assert w.neighbors("Лагерь") == ["Пещера"]


def test_set_voice_requires_known_tag():
    w = WorldState({})
    assert w.set_voice("Кузнец", "грубый") is True
    assert w.npc_voices == {"Кузнец": "грубый"}
    assert w.set_voice("Кузнец", "писклявый") is False
    assert w.set_voice("", "грубый") is False


def test_prompt_block_contains_sections():
    w = WorldState({
        "location": "Лагерь",
        "facts": ["Врата закрыты"],
        "npc_voices": {"Иван": "грубый"},
        "connections": {"Лагерь": ["Пещера"]},
    })
    block = w.prompt_block()
    assert "[МИР]" in block
    assert "<<Лагерь>>" in block
    assert "Врата закрыты" in block
    assert "Иван" in block
    assert "КАРТА связей" in block


def test_prompt_block_empty_world_is_empty():
    assert WorldState({}).prompt_block() == ""


def test_parse_world_command_variants():
    assert parse_world_command("!мир") == ("show", None)
    assert parse_world_command("!карта") == ("map", None)
    assert parse_world_command("связь А Б") == ("connect", ("А", "Б"))
    assert parse_world_command("!идти <<Пещеры>>") == ("goto", "Пещеры")
    assert parse_world_command("!локация Тракт") == ("goto", "Тракт")
    assert parse_world_command("!факт Врата закрыты") == ("fact", "Врата закрыты")
    assert parse_world_command("!голос {Иван} ГРУБЫЙ") == ("voice", ("Иван", "грубый"))
    assert parse_world_command("просто текст") is None


def test_show_world_and_map_smoke(capsys):
    w = WorldState({
        "location": "Лагерь",
        "visited": ["Лагерь"],
        "facts": ["Врата закрыты"],
        "npc_voices": {"Иван": "грубый"},
        "connections": {"Лагерь": ["Пещера"]},
    })
    show_world(w)
    show_map(w)
    out = capsys.readouterr().out
    assert "Лагерь" in out and "Врата закрыты" in out and "Пещера" in out

    show_map(WorldState({}))
    assert t("world.map_empty") in capsys.readouterr().out
