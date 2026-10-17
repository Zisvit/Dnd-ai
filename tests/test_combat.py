#!/usr/bin/env python3
"""Тесты боевой системы: раунд боя, крит, урон по лежащему,
морale, лечение заклинанием, стабилизация."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.commands.combat_cmds import (fight_command, save_command,
                                      _attack_round)
from tests.test_dispatch import make_ctx


class FakeRandom:
    """Подменяет random.randint очередью значений (детерминизм)."""

    def __init__(self, queue):
        self.queue = list(queue)
        self.default = 3

    def randint(self, a, b):
        if self.queue:
            return self.queue.pop(0)
        return min(b, max(a, self.default))

    def __call__(self):
        return self


def test_fight_introduces_enemy_and_returns_rewrite():
    ctx = make_ctx()
    result = fight_command("!бой Гоблин 12 15", ctx)
    assert result is not None
    assert len(ctx.enemies) == 1
    assert ctx.enemies.enemies[0]["name"] == "Гоблин"
    assert ctx.enemies.enemies[0]["max_hp"] == 15
    assert result.rewrite_act and "МЕХАНИКА БОЯ" in result.rewrite_act
    assert not result.stop  # ход уходит мастеру


def test_attack_unknown_enemy():
    ctx = make_ctx()
    result = fight_command("!атака Никого", ctx)
    assert result is not None
    assert result.stop  # стоп: врага нет, мастеру ничего не уходит


def test_kill_grants_xp_and_clears_battle():
    import random
    ctx = make_ctx()
    ctx.enemies.add("Слизень", hp=5, ac=5)
    # игрок: d20=20 (крит); врагов больше нет → контратак нет
    fake = FakeRandom([20])
    orig_randint = random.randint
    random.randint = fake.randint
    try:
        xp_before = ctx.prog.xp
        result = _attack_round("Слизень", ctx, act="!атака Слизень")
        assert ctx.prog.xp > xp_before
        assert len(ctx.enemies) == 0
        assert "ВРАГ ПОВЕРЖЕН" in result.rewrite_act
    finally:
        random.randint = orig_randint


def test_hit_while_down_adds_death_failure():
    import random
    ctx = make_ctx()
    c = ctx.character
    c.hp = 1
    c.ac = 0            # гарантированно низкая КД
    ctx.enemies.add("Тролль", hp=200, ac=5)   # сильный враг (бонус атаки высок)
    eff_ac = c.ac + c.equip_ac_bonus() + ctx.status.ac_bonus()
    # очередь: игрок промахивается (d20=1), тролль бьёт некритом (d20=5),
    # дальше — кости урона (default занижен к 3)
    fake = FakeRandom([1, 5])
    fake.default = 3
    orig_randint = random.randint
    random.randint = fake.randint
    try:
        _attack_round("Тролль", ctx, act="!атака Тролль")
        assert c.hp == 0
        assert c.death_saves["failures"] == 1  # урон по лежащему = провал
    finally:
        random.randint = orig_randint
    assert eff_ac >= 0  # sanity


def test_crit_doubles_dice_not_modifier():
    import random
    ctx = make_ctx()
    char = ctx.character
    char.equipped["weapon"] = "Меч"      # 1d8
    char.stats["STR"] = 20               # модификатор +5
    ctx.enemies.add("Манекен", hp=1000, ac=10)  # не умрёт с одного удара
    fake = FakeRandom([20])              # крит игрока
    fake.default = 4                     # кость урона = 4
    orig_randint = random.randint
    random.randint = fake.randint
    try:
        dmg_before_hp = ctx.enemies.find("Манекен")["hp"]
        _attack_round("Манекен", ctx, act="!атака Манекен")
        dealt = dmg_before_hp - ctx.enemies.find("Манекен")["hp"]
        # По RAW 5e: удвоенная порция КОСТЕЙ, модификатор один раз:
        # 2*4 + 5 = 13 (а не 2*(4+5)=18 и не 4+5=9)
        assert dealt == 13
    finally:
        random.randint = orig_randint


def test_morale_xp_is_half_of_kill():
    import random
    ctx = make_ctx()
    foe = ctx.enemies.add("Трус", hp=20, ac=5)
    foe["hp"] = 2  # 10% HP → проверка морали возможна
    kill_xp = max(25, 5 * foe["max_hp"])
    # форсируем успех морали: любой бросок < 12 держится, >=12 бежит
    orig = random.randint
    random.randint = lambda a, b: 12
    try:
        from dndai.commands.combat_cmds import _morale_check
        msg = _morale_check(ctx, foe)
        assert msg is not None
        expected = max(10, kill_xp // 2)
        assert f"{expected}" in msg or str(expected) in msg
        assert len(ctx.enemies) == 0
    finally:
        random.randint = orig


def test_mob_stats_scale_with_hp():
    from dndai.game.rpg import mob_attack_stats
    weak = {"name": "Крыса", "hp": 5, "max_hp": 5}
    strong = {"name": "Дракон", "hp": 120, "max_hp": 120}
    wb, wd = mob_attack_stats(weak)
    sb, sd = mob_attack_stats(strong)
    assert sb > wb          # сильный бьёт точнее
    assert sd != wd         # и больнее


def test_save_command_rewrites_act():
    ctx = make_ctx()
    result = save_command("!спас DEX 12", ctx)
    assert result is not None
    assert result.rewrite_act and "спасбросок" in result.rewrite_act.lower()


def test_stabilize_keeps_flag():
    from dndai.commands.rpg_cmds import stabilize_command
    ctx = make_ctx()
    c = ctx.character
    c.hp = 0
    c.death_saves["successes"] = 3   # уже 3 успеха → стабилизация
    result = stabilize_command("!стабилизироваться", ctx)
    assert result is not None
    assert c.death_saves["stabilized"] is True


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
