#!/usr/bin/env python3
"""Целостность локализации: паритет ru/en по ключам и плейсхолдерам.

Один агрегатный тест вместо поштучных (решение совета): ловит дрейф
при добавлении строк и не раздувает дифф при новых ключах.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from string import Formatter

from dndai.core import i18n


def _placeholders(template):
    return {
        name
        for _literal, name, _spec, _conv in Formatter().parse(template)
        if name is not None
    }


def test_all_keys_have_ru_and_en():
    missing = [
        key
        for key, entry in i18n._T.items()
        if not isinstance(entry.get("ru"), str) or not isinstance(entry.get("en"), str)
    ]
    assert missing == []


def test_placeholders_parity_between_languages():
    bad = []
    for key, entry in i18n._T.items():
        try:
            ru = _placeholders(entry["ru"])
            en = _placeholders(entry["en"])
        except ValueError as exc:
            bad.append((key, str(exc)))
            continue
        if ru != en:
            bad.append((key, sorted(ru), sorted(en)))
    assert bad == []


def test_t_fallback_and_placeholder_substitution():
    assert i18n.t("definitely.missing.key") == "definitely.missing.key"
    assert "503" in i18n.t("api.error_server", status=503)


def test_variants_cover_both_languages():
    values = i18n.variants("main.first_prompt_tavern")
    assert len(values) == 2
    assert all(isinstance(v, str) and v for v in values)
