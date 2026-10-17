#!/usr/bin/env python3
"""Тесты командного слоя: партия, мир/карта, RPG-команды, мета (кости, откат)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.commands.meta_cmds import dice_command, rollback_command
from dndai.commands.party_cmds import (
    party_list,
    party_new,
    party_remove,
    party_rename,
    party_switch,
)
from dndai.commands.rpg_cmds import (
    check_command,
    enemy_add_command,
    journal_command,
    macro_command,
    quest_command,
    quiet_command,
    reputation_command,
    rest_command,
    spell_command,
    stabilize_command,
    status_command,
    style_command,
    time_command,
    weather_command,
    xp_command,
)
from dndai.commands.world_cmds import map_connect, map_show, npc_command, world_command
from dndai.core.i18n import t
from dndai.game.party import Party
from dndai.game.rpg import Reputation
from tests.test_dispatch import make_ctx

# ── Партия ──


def test_party_list_empty_and_filled():
    ctx = make_ctx()
    res = party_list("!персонажи", ctx)
    assert res is not None and t("party.empty") in res.text
    ctx.party = Party([{"name": "Аня"}, {"name": "Боря"}])
    res2 = party_list("партия", ctx)
    assert "Аня" in res2.text and "Боря" in res2.text and "▶" in res2.text
    assert party_list("!персонаж", ctx) is None


def test_party_switch_and_persist():
    ctx = make_ctx()
    ctx.party = Party([{"name": "Аня"}, {"name": "Боря"}])
    ctx.party.switch("Боря")
    calls = []
    ctx.persist = lambda: calls.append(1)
    res = party_switch("!играть аня", ctx)
    assert ctx.party.active_name == "Аня" and calls == [1]
    assert "Аня" in res.text
    res2 = party_switch("!играть Зоя", ctx)
    assert "Боря" in res2.text  # подсказка со списком доступных
    assert party_switch("ерунда", ctx) is None


def test_party_new_adds_character():
    ctx = make_ctx()
    ctx.party = Party({})
    res = party_new("!новый Гриша, Воин, 12, 13", ctx)
    assert [c.name for c in ctx.party.chars] == ["Гриша"]
    assert ctx.party.active == 0
    assert "Гриша" in res.text
    assert party_new("ерунда", ctx) is None


def test_party_rename_active():
    ctx = make_ctx()
    ctx.party = Party([{"name": "Аня"}])
    calls = []
    ctx.persist = lambda: calls.append(1)
    res = party_rename("!переименовать Анюта", ctx)
    assert ctx.party.active_name == "Анюта" and calls == [1]
    assert "Анюта" in res.text


def test_party_remove_flow():
    ctx = make_ctx()
    ctx.party = Party([{"name": "Аня"}, {"name": "Боря"}])
    ctx.party.switch("Боря")
    res = party_remove("!партия удалить Боря", ctx)
    assert [c.name for c in ctx.party.chars] == ["Аня"]
    assert ctx.character is ctx.party.active_character
    assert "Аня" in res.text
    res2 = party_remove("!партия удалить Аня", ctx)  # последнего нельзя
    assert len(ctx.party.chars) == 1 and "Аня" in res2.text


# ── Мир и карта ──


def test_world_goto_advances_time_and_shows_exits():
    ctx = make_ctx()
    ctx.world.connect("Лагерь", "Пещера")
    res = world_command("!идти Лагерь", ctx)
    assert ctx.world.location == "Лагерь"
    assert ctx.timew.hour == 9
    assert "Пещера" in res.text


def test_world_fact_voice_and_connect():
    ctx = make_ctx()
    world_command("!факт Врата закрыты", ctx)
    assert ctx.world.facts == ["Врата закрыты"]
    res = world_command("!факт Врата закрыты", ctx)
    assert t("world.fact_exists") in res.text
    world_command("!голос {Иван} грубый", ctx)
    assert ctx.world.npc_voices == {"Иван": "грубый"}
    res3 = world_command("!голос {Иван} писклявый", ctx)
    assert "грубый" in res3.text  # список допустимых голосов
    world_command("связь А Б", ctx)
    assert ctx.world.neighbors("А") == ["Б"]
    assert world_command("ерунда", ctx) is None


def test_world_show_and_map_silent(capsys):
    ctx = make_ctx()
    ctx.world.set_location("Лагерь")
    res = world_command("!мир", ctx)
    assert res.text == ""
    assert "Лагерь" in capsys.readouterr().out
    res2 = map_show("!карта", ctx)
    assert res2.text == ""
    assert "Лагерь" in capsys.readouterr().out
    res3 = map_connect("!связь <<Лагерь>> <<Пещера>>", ctx)
    assert ctx.world.neighbors("Лагерь") == ["Пещера"]
    assert "Пещера" in res3.text
    assert map_show("не карта", ctx) is None
    assert map_connect("!связь А Б", ctx) is None  # map_connect ждёт <<...>>


def test_npc_add_show_remove_flow(capsys):
    ctx = make_ctx()
    res = npc_command("!npc Бармен | циничный | знает слухи", ctx)
    assert ctx.npcs.npcs["Бармен"]["voice"] == "циничный"
    assert "Бармен" in res.text
    res_show = npc_command("!npc", ctx)
    assert res_show.text == "" and "Бармен" in capsys.readouterr().out
    npc_command("!npc удалить Бармен", ctx)
    assert "Бармен" not in ctx.npcs.npcs
    assert "удалить" not in ctx.npcs.npcs  # регрессия: «удалить» не создаёт NPC
    res2 = npc_command("!npc удалить Бармен", ctx)
    assert t("world.npc_not_found") in res2.text
    assert npc_command("!npc удал Бармен", ctx) is not None  # тоже форма удаления


# ── Заклинания и статусы ──


def test_spell_add_show_remove_flow(capsys):
    ctx = make_ctx()
    res = spell_command("!заклинание Огонь: жгучий | урон 2d6 | СЛ 14", ctx)
    spell = ctx.spells.spells[0]
    assert spell["name"] == "Огонь" and spell["dmg"] == "2d6" and spell["save_dc"] == 14
    assert "Огонь" in res.text
    assert spell_command("!заклинания", ctx).text == ""
    assert "Огонь" in capsys.readouterr().out
    spell_command("!заклинание удалить Огонь", ctx)
    assert ctx.spells.spells == []  # регрессия: «удалить X» не добавляет «удалить X»
    res2 = spell_command("!заклинание удалить Огонь", ctx)
    assert t("rpg.spell_not_found") in res2.text


def test_status_add_remove_flow():
    ctx = make_ctx()
    res = status_command("!статус-эффект отравлен 2", ctx)
    assert ctx.status.effects[0] == {"name": "отравлен", "rounds": 2, "magnitude": 0}
    assert "отравлен" in res.text
    status_command("!статус-эффект удалить отравлен", ctx)
    assert ctx.status.effects == []
    res2 = status_command("!статус-эффект удалить отравлен", ctx)
    assert t("rpg.effect_not_found") in res2.text
    assert status_command("!эффекты", ctx).text == ""


# ── Уровни, квесты, время ──


def test_xp_command_levelup_and_statup():
    ctx = make_ctx()
    xp_command("!опыт 300", ctx)
    assert ctx.prog.level == 2 and ctx.prog.xp_bonus == 1
    xp_command("!улучшить STR 1", ctx)
    assert ctx.character.stats["STR"] == 15
    assert ctx.prog.xp_bonus == 0
    res = xp_command("!улучшить STR 5", ctx)
    assert ctx.character.stats["STR"] == 15  # очков не хватает
    assert "STR" in res.text


def test_quest_done_and_del_flow():
    ctx = make_ctx()
    quest_command("!квест Найти кота", ctx)
    quest_command("!квест готов Найти кота", ctx)
    assert ctx.quests.active == [] and len(ctx.quests.done) == 1
    assert ctx.prog.xp == 100
    quest_command("!квест Проводить караван", ctx)
    res = quest_command("!квест удалить Проводить караван", ctx)
    assert ctx.quests.active == []
    assert "Проводить караван" in res.text
    res2 = quest_command("!квест удалить Нет такого", ctx)
    assert t("rpg.quest_not_found") in res2.text
    assert quest_command("!квесты", ctx).text == ""


def test_time_and_weather_commands():
    ctx = make_ctx()
    res = time_command("!время +3", ctx)
    assert ctx.timew.hour == 11
    assert "11" in res.text
    res2 = time_command("!время", ctx)
    assert "11" in res2.text
    weather_command("!погода дождь", ctx)
    assert ctx.timew.weather == "дождь"
    res3 = weather_command("!погода град", ctx)
    assert "гроза" in res3.text  # список допустимой погоды
    assert weather_command("ерунда", ctx) is None


def test_journal_command():
    ctx = make_ctx()
    journal_command("!запись Начали поход", ctx)
    assert ctx.journal.entries[0]["text"] == "[Тест] Начали поход"
    assert ctx.journal.entries[0]["day"] == 1
    assert journal_command("!журнал", ctx).text == ""


def test_macro_command_flow():
    ctx = make_ctx()
    res = macro_command("!макрос бой = !атака Гоблин", ctx)
    assert ctx.macros.expand("бой") == "!атака Гоблин"
    assert "бой" in res.text
    res2 = macro_command("!макрос удалить бой", ctx)
    assert ctx.macros.macros == {}
    assert t("rpg.macro_removed") in res2.text


def test_style_command_flow():
    ctx = make_ctx()
    style_command("!тон мрачный", ctx)
    assert ctx.style.tone == "мрачный"
    res = style_command("!тон бред", ctx)
    assert "мрачный" in res.text  # список допустимых тонов
    style_command("!жанр киберпанк", ctx)
    assert ctx.style.genre == "киберпанк"
    res2 = style_command("!жанр мелодрама", ctx)
    assert "киберпанк" in res2.text
    assert style_command("ерунда", ctx) is None


def test_rest_command_restores_everything():
    ctx = make_ctx()
    ctx.character.hp = 3
    ctx.status.add("отравлен", 5)
    ctx.spells.set_slots(2, "маг")
    ctx.spells.use_slot()
    ctx.timew.hour = 20
    res = rest_command("!отдых", ctx)
    assert ctx.character.hp == ctx.character.max_hp == 20
    assert ctx.status.effects == []
    assert ctx.spells.slots_used == 0
    assert (ctx.timew.day, ctx.timew.hour) == (2, 4)
    assert res is not None


def test_enemy_add_command():
    ctx = make_ctx()
    enemy_add_command("!враг Гоблин 12 15", ctx)
    assert len(ctx.enemies) == 1
    assert ctx.enemies.enemies[0]["ac"] == 15
    res = enemy_add_command("!враг Гоблин 5", ctx)
    assert "Гоблин" in res.text  # уже существует


def test_check_command_conflict_and_ok():
    ctx = make_ctx()
    ctx.world.add_fact("Ворота заперты без ключа")
    res = check_command("!проверка Ворота не заперты без ключа", ctx)
    assert t("rpg.check_conflict") in res.text
    assert "Ворота заперты без ключа" in res.text
    res2 = check_command("!проверка Погода ясная", ctx)
    assert t("rpg.check_ok") in res2.text


def test_quiet_command():
    ctx = make_ctx()
    quiet_command("!тихо выкл", ctx)
    assert ctx.quiet_mode["on"] is False
    quiet_command("!тихо вкл", ctx)
    assert ctx.quiet_mode["on"] is True


def test_reputation_command_silent(capsys):
    ctx = make_ctx()
    ctx.reputation = None
    assert reputation_command("!репутация", ctx) is None
    ctx.reputation = Reputation({"Корпорация": -20})
    res = reputation_command("!репутация", ctx)
    assert res.text == ""
    assert "Корпорация" in capsys.readouterr().out


def test_stabilize_command_success_and_fail(monkeypatch):
    monkeypatch.setattr("dndai.commands.rpg_cmds.random.randint", lambda a, b: 15)
    ctx = make_ctx()
    assert stabilize_command("!стабилизироваться", ctx).text  # ещё не умирает
    ctx.character.hp = 0
    stabilize_command("!стабилизироваться", ctx)
    assert ctx.character.death_saves["stabilized"] is True

    monkeypatch.setattr("dndai.commands.rpg_cmds.random.randint", lambda a, b: 1)
    ctx2 = make_ctx()
    ctx2.character.hp = 0
    stabilize_command("!стабилизироваться", ctx2)
    assert ctx2.character.death_saves["failures"] == 1


# ── Мета ──


def test_dice_command():
    ctx = make_ctx()
    res = dice_command("!кости 2d6", ctx)
    assert res is not None and "2d6" in res.text
    assert dice_command("!кости абракадабра", ctx) is None


def test_rollback_command_flow():
    ctx = make_ctx()
    res = rollback_command("!откат", ctx)
    assert res is not None and res.text  # бэкапа нет
    ctx.rollback = lambda: True
    res2 = rollback_command("!откат", ctx)
    assert res2.exit_loop is True and res2.skip_persist is True
