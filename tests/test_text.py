#!/usr/bin/env python3
"""Тесты для core/text.py — highlight(), format_paragraphs()"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.core.text import highlight, format_paragraphs


def test_highlight_npc():
    result = highlight("{{Бармен}} кивает")
    assert "Бармен" in result


def test_highlight_location():
    result = highlight("<<Таверна>> тёмная")
    assert "Таверна" in result


def test_highlight_item():
    result = highlight("[[Меч]] острый")
    assert "Меч" in result


def test_highlight_event():
    result = highlight("__Бой__ начался")
    assert "Бой" in result


def test_highlight_emotion():
    result = highlight("!!Страх!! нарастает")
    assert "Страх" in result


def test_highlight_dialogue():
    result = highlight('"Привет!" — говорит он')
    assert "Привет!" in result


def test_highlight_none():
    assert highlight(None) == ""
    assert highlight("") == ""


def test_format_paragraphs_empty():
    assert format_paragraphs("") == ""
    assert format_paragraphs(None) == ""


def test_format_paragraphs_short():
    result = format_paragraphs("Один. Два. Три.")
    assert "Один" in result
    assert "Три" in result


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
