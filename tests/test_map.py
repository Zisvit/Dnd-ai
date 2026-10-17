#!/usr/bin/env python3
"""Тесты карты v1: nodes/map_view, зум обзора, !место, !идти, рендер."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.commands import dispatch
from dndai.commands.world_cmds import map_show, world_command
from dndai.core.i18n import t
from dndai.game.world import (
    SCALE_LADDER,
    WorldState,
    parse_scale,
    parse_world_command,
    scale_display,
    show_map,
    show_map_all,
)
from tests.test_dispatch import make_ctx

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def design_world():
    """Мир из дизайна: полная лестница от Таверны до галактики."""

    return WorldState(
        {
            "location": "Таверна",
            "visited": ["Таверна"],
            "nodes": {
                "Таверна": {"parent": "Рыночный квартал", "scale": "строение"},
                "Рыночный квартал": {"parent": "Туманск", "scale": "квартал"},
                "Туманск": {"parent": "Весталия", "scale": "город"},
                "Устье": {"parent": "Весталия", "scale": "город"},
                "Весталия": {"parent": "Терра", "scale": "страна"},
                "Терра": {"parent": "Система Тумана", "scale": "планета"},
                "Система Тумана": {"parent": "Млечный Путь", "scale": "система"},
                "Млечный Путь": {"parent": None, "scale": "галактика"},
            },
            "connections": {"Туманск": ["Устье"], "Устье": ["Туманск"]},
        }
    )


# ── Данные и миграция ────────────────────────────────────────────────────


def test_roundtrip_nodes_and_map_view():
    data = {
        "location": "Туманск",
        "visited": ["Туманск"],
        "facts": [],
        "npc_voices": {},
        "connections": {},
        "markets": {},
        "trade_goods": {},
        "nodes": {"Туманск": {"parent": "Весталия", "scale": "город"}},
        "map_view": "страна",
    }
    assert WorldState(data).to_dict() == data


def test_lazy_migration_old_sessions_unchanged():
    data = {
        "location": "Лагерь",
        "visited": ["Лагерь"],
        "facts": [],
        "npc_voices": {},
        "connections": {},
        "markets": {},
        "trade_goods": {},
    }
    out = WorldState(data).to_dict()
    assert out == data
    assert "nodes" not in out and "map_view" not in out


# ── Парсер и уровни ──────────────────────────────────────────────────────


def test_parse_map_arg_and_place_forms():
    assert parse_world_command("!карта") == ("map", None)
    assert parse_world_command("!карта вверх") == ("map", "вверх")
    assert parse_world_command("!карта всё") == ("map", "всё")
    assert parse_world_command("!карта страна") == ("map", "страна")
    assert parse_world_command("!место Тракт в Город") == ("place", ("Тракт", "Город"))
    assert parse_world_command("!место Тракт уровень квартал") == (
        "place_level",
        ("Тракт", "квартал"),
    )
    assert parse_world_command("!место Тракт level city") == (
        "place_level",
        ("Тракт", "city"),
    )
    assert parse_world_command("место Тракт в Город") is None
    assert parse_world_command("!местный житель пришёл") is None


def test_scale_aliases_and_display():
    assert parse_scale("city") == "город"
    assert parse_scale("ГОРОД") == "город"
    assert parse_scale("скопление") == "скопление"
    assert parse_scale(None) is None
    assert scale_display("город") == t("world.scale_city")
    assert scale_display("city") == t("world.scale_city")
    assert scale_display("скопление") == "скопление"
    assert scale_display("") == ""
    assert len(SCALE_LADDER) == 7


# ── !место ───────────────────────────────────────────────────────────────


def test_place_infers_scale_from_siblings_then_parent():
    ctx = make_ctx()
    w = ctx.world
    w.nodes = {
        "Туманск": {"scale": "город"},
        "Рынок": {"parent": "Туманск", "scale": "квартал"},
    }
    res = world_command("!место Порт в Туманск", ctx)
    assert w.nodes["Порт"]["parent"] == "Туманск"
    assert w.nodes["Порт"]["scale"] == "квартал"  # как у брата
    assert "Порт" in res.text
    # без братьев — ступень ниже родителя
    world_command("!место Стойка в Порт", ctx)
    assert w.nodes["Стойка"]["scale"] == "строение"


def test_place_level_explicit_and_unknown():
    ctx = make_ctx()
    w = ctx.world
    world_command("!место Тракт уровень город", ctx)
    assert w.nodes["Тракт"]["scale"] == "город"
    world_command("!место Тракт уровень building", ctx)
    assert w.nodes["Тракт"]["scale"] == "строение"  # EN-алиас → канон
    res = world_command("!место Тракт уровень скопление", ctx)
    assert w.nodes["Тракт"]["scale"] == "скопление"  # неизвестная метка живёт
    assert "Тракт" in res.text


def test_place_guard_cycle_and_self():
    ctx = make_ctx()
    w = ctx.world
    world_command("!место А в Б", ctx)
    assert w.parent_of("А") == "Б"
    res = world_command("!место Б в А", ctx)  # цикл
    assert w.parent_of("Б") is None
    assert w.parent_of("А") == "Б"
    assert "Б" in res.text
    res2 = world_command("!место А в А", ctx)  # сам в себя
    assert w.parent_of("А") == "Б"
    assert res2 is not None


# ── !идти ────────────────────────────────────────────────────────────────


def test_goto_new_place_grows_tree_and_resets_view():
    ctx = make_ctx()
    w = ctx.world
    w.set_location("Туманск")
    w.nodes = {"Туманск": {"parent": "Весталия", "scale": "город"}}
    w.map_view = "страна"
    world_command("!идти Порт", ctx)
    assert w.location == "Порт"
    assert w.nodes["Порт"]["parent"] == "Туманск"
    assert w.nodes["Порт"]["scale"] == "квартал"  # ступень ниже города
    assert w.map_view is None  # обзор сброшен на уровень новой локации
    assert "Порт" in w.visited
    assert ctx.timew.hour == 9  # одна поездка — один час


def test_goto_neighbor_parent_child_one_step():
    ctx = make_ctx()
    w = ctx.world
    w.nodes = {
        "Город": {"scale": "город"},
        "Квартал": {"parent": "Город", "scale": "квартал"},
        "Дом": {"parent": "Квартал", "scale": "строение"},
    }
    w.connect("Город", "Тракт")
    w.set_location("Дом")
    world_command("!идти Квартал", ctx)  # родитель
    assert w.location == "Квартал"
    assert ctx.timew.hour == 9
    world_command("!идти Город", ctx)  # родитель
    assert w.location == "Город"
    assert ctx.timew.hour == 10
    world_command("!идти Тракт", ctx)  # сосед
    assert w.location == "Тракт"
    world_command("!идти Город", ctx)  # сосед обратно
    assert w.location == "Город"
    assert ctx.timew.hour == 12
    res = world_command("!идти Дом", ctx)  # известная точка не в одном шаге
    assert w.location == "Город"
    assert ctx.timew.hour == 12  # время не двигалось
    assert "Дом" in res.text


# ── Зум ──────────────────────────────────────────────────────────────────


def test_zoom_steps_edges_and_jump():
    ctx = make_ctx()
    w = ctx.world
    w.nodes = {
        "Таверна": {"parent": "Квартал", "scale": "строение"},
        "Квартал": {"parent": "Город", "scale": "квартал"},
        "Город": {"scale": "город"},
    }
    w.set_location("Таверна")
    map_show("!карта вверх", ctx)
    assert w.map_view == "квартал"
    map_show("!карта +", ctx)
    assert w.map_view == "город"
    map_show("!карта вниз", ctx)
    assert w.map_view == "квартал"
    map_show("!карта -", ctx)
    assert w.map_view == "строение"
    res = map_show("!карта вниз", ctx)  # ниже строения нет
    assert w.map_view == "строение"
    assert t("world.map_zoom_edge") in res.text
    map_show("!карта страна", ctx)  # прыжок к уровню
    assert w.map_view == "страна"
    map_show("!карта вверх", ctx)
    assert w.map_view == "планета"
    assert w.location == "Таверна"  # зум местоположение не меняет


def test_zoom_without_levels_message():
    ctx = make_ctx()
    res = map_show("!карта вверх", ctx)
    assert t("world.map_zoom_none") in res.text
    res2 = map_show("!карта вниз", ctx)
    assert t("world.map_zoom_none") in res2.text


def test_map_unknown_level_hint():
    ctx = make_ctx()
    res = map_show("!карта скопление", ctx)
    assert t("world.scale_city") in res.text  # подсказка со списком уровней


# ── Рендер ───────────────────────────────────────────────────────────────


def test_level_view_render(capsys):
    w = design_world()
    w.map_view = "город"
    show_map(w)
    out = ANSI.sub("", capsys.readouterr().out)
    assert t("world.map_level_title", level=t("world.scale_city")) in out
    assert "Туманск" in out and "Устье" in out
    assert "Млечный Путь ▸ Система Тумана ▸ Терра ▸ Весталия ▸ Туманск" in out
    assert "▸" in out and t("world.map_here") in out
    assert "↔" in out  # связь между точками уровня
    assert t("world.map_down", n=1) in out
    assert "Весталия" in out and t("world.scale_country") in out
    assert t("world.map_hint") in out


def test_level_view_missing_level(capsys):
    w = design_world()
    del w.nodes["Терра"]  # уровень «планета» пропал из ветки
    w.map_view = "планета"
    show_map(w)
    out = ANSI.sub("", capsys.readouterr().out)
    assert t("world.map_level_missing", level=t("world.scale_planet")) in out


def test_map_all_render(capsys):
    w = design_world()
    show_map_all(w)
    out = ANSI.sub("", capsys.readouterr().out)
    assert t("world.map_all_title") in out
    assert "Млечный Путь" in out and "Таверна" in out
    assert out.index("Млечный Путь") < out.index("Таверна")
    assert t("world.scale_galaxy") in out and t("world.scale_building") in out
    assert t("world.map_here") in out


def test_flat_view_without_nodes(capsys):
    w = WorldState(
        {
            "location": "Лагерь",
            "visited": ["Лагерь"],
            "connections": {"Лагерь": ["Пещера"]},
        }
    )
    show_map(w)
    out = ANSI.sub("", capsys.readouterr().out)
    assert t("world.map_title") in out
    assert "Пещера" in out and t("world.map_links") in out


def test_lines_fit_80_columns(capsys):
    w = WorldState(
        {
            "location": "Очень длинное имя локации игрока",
            "visited": ["Очень длинное имя локации игрока"],
            "nodes": {
                "Очень длинное имя локации игрока": {
                    "parent": "Длиннющее название города",
                    "scale": "строение",
                },
                "Длиннющее название города": {
                    "parent": "Огромная страна",
                    "scale": "город",
                },
                "Огромная страна": {"scale": "страна"},
            },
            "connections": {
                "Очень длинное имя локации игрока": [
                    "Ещё один очень длинный сосед города"
                ]
            },
        }
    )
    show_map(w)
    show_map_all(w)
    for line in capsys.readouterr().out.splitlines():
        assert len(ANSI.sub("", line)) <= 80, repr(line)


# ── Промпт мастера ───────────────────────────────────────────────────────


def test_prompt_block_map_section_capped():
    nodes = {
        "Страна": {"scale": "страна"},
        "Город": {"parent": "Страна", "scale": "город"},
    }
    for i in range(50):
        nodes[f"Точка-{i}"] = {"parent": "Город", "scale": "квартал"}
    conns = {f"Точка-{i}": [f"Точка-{i + 1}"] for i in range(0, 50, 2)}
    w = WorldState(
        {
            "location": "Город",
            "visited": ["Город"],
            "nodes": nodes,
            "connections": conns,
        }
    )
    block = w.prompt_block()
    assert "Путь:" in block
    assert "Можно идти:" in block
    assert "… и ещё" in block
    map_lines = [
        line
        for line in block.splitlines()
        if line.startswith(("Путь:", "Можно идти:", "КАРТА связей:"))
    ]
    assert len(map_lines) == 3
    assert sum(len(line) for line in map_lines) <= 900


def test_prompt_block_old_world_has_no_map_lines():
    w = WorldState({"location": "Лагерь", "connections": {"Лагерь": ["Пещера"]}})
    block = w.prompt_block()
    assert "Путь:" not in block  # иерархии нет — пути нет
    assert "Можно идти: <<Пещера>>" in block  # соседи всё равно видны
    assert "КАРТА связей" in block


# ── Диспетчер ────────────────────────────────────────────────────────────


def test_dispatch_handles_map_and_place():
    ctx = make_ctx()
    ctx.world.set_location("Таверна")
    ctx.world.nodes = {"Таверна": {"scale": "строение"}}
    res = dispatch("!карта", ctx)
    assert res is not None and res.text == ""
    res2 = dispatch("!карта вверх", ctx)
    assert res2 is not None and ctx.world.map_view == "квартал"
    res3 = dispatch("!место Таверна в Город", ctx)
    assert res3 is not None
    assert ctx.world.parent_of("Таверна") == "Город"


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
