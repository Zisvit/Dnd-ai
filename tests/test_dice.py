#!/usr/bin/env python3
"""Тесты dndai/core/dice.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.core.dice import roll_dice


def test_simple_d20():
    total, rolls = roll_dice("d20")
    assert total is not None
    assert len(rolls) == 1
    assert 1 <= rolls[0] <= 20


def test_2d6():
    total, rolls = roll_dice("2d6")
    assert len(rolls) == 2
    assert all(1 <= r <= 6 for r in rolls)
    assert total == sum(rolls)


def test_with_modifier():
    total, rolls = roll_dice("1d20+5")
    assert len(rolls) == 1
    assert total == rolls[0] + 5


def test_negative_modifier():
    total, rolls = roll_dice("3d8-2")
    assert len(rolls) == 3
    assert all(1 <= r <= 8 for r in rolls)
    assert total == sum(rolls) - 2


def test_spaces_tolerated():
    total, _ = roll_dice(" 2d6 + 3 ")
    assert total is not None


def test_case_insensitive():
    total, rolls = roll_dice("D6")
    assert len(rolls) == 1


def test_embedded_text_rejected():
    """Строка с лишним текстом — НЕ dice-выражение."""
    assert roll_dice("2d6 бросаю кубик") == (None, None)
    assert roll_dice("брошу d20") == (None, None)
    assert roll_dice("у меня 2d6") == (None, None)


def test_zero_dice_rejected():
    assert roll_dice("0d6") == (None, None)


def test_one_sided_die_rejected():
    assert roll_dice("2d1") == (None, None)


def test_garbage_rejected():
    assert roll_dice("abc") == (None, None)
    assert roll_dice("") == (None, None)
    assert roll_dice(None) == (None, None)


def test_count_capped():
    total, rolls = roll_dice("1000d6")
    # ограничение защиты от абузa: максимум MAX_DICE_COUNT кубиков
    from dndai.core.dice import MAX_DICE_COUNT
    assert len(rolls) == MAX_DICE_COUNT


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
