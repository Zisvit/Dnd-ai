#!/usr/bin/env python3
"""Тесты для core/output.py — clean()"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.core.output import clean


def test_empty():
    assert clean("") == ""
    assert clean(None) == ""
    assert clean("   ") == ""


def test_normal_text():
    text = "Ты входишь в <<Таверну>>. {{Бармен}} кивает."
    assert clean(text) == text


def test_closed_think():
    text = "<think>thinking...</think>Real response"
    result = clean(text)
    assert "<think>" not in result
    assert "</tool_call>" not in result
    assert "Real response" in result


def test_unclosed_think_with_newlines():
    text = "<think>thinking...\n\nReal response here"
    result = clean(text)
    assert "<think>" not in result
    assert "Real response" in result


def test_unclosed_think_without_newlines():
    text = "<think>thinking...\nReal response"
    result = clean(text)
    assert "<think>" not in result


def test_closed_think_multiline():
    text = "<think>line1\nline2\nline3\n</think>Actual response"
    result = clean(text)
    assert "line1" not in result
    assert "line2" not in result
    assert "line3" not in result
    assert "Actual response" in result


def test_unicode_think():
    text = "<𝑎𝑛𝑡𝑚𝑙:thinking>thinking...<𝑎𝑛𝑡𝑚𝑙:thinking>Response"
    result = clean(text)
    assert "thinking" not in result
    assert "Response" in result


def test_unicode_think_unclosed():
    text = "<𝑎𝑛𝑡𝑚𝑙:thinking>thinking...\n\nResponse here"
    result = clean(text)
    assert "thinking" not in result
    assert "Response here" in result


def test_ascii_think():
    text = "<thinking>thinking...</thinking>Response"
    result = clean(text)
    assert "thinking" not in result
    assert "Response" in result


def test_ascii_think_unclosed():
    text = "<thinking>thinking...\n\nResponse here"
    result = clean(text)
    assert "thinking" not in result
    assert "Response here" in result


def test_reasoning_tag():
    text = "<reasoning>analysis...</reasoning>Response"
    result = clean(text)
    assert "analysis" not in result
    assert "Response" in result


def test_junk_bold_headers():
    text = "1. **Analyze User Input:**\n2. **Final Polish:**\nReal response"
    result = clean(text)
    assert "Analyze User Input" not in result
    assert "Final Polish" not in result
    assert "Real response" in result


def test_junk_bullet_bold():
    text = "- **Role/Context:** value\n- **Task:** do something\nReal response"
    result = clean(text)
    assert "Role/Context" not in result
    assert "Real response" in result


def test_junk_proceeds():
    text = "Proceeds.\nReady.\nReal response"
    result = clean(text)
    assert "Proceeds." not in result
    assert "Ready." not in result
    assert "Real response" in result


def test_junk_done_checkmark():
    text = "✅\n[Done]\nReal response"
    result = clean(text)
    assert "✅" not in result
    assert "[Done]" not in result
    assert "Real response" in result


def test_junk_output_matches():
    text = "Output matches response.\nSelf-Correction applied.\nReal response"
    result = clean(text)
    assert "Output matches" not in result
    assert "Self-Correction" not in result
    assert "Real response" in result


def test_preserves_dnd_content():
    text = 'Ты видишь **гоблина**. {{Гоблин}} рычит. __Бой!__ [Меч]'
    result = clean(text)
    assert result == text


def test_preserves_dialogues():
    text = '— Привет! — говорит {{Бармен}}. "Садись", — добавляет он.'
    result = clean(text)
    assert result == text


def test_mixed_think_and_junk():
    text = ("<think>thinking...\n"
            "Here's a thinking process:\n"
            "1. **Analyze User Input:**\n"
            "   - Something\n"
            "2. **Final Polish:**\n"
            "   Ready.\n"
            "   ✅\n"
            "   [Done]\n"
            "\n"
            "---\n"
            "\n"
            "Ты в <<Таверне>>. {{Бармен}} ждёт.")
    result = clean(text)
    # Жёсткие ассерты: ни мышления, ни служебного мусора не остаётся
    assert "<think>" not in result
    assert "Analyze" not in result
    assert "[Done]" not in result
    assert result.strip().endswith("{{Бармен}} ждёт.")


def test_multiple_think_blocks():
    text = "<think>first</think><think>second</think>Real response"
    result = clean(text)
    assert "<think>" not in result
    assert "Real response" in result


def test_newlines_collapsed():
    text = "Response\n\n\n\n\n\nMore"
    result = clean(text)
    assert "\n\n\n" not in result


def test_highlight_strips_service_markers():
    """Служебные маркеры [[ФАКТ:/[[ЗОЛОТО: и т.п. не видны игроку."""
    from dndai.core.text import highlight
    text = ("Ты нашёл [[Меч]].\n[[ФАКТ: Магия запрещена]] "
            "[[ЗОЛОТО: +25]] [[РЕПУТАЦИЯ: Гильдия +10]]")
    result = highlight(text)
    assert "ФАКТ" not in result
    assert "ЗОЛОТО" not in result
    assert "РЕПУТАЦИЯ" not in result
    # обычная предметная разметка сохраняется
    assert "Меч" in result


def test_highlight_keeps_item_markup():
    from dndai.core.text import highlight
    text = "На прилавке лежит [[Аптечка]]"
    result = highlight(text)
    assert "[[" not in result  # разметка заменена подсветкой
    assert "Аптечка" in result


def _make_printer(monkeypatch):
    import importlib

    output_mod = importlib.import_module("dndai.core.output")
    printed = []
    monkeypatch.setattr(output_mod, "_write", printed.append)
    return output_mod.StreamingPrinter(), printed


def test_streaming_printer_keeps_single_lt(monkeypatch):
    """Регресс №2: одиночный '<' терялся и следующий токен печатался как текст."""
    printer, printed = _make_printer(monkeypatch)
    printer.on_token("Абв<")
    printer.on_token("think>тайна</think> дальше")
    printer.finish()
    out = "".join(printed)
    assert "Абв" in out
    assert "дальше" in out
    assert "тайна" not in out


def test_streaming_printer_hides_tag_split_across_tokens(monkeypatch):
    printer, printed = _make_printer(monkeypatch)
    for chunk in ["<thi", "nk>секрет", " ответа</thi", "nk> Видимый текст"]:
        printer.on_token(chunk)
    printer.finish()
    out = "".join(printed)
    assert "секрет" not in out
    assert "ответа" not in out
    assert "Видимый текст" in out


def test_streaming_printer_finish_flushes_pending_lt(monkeypatch):
    printer, printed = _make_printer(monkeypatch)
    printer.on_token("Текст<")
    printer.finish()
    assert "".join(printed).startswith("Текст<")


def test_streaming_printer_keeps_legit_lt_in_text(monkeypatch):
    printer, printed = _make_printer(monkeypatch)
    printer.on_token("урон 2 <")
    printer.on_token(" 3")
    printer.finish()
    assert "2 < 3" in "".join(printed)


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
