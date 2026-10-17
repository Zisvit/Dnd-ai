#!/usr/bin/env python3
"""Тесты экономики: профиль рынка, условия, маркеры [[ЦЕНА]]/[[ТОВАР]]."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dndai.commands import dispatch
from dndai.commands.character_cmds import shop_command
from dndai.commands.world_cmds import market_command
from dndai.core.i18n import t
from dndai.game import economy
from dndai.game.world import WorldState
from tests.test_dispatch import make_ctx

LEGACY_PRICES = {
    "зелье лечения": 25,
    "зелье": 25,
    "факел": 2,
    "верёвка": 5,
    "отмычки": 40,
    "стрелы": 10,
    "кинжал": 15,
    "меч": 50,
    "щит": 30,
    "лук": 60,
    "кольчуга": 100,
    "латы": 250,
    "посох": 20,
    "топор": 40,
}


def neutral_world(loc="Таверна", facts=None, markets=None, goods=None):
    """Мир с заданной локацией, фактами и записями (по умолчанию нейтраль)."""
    return WorldState(
        {
            "location": loc,
            "facts": facts or [],
            "markets": markets or {},
            "trade_goods": goods or {},
        }
    )


# ── Нейтраль и арифметика ────────────────────────────────────────────────
def test_neutral_market_reproduces_legacy_prices():
    w = neutral_world()
    for name, old_price in LEGACY_PRICES.items():
        assert economy.buy_price(w, name) == old_price, name
    assert economy.SHOP_PRICES == LEGACY_PRICES
    assert economy.sell_price(w, "зелье") == 12  # 25 // 2
    assert economy.sell_price(w, "факел") == 1  # 2 // 2
    # неизвестный товар: покупка 30, скупка 10 — как раньше
    assert economy.buy_price(w, "амулет") == 30
    assert economy.sell_price(w, "амулет") == 10


def test_half_up_single_rounding():
    w = neutral_world(loc="Глухая деревня")
    assert economy.buy_price(w, "меч") == 55  # 50 × 1.10
    w = neutral_world(
        loc="Глухая деревня",
        markets={"глухая деревня": {"wealth": "rich", "src": {"wealth": "dm"}}},
    )
    # 50 × 1.10 × 1.10 = 60.5 → 61: одно half-up округление в конце
    assert economy.buy_price(w, "меч") == 61


# ── Профиль и условия ────────────────────────────────────────────────────
def test_heuristic_profiles():
    assert economy.infer_profile("Глухая Деревня").get("size") == "village"
    assert economy.infer_profile("Столица Империи").get("size") == "capital"
    assert economy.infer_profile("Соль-Городок").get("size") == "town"
    assert economy.infer_profile("Город Мрака").get("size") == "city"
    assert economy.infer_profile("Посёлок у реки").get("size") == "settlement"
    assert economy.infer_profile("Хутор Ветров").get("size") == "hamlet"
    assert economy.infer_profile("Порт Синих Скал").get("tags") == ["port"]
    assert economy.infer_profile("Богатый квартал").get("wealth") == "rich"
    # «Торговая Роща» и «Таверна» — нейтральны (лечатся !рынок тип)
    assert economy.infer_profile("Торговая Роща") == {}
    assert economy.infer_profile("Таверна") == {}


def test_heuristic_order_specific_before_general():
    assert economy.infer_profile("Посёлок")["size"] == "settlement"
    assert economy.infer_profile("Городок")["size"] == "town"
    assert economy.infer_profile("Город")["size"] == "city"


def test_tag_and_wealth_factors():
    w = neutral_world(markets={"таверна": {"tags": ["port"]}})
    assert economy.buy_price(w, "зелье") == 23  # 25 × 0.9 = 22.5 → 23
    assert economy.buy_price(w, "меч") == 50
    w = neutral_world(markets={"таверна": {"tags": ["smith"]}})
    assert economy.buy_price(w, "меч") == 43  # 50 × 0.85 = 42.5 → 43
    assert economy.buy_price(w, "кольчуга") == 90  # 100 × 0.9
    assert economy.buy_price(w, "зелье") == 25


def test_conditions_from_facts():
    assert economy.conditions_factor(neutral_world(facts=["В городе голод"]))[0] == 1400
    assert economy.conditions_factor(neutral_world(facts=["неурожай"]))[0] == 1400
    # на один факт — только первое совпадение
    assert economy.conditions_factor(neutral_world(facts=["осада и голод"]))[0] == 1250
    assert economy.conditions_factor(neutral_world(facts=["осада", "голод"]))[0] == 1750
    # произведение клампится сверху
    w = neutral_world(facts=["осада", "голод", "дефицит", "блокада"])
    assert economy.conditions_factor(w)[0] == 2000
    assert economy.conditions_factor(neutral_world(facts=["Осенняя ярмарка"]))[0] == 900


def test_conditions_affect_price():
    w = neutral_world(loc="Глухая деревня", facts=["голод"])
    assert economy.buy_price(w, "меч") == 77  # 50 × 1.10 × 1.40


def test_market_prices_change_after_goto():
    w = neutral_world(loc="Глухая деревня")
    assert economy.buy_price(w, "меч") == 55
    w.set_location("Столица Империи")
    assert economy.buy_price(w, "меч") == 43  # 50 × 0.85


# ── Блок [РЫНОК] ─────────────────────────────────────────────────────────
def test_market_block_fits_limit_and_updates():
    w = neutral_world()
    block = economy.market_block(w)
    assert block.startswith("[РЫНОК]")
    assert "Таверна" in block
    assert "меч 50" in block
    assert "зелье лечения 25" in block
    assert "зелье 25" not in block  # алиас не дублируется
    assert len(block) <= economy.MARKET_BLOCK_LIMIT

    w2 = neutral_world(loc="Глухая деревня")
    block2 = economy.market_block(w2)
    assert block2 != block
    assert "деревня" in block2 and "меч 55" in block2

    # экстремальный случай: длинная локация, условия и переполненный каталог
    w3 = neutral_world(loc="Очень длинное название " * 5, facts=["осада", "голод"])
    for i in range(60):
        w3.trade_goods[f"товар-{i}"] = {"name": f"Товар-{i}", "base": 10, "cat": "misc"}
    assert len(economy.market_block(w3)) <= economy.MARKET_BLOCK_LIMIT


def test_market_block_empty_without_location():
    assert economy.market_block(neutral_world(loc="")) == ""


# ── Маркеры [[ЦЕНА]] / [[ТОВАР]] / [[РЫНОК]] ─────────────────────────────
def test_price_marker_sets_override_and_clamps():
    w = neutral_world()
    economy.apply_trade_markers("[[ЦЕНА: меч|100]]", w)
    assert economy.buy_price(w, "меч") == 100
    assert economy.sell_price(w, "меч") == 50
    # выход за коридор ×2 — кламп с нотой
    notes = economy.apply_trade_markers("[[ЦЕНА: меч|300]]", w)
    assert economy.buy_price(w, "меч") == 100
    assert notes == [t("market.note_clamped", item="меч", price=100)]
    # выход за коридор ×0.5 — кламп снизу
    notes = economy.apply_trade_markers("[[ЦЕНА: меч|10]]", w)
    assert economy.buy_price(w, "меч") == 25
    assert notes == [t("market.note_clamped", item="меч", price=25)]


def test_price_marker_unknown_and_cap():
    w = neutral_world()
    notes = economy.apply_trade_markers("[[ЦЕНА: амулет|500]]", w)
    assert notes == [t("market.note_unknown", item="амулет")]
    assert economy.buy_price(w, "амулет") == 30  # не зарегистрировано
    assert "overrides" not in w.markets.get("таверна", {})
    # не больше 5 срабатываний за ход
    text = " ".join(f"[[ЦЕНА: меч|{50 + i}]]" for i in range(7))
    notes = economy.apply_trade_markers(text, w)
    assert t("market.note_cap_price") in notes
    assert sum(1 for n in notes if "меч" in n) == 5


def test_goods_marker_register_overwrite_protect():
    w = neutral_world()
    notes = economy.apply_trade_markers("[[ТОВАР: Лунный амулет|150|зелье]]", w)
    assert notes == [t("market.note_good", name="Лунный амулет", base=150)]
    assert w.trade_goods["лунный амулет"] == {
        "name": "Лунный амулет",
        "base": 150,
        "cat": "potion",
    }
    assert economy.buy_price(w, "лунный амулет") == 150
    assert economy.sell_price(w, "лунный амулет") == 75
    # overwrite
    notes = economy.apply_trade_markers("[[ТОВАР: Лунный амулет|200|зелье]]", w)
    assert t("market.note_good", name="Лунный амулет", base=200) in notes
    assert economy.buy_price(w, "лунный амулет") == 200
    # идентичный payload — тихий no-op
    assert economy.apply_trade_markers("[[ТОВАР: Лунный амулет|200|зелье]]", w) == []
    # статический каталог защищён
    notes = economy.apply_trade_markers("[[ТОВАР: меч|999]]", w)
    assert t("market.note_known", name="меч") in notes
    assert w.trade_goods.get("меч") is None
    assert economy.buy_price(w, "меч") == 50


def test_registry_cap_blocks_51st_good():
    w = neutral_world()
    for i in range(economy.REGISTRY_CAP):
        w.trade_goods[f"товар-{i}"] = {"name": f"Товар-{i}", "base": 10, "cat": "misc"}
    notes = economy.apply_trade_markers("[[ТОВАР: Сверхновый|10|misc]]", w)
    assert "сверхновый" not in w.trade_goods
    assert notes == [t("market.note_registry_full")]


def test_market_marker_applies_and_respects_manual():
    w = neutral_world(loc="Глухая деревня")
    notes = economy.apply_trade_markers("[[РЫНОК: <<Глухая деревня>>|город богатый портовый]]", w)
    expected_parts = ", ".join(
        [t("market.size_city"), t("market.wealth_rich"), t("market.tag_port")]
    )
    assert notes == [t("market.note_profile", loc="Глухая деревня", parts=expected_parts)]
    record = w.markets["глухая деревня"]
    assert record["size"] == "city"
    assert record["wealth"] == "rich"
    assert record["tags"] == ["port"]

    ctx = make_ctx()
    ctx.world = w
    market_command("!рынок тип деревня", ctx)
    assert w.markets["глухая деревня"]["size"] == "village"
    assert w.markets["глухая деревня"]["src"]["size"] == "manual"
    # закреплённый тип маркер не перебивает, остальные поля — обновляет
    economy.apply_trade_markers("[[РЫНОК: <<Глухая деревня>>|столица бедный]]", w)
    assert w.markets["глухая деревня"]["size"] == "village"
    assert w.markets["глухая деревня"]["wealth"] == "poor"


def test_reset_market_clears_manual_and_overrides():
    ctx = make_ctx()
    ctx.world = neutral_world(loc="Глухая деревня")
    w = ctx.world
    market_command("!рынок тип город", ctx)
    market_command("!рынок достаток богатый", ctx)
    economy.apply_trade_markers("[[ЦЕНА: меч|100]]", w)
    assert w.markets["глухая деревня"]["src"]["size"] == "manual"
    assert w.markets["глухая деревня"]["overrides"]

    res = market_command("!рынок сброс", ctx)
    assert t("market.reset_done", loc="Глухая деревня") in res.text
    # ручные поля и наценки сняты; пустая запись удалена → эвристика снова работает
    assert "глухая деревня" not in w.markets
    assert economy.buy_price(w, "меч") == 55
    # после сброса маркер снова задаёт тип
    economy.apply_trade_markers("[[РЫНОК: <<Глухая деревня>>|столица]]", w)
    assert w.markets["глухая деревня"]["size"] == "capital"
    # повторный сброс без ручных настроек
    res = market_command("!рынок сброс", ctx)
    assert t("market.reset_none", loc="Глухая деревня") in res.text


# ── Команда !рынок ───────────────────────────────────────────────────────
def test_market_view_shows_profile_and_manual_mark(capsys):
    ctx = make_ctx()
    ctx.world = neutral_world(loc="Глухая деревня")
    market_command("!рынок тип городок", ctx)
    market_command("!рынок", ctx)
    out = capsys.readouterr().out
    assert t("market.title", loc="Глухая деревня") in out
    assert t("market.size_town") in out
    assert t("market.src_manual") in out
    assert "меч" in out
    assert t("market.hint") in out


def test_market_command_safety():
    ctx = make_ctx()
    ctx.world = neutral_world()
    assert market_command("идём на рынок за хлебом", ctx) is None
    assert market_command("рынок в городе закрыт", ctx) is None
    res = market_command("!рынок мегаполис", ctx)
    assert t("market.hint") in res.text


def test_market_type_unknown_value():
    ctx = make_ctx()
    ctx.world = neutral_world(loc="Лагерь")
    res = market_command("!рынок тип мегаполис", ctx)
    assert "мегаполис" in res.text
    res = market_command("!рынок достаток несметный", ctx)
    assert "несметный" in res.text


def test_market_command_registered_in_dispatch(capsys):
    ctx = make_ctx()
    ctx.world = neutral_world(loc="Глухая деревня")
    dispatch("!рынок", ctx)
    assert t("market.title", loc="Глухая деревня") in capsys.readouterr().out
    res = dispatch("!рынок тип город", ctx)
    assert ctx.world.markets["глухая деревня"]["size"] == "city"
    assert t("market.type_set", loc="Глухая деревня", size=t("market.size_city")) in res.text


# ── Магазин (!купить/!продать) ───────────────────────────────────────────
def test_shop_uses_local_prices_and_ignores_offer():
    ctx = make_ctx()
    ctx.world = neutral_world(loc="Глухая деревня")
    ctx.character.gold = 200
    res = shop_command("!купить меч", ctx)
    assert ctx.character.gold == 145  # 200 − 55
    assert t("shop.bought", item="меч", price=55, gold=145) in res.text
    # своя цена — только подсказка: платим местную, в ответе нота
    res = shop_command("!купить меч 40", ctx)
    assert ctx.character.gold == 90
    assert t("shop.offer_ignored", offer=40, price=55) in res.text
    # продажа по местной цене: 55 // 2 = 27
    res = shop_command("!продать меч", ctx)
    assert ctx.character.gold == 117
    assert t("shop.sold", item="Меч", price=27, gold=117) in res.text
    res = shop_command("!продать меч 100", ctx)
    assert ctx.character.gold == 144
    assert t("shop.offer_ignored", offer=100, price=27) in res.text


def test_shop_unknown_item_fallback_price():
    ctx = make_ctx()
    ctx.world = neutral_world()
    ctx.character.gold = 100
    shop_command("!купить амулет", ctx)
    assert ctx.character.gold == 70  # фолбэк 30


# ── Сессии ───────────────────────────────────────────────────────────────
def test_world_roundtrip_supports_markets_and_legacy():
    data = {
        "location": "Лагерь",
        "markets": {"лагерь": {"tags": ["smith"], "overrides": {"меч": 1200}}},
        "trade_goods": {"амулет": {"name": "Амулет", "base": 99, "cat": "misc"}},
    }
    w = WorldState(data)
    dumped = w.to_dict()
    assert dumped["markets"] == data["markets"]
    assert dumped["trade_goods"] == data["trade_goods"]
    # старая сессия без новых полей читается и даёт нейтральные цены
    old = WorldState({"location": "Лагерь", "visited": ["Лагерь"]})
    assert old.markets == {} and old.trade_goods == {}
    assert economy.buy_price(old, "меч") == 50
