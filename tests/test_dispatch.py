#!/usr/bin/env python3
"""Тесты диспетчера команд: порядок HANDLERS, категории, детализация,
квесты через dispatch, регрессии конфликтов."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dndai.game.commands as game_commands
from dndai.commands import GameContext, dispatch
from dndai.game.character import CharacterState
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
)
from dndai.game.world import WorldState


def make_ctx():
    """Минимальный игровой контекст без печати и сети."""
    ctx = GameContext(
        character=CharacterState(
            {
                "name": "Тест",
                "class": "Воин",
                "hp": 20,
                "max_hp": 20,
                "ac": 14,
                "stats": {"STR": 14, "DEX": 12, "CON": 12},
            }
        ),
        world=WorldState({}),
        spells=SpellBook([]),
        prog=Progression({}),
        status=StatusEffects([]),
        quests=Quests({}),
        npcs=NPCs({}),
        timew=TimeWeather({}),
        journal=Journal([]),
        macros=Macros({}),
        style=Style({}),
        session_name="test",
        persist=lambda: None,
        rollback=lambda: False,
        quiet_mode={"on": True},  # тихий режим: меньше цветного мусора
        history=[],
        summary="",
        player_name="Тест",
        compress=lambda h, s, c, o: (h, o),
        shutdown=lambda: None,
        party=None,
        enemies=Enemies([]),
        reputation=Reputation({}),
    )
    return ctx


# ── Порядок обработчиков ─────────────────────────────────────────────────


def test_personazhi_not_swallowed_by_character_create():
    """!персонажи должен попадать в party_list, а не в создание персонажа."""
    ctx = make_ctx()
    result = dispatch("!персонажи", ctx)
    assert result is not None
    # пустая партия → сообщение об отсутствии партии, а не про формат создания
    assert "party.empty" in result.text or "парти" in result.text.lower()


def test_npc_reaches_npc_handler_not_world():
    """!npc Бармен циничный — добавление NPC, а не голос мира."""
    ctx = make_ctx()
    result = dispatch("!npc Бармен циничный", ctx)
    assert result is not None
    assert "Бармен" in ctx.npcs.npcs


# ── Категории и детализация ──────────────────────────────────────────────


def test_category_command_red():
    old = game_commands.forced_model
    try:
        ctx = make_ctx()
        result = dispatch("красный", ctx)
        assert result is not None
        assert game_commands.forced_model == "red"
    finally:
        game_commands.forced_model = old


def test_detail_command_up_down():
    old = game_commands.forced_detail_level
    try:
        game_commands.forced_detail_level = 0
        ctx = make_ctx()
        dispatch("детальнее", ctx)
        assert game_commands.forced_detail_level == 1
        dispatch("короче", ctx)
        assert game_commands.forced_detail_level == 0
    finally:
        game_commands.forced_detail_level = old


def test_detail_command_capped():
    old = game_commands.forced_detail_level
    try:
        game_commands.forced_detail_level = 2
        ctx = make_ctx()
        dispatch("детальнее", ctx)
        assert game_commands.forced_detail_level == 2
    finally:
        game_commands.forced_detail_level = old


# ── Квесты через dispatch ────────────────────────────────────────────────


def test_quest_create_with_verb_like_title():
    """Квест с «глагольным» названием создаётся, а не завершается."""
    ctx = make_ctx()
    result = dispatch("!квест Закрытие гейта: найти ключ", ctx)
    assert result is not None
    titles = [q["title"] for q in ctx.quests.active]
    assert "Закрытие гейта" in titles


def test_quest_complete_flow():
    ctx = make_ctx()
    dispatch("!квест Найти кота", ctx)
    xp_before = ctx.prog.xp
    result = dispatch("!квест готов Найти кота", ctx)
    assert result is not None
    assert ctx.quests.active == []
    assert len(ctx.quests.done) == 1
    assert ctx.prog.xp == xp_before + 100


# ── Отдых и враги ────────────────────────────────────────────────────────


def test_rest_blocked_in_combat():
    ctx = make_ctx()
    ctx.enemies.add("Гоблин", hp=10, ac=10)
    ctx.character.hp = 5
    result = dispatch("!отдых", ctx)
    assert result is not None
    assert len(ctx.enemies) == 1  # бой НЕ стёрт
    assert ctx.character.hp == 5  # лечение не произошло


def test_rest_works_without_enemies():
    ctx = make_ctx()
    ctx.character.hp = 4
    result = dispatch("!отдых", ctx)
    assert result is not None
    assert ctx.character.hp == ctx.character.max_hp


# ── Лечащее заклинание ──────────────────────────────────────────────────


def test_heal_spell_heals_via_cast():
    ctx = make_ctx()
    ctx.spells.set_slots(1, "жрец")
    ctx.spells.add("Малое лечение", desc="исцеляет раны")
    ctx.character.hp = 6
    result = dispatch("!каст Малое лечение", ctx)
    assert result is not None
    assert ctx.character.hp > 6
    assert ctx.spells.slots_used == 1


# ── Статистика ───────────────────────────────────────────────────────────


def test_stats_reset_via_dispatch():
    """`статистика сброс` обнуляет счётчики запросов."""
    from dndai.core.i18n import variants
    from dndai.game import stats as stats_mod

    ctx = make_ctx()
    stats_mod.record_request("Groq", tokens=10, ok=True)
    assert stats_mod._stats["Groq"]["requests"] >= 1
    result = dispatch("статистика сброс", ctx)
    assert result is not None
    assert stats_mod._stats["Groq"]["requests"] == 0
    assert stats_mod._stats["Groq"]["tokens"] == 0
    assert any(v in result.text for v in variants("stats.reset_ok"))


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
        except Exception as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
