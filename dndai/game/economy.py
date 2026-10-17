#!/usr/bin/env python3
"""Экономика мира: цены зависят от места и условий.

Профиль локации и условия выводятся на чтении из уже хранимых данных:

- ``world["markets"]`` — только явные записи (маркер ``[[РЫНОК]]`` или
  команды ``!рынок``); недостающие поля добирает эвристика по имени локации;
- ``world["trade_goods"]`` — динамические товары (``[[ТОВАР: имя|база|категория]]``);
- условия — из ``world.facts`` (осада, голод, ярмарка...), произведение множителей.

Формула целочисленная, одно half-up округление в конце::

    price = max(1, (base * f1 * f2 * ... + D // 2) // D),  D = 1000 ** k

Нейтральный рынок воспроизводит прежний прайс-лист торговца один в один
(неизвестный товар: покупка 30, скупка 10).
"""

import re

from dndai.core.i18n import t

# ── Константы ─────────────────────────────────────────────────────────────
PERMILLE = 1000
UNKNOWN_BUY_BASE = 30  # неизвестный товар: база покупки
UNKNOWN_SELL_BASE = 20  # неизвестный товар: база скупки (нейтрально — 10)
MARKER_CAP_PER_TURN = 5  # максимум [[ЦЕНА]] и столько же [[ТОВАР]] за ход
REGISTRY_CAP = 50  # потолок динамического каталога товаров
PRICE_CORRIDOR_MIN = 500  # коридор [[ЦЕНА]]: ×0.5 … ×2.0
PRICE_CORRIDOR_MAX = 2000
CONDITION_MIN = 500  # кламп произведения условий
CONDITION_MAX = 2000
MARKET_BLOCK_LIMIT = 450  # размер блока [РЫНОК] в памяти мастера

# ── Каталог товаров: имя → (база, категория) ──────────────────────────────
GOODS = {
    "зелье лечения": (25, "potion"),
    "зелье": (25, "potion"),
    "факел": (2, "gear"),
    "верёвка": (5, "gear"),
    "отмычки": (40, "gear"),
    "стрелы": (10, "gear"),
    "кинжал": (15, "weapon"),
    "меч": (50, "weapon"),
    "щит": (30, "armor"),
    "лук": (60, "weapon"),
    "кольчуга": (100, "armor"),
    "латы": (250, "armor"),
    "посох": (20, "weapon"),
    "топор": (40, "weapon"),
}

# Нейтральный прайс торговца (обратная совместимость со старым SHOP_PRICES)
SHOP_PRICES = {name: base for name, (base, _cat) in GOODS.items()}

SIZE_PERMILLE = {
    "hamlet": 1150,
    "village": 1100,
    "settlement": 1000,
    "town": 950,
    "city": 900,
    "capital": 850,
}
WEALTH_PERMILLE = {"poor": 900, "normal": 1000, "rich": 1100}

# Теги рынка → скидки категорий (‰): кузница дешевит оружие/броню, порт — снаряжение/зелья
TAG_FACTORS = {
    "smith": {"weapon": 850, "armor": 900},
    "port": {"gear": 900, "potion": 900},
}

SIZE_LABELS = {
    "hamlet": "хутор",
    "village": "деревня",
    "settlement": "посёлок",
    "town": "городок",
    "city": "город",
    "capital": "столица",
}
WEALTH_LABELS = {"poor": "бедный", "normal": "обычный", "rich": "богатый"}
TAG_LABELS = {"smith": "кузнечный", "port": "портовый"}

# Словари маркеров и команд (!рынок тип/достаток)
SIZE_WORDS = {
    "хутор": "hamlet",
    "деревня": "village",
    "деревенька": "village",
    "село": "village",
    "сельцо": "village",
    "посёлок": "settlement",
    "поселок": "settlement",
    "городок": "town",
    "город": "city",
    "столица": "capital",
    "hamlet": "hamlet",
    "village": "village",
    "settlement": "settlement",
    "town": "town",
    "city": "city",
    "capital": "capital",
}
WEALTH_WORDS = {
    "бедный": "poor",
    "бедная": "poor",
    "бедное": "poor",
    "нищий": "poor",
    "обычный": "normal",
    "обычная": "normal",
    "средний": "normal",
    "богатый": "rich",
    "богатая": "rich",
    "богатое": "rich",
    "зажиточный": "rich",
    "poor": "poor",
    "normal": "normal",
    "rich": "rich",
}
TAG_WORDS = {
    "кузнечный": "smith",
    "кузница": "smith",
    "кузнец": "smith",
    "smith": "smith",
    "forge": "smith",
    "портовый": "port",
    "порт": "port",
    "гавань": "port",
    "port": "port",
    "harbor": "port",
    "harbour": "port",
}
CATEGORY_WORDS = {
    "оружие": "weapon",
    "weapon": "weapon",
    "броня": "armor",
    "armor": "armor",
    "снаряжение": "gear",
    "gear": "gear",
    "зелье": "potion",
    "зелья": "potion",
    "potion": "potion",
    "прочее": "misc",
    "misc": "misc",
}

# Условия мира: (подстрока факта, ярлык, множитель ‰); на факт — первое совпадение
CONDITION_WORDS = (
    ("осад", "осада", 1250),
    ("блокад", "блокада", 1250),
    ("голод", "голод", 1400),
    ("неурожай", "неурожай", 1400),
    ("дефицит", "дефицит", 1300),
    ("чума", "чума", 1250),
    ("эпидеми", "эпидемия", 1250),
    ("ярмарк", "ярмарка", 900),
    ("изобили", "изобилие", 850),
    ("урожай", "урожай", 850),
)

# Эвристика имени локации: частное раньше общего («городок» до «город»)
_NAME_HINTS = (
    ("столица", "size", "capital"),
    ("capital", "size", "capital"),
    ("городок", "size", "town"),
    ("посёлок", "size", "settlement"),
    ("поселок", "size", "settlement"),
    ("settlement", "size", "settlement"),
    ("деревня", "size", "village"),
    ("деревенька", "size", "village"),
    ("сельцо", "size", "village"),
    ("село", "size", "village"),
    ("хутор", "size", "hamlet"),
    ("village", "size", "village"),
    ("hamlet", "size", "hamlet"),
    ("город", "size", "city"),
    ("city", "size", "city"),
    ("town", "size", "town"),
    ("порт", "tag", "port"),
    ("гавань", "tag", "port"),
    ("пристан", "tag", "port"),
    ("harbor", "tag", "port"),
    ("harbour", "tag", "port"),
    ("port", "tag", "port"),
    ("кузн", "tag", "smith"),
    ("smith", "tag", "smith"),
    ("forge", "tag", "smith"),
    ("бедн", "wealth", "poor"),
    ("нищ", "wealth", "poor"),
    ("poor", "wealth", "poor"),
    ("богат", "wealth", "rich"),
    ("зажиточ", "wealth", "rich"),
    ("rich", "wealth", "rich"),
)

_MARKET_RE = re.compile(r"\[\[\s*(?:РЫНОК|MARKET)\s*:\s*([^\]]+)\]\]", re.IGNORECASE)
_PRICE_RE = re.compile(r"\[\[\s*(?:ЦЕНА|PRICE)\s*:\s*([^\]]+)\]\]", re.IGNORECASE)
_GOOD_RE = re.compile(r"\[\[\s*(?:ТОВАР|GOOD)\s*:\s*([^\]]+)\]\]", re.IGNORECASE)


# ── Нормализация и доступ к записям ───────────────────────────────────────
def _norm_key(name):
    return re.sub(r"\s+", " ", (name or "").strip()).lower()


def _norm_loc(name):
    return _norm_key((name or "").strip().strip("<>«»\"'"))


def _markets(world):
    markets = getattr(world, "markets", None)
    if markets is None:
        markets = {}
        world.markets = markets
    return markets


def _goods(world):
    goods = getattr(world, "trade_goods", None)
    if goods is None:
        goods = {}
        world.trade_goods = goods
    return goods


def get_market(world, loc):
    """Явная запись рынка локации (или None)."""
    return _markets(world).get(_norm_loc(loc))


def ensure_market(world, loc):
    """Запись рынка локации; создаётся при необходимости."""
    return _markets(world).setdefault(_norm_loc(loc), {})


def reset_market(world, loc):
    """Снимает ручные поля и мастерские цены; записи мастера остаются."""
    key = _norm_loc(loc)
    markets = _markets(world)
    record = markets.get(key)
    if not record:
        return False
    changed = False
    sources = record.get("src", {})
    for field in ("size", "wealth"):
        if sources.get(field) == "manual":
            record.pop(field, None)
            sources.pop(field, None)
            changed = True
    if record.get("overrides"):
        record["overrides"] = {}
        changed = True
    if not sources:
        record.pop("src", None)
    if not any(record.get(f) for f in ("size", "wealth", "tags", "overrides")):
        markets.pop(key, None)
    return changed


# ── Парсеры слов ──────────────────────────────────────────────────────────
def parse_size(word):
    """Слово → канонический размер («деревня» → village) или None."""
    return SIZE_WORDS.get((word or "").strip().lower())


def parse_wealth(word):
    """Слово → канонический достаток («богатый» → rich) или None."""
    return WEALTH_WORDS.get((word or "").strip().lower())


def parse_tag(word):
    """Слово → канонический тег рынка («портовый» → port) или None."""
    return TAG_WORDS.get((word or "").strip().lower())


# ── Профиль и условия ─────────────────────────────────────────────────────
def infer_profile(loc):
    """Профиль по имени локации («Глухая деревня» → village).

    Таблица упорядочена: частное раньше общего («городок» до «город»),
    первое совпадение выигрывает. Ничего не угадали — пустой профиль
    (нейтральные цены).
    """
    name = _norm_loc(loc)
    if not name:
        return {}
    size = None
    wealth = None
    tags = []
    for word, kind, value in _NAME_HINTS:
        if word not in name:
            continue
        if kind == "size" and size is None:
            size = value
        elif kind == "wealth" and wealth is None:
            wealth = value
        elif kind == "tag" and value not in tags:
            tags.append(value)
    profile = {}
    if size:
        profile["size"] = size
    if wealth:
        profile["wealth"] = wealth
    if tags:
        profile["tags"] = tags
    return profile


def profile_for(world, loc):
    """Итоговый профиль локации и источники полей.

    Источники: "manual" — ручная настройка (!рынок), "dm" — запись мастера
    ([[РЫНОК]]), "auto" — эвристика по имени. Теги объединяются (rec > эвристика).
    """
    record = get_market(world, loc) or {}
    heur = infer_profile(loc)
    src_rec = record.get("src", {})
    profile = {}
    sources = {"size": None, "wealth": None, "tags": {}}
    for field in ("size", "wealth"):
        if field in record:
            profile[field] = record[field]
            sources[field] = "manual" if src_rec.get(field) == "manual" else "dm"
        elif field in heur:
            profile[field] = heur[field]
            sources[field] = "auto"
    tags = []
    for tag in heur.get("tags", []):
        tags.append(tag)
        sources["tags"][tag] = "auto"
    for tag in record.get("tags", []):
        if tag not in tags:
            tags.append(tag)
        sources["tags"][tag] = "dm"
    profile["tags"] = tags
    return profile, sources


def conditions_factor(world):
    """Множитель условий из фактов мира и список сработавших условий.

    Каждый факт даёт не больше одного совпадения (первое по таблице);
    произведение клампится [0.5, 2.0].
    """
    num, den = 1, 1
    matched = []
    for fact in getattr(world, "facts", None) or []:
        low = str(fact).lower()
        for word, label, perm in CONDITION_WORDS:
            if word in low:
                num *= perm
                den *= PERMILLE
                matched.append((label, perm))
                break
    raw = num * PERMILLE // den
    return max(CONDITION_MIN, min(CONDITION_MAX, raw)), matched


# ── Цены ──────────────────────────────────────────────────────────────────
def _scale(base, factors):
    """base × произведение factors(‰) c одним half-up округлением в конце."""
    num, den = base, 1
    for factor in factors:
        num *= factor
        den *= PERMILLE
    return max(1, (num + den // 2) // den)


def lookup_good(world, item):
    """Ищет товар по вхождению: побеждает самое длинное имя (как раньше).

    Возвращает (ключ, база, категория, динамический?) или None.
    """
    text = _norm_key(item)
    best = None
    for key, entry in _goods(world).items():
        if key and key in text:
            best = _pick(
                best, (key, entry.get("base", UNKNOWN_BUY_BASE), entry.get("cat", "misc"), True)
            )
    for name, (base, cat) in GOODS.items():
        if name in text:
            best = _pick(best, (name, base, cat, False))
    return best


def _pick(best, candidate):
    """Длиннее — приоритетнее; при равенстве длины остаётся первый."""
    if best is None or len(candidate[0]) > len(best[0]):
        return candidate
    return best


def _factors(world, category):
    profile, _sources = profile_for(world, getattr(world, "location", ""))
    factors = [
        SIZE_PERMILLE.get(profile.get("size"), PERMILLE),
        WEALTH_PERMILLE.get(profile.get("wealth"), PERMILLE),
    ]
    for tag in profile.get("tags", []):
        factor = TAG_FACTORS.get(tag, {}).get(category)
        if factor:
            factors.append(factor)
    cond, _matched = conditions_factor(world)
    factors.append(cond)
    return factors


def _override(world, loc, key):
    record = get_market(world, loc) or {}
    return (record.get("overrides") or {}).get(key)


def buy_price(world, item, ignore_override=False):
    """Местная цена покупки предмета (минимум 1)."""
    found = lookup_good(world, item)
    factors = _factors(world, found[2] if found else "misc")
    if found and not ignore_override:
        override = _override(world, getattr(world, "location", ""), found[0])
        if override:
            factors.append(override)
    base = found[1] if found else UNKNOWN_BUY_BASE
    return _scale(base, factors)


def sell_price(world, item, ignore_override=False):
    """Местная цена скупки: половина цены покупки (неизвестное — 20 // 2)."""
    found = lookup_good(world, item)
    factors = _factors(world, found[2] if found else "misc")
    if found and not ignore_override:
        override = _override(world, getattr(world, "location", ""), found[0])
        if override:
            factors.append(override)
    base = found[1] if found else UNKNOWN_SELL_BASE
    return max(1, _scale(base, factors) // 2)


def fmt_mult(perm):
    """Промилле → компактный множитель ×1.25 (целочисленно, без float)."""
    return f"×{perm // PERMILLE}.{perm % PERMILLE // 10:02d}"


def _is_alias(name):
    """«зелье» не показываем, если есть «зелье лечения» с той же ценой."""
    base, cat = GOODS[name]
    for other, params in GOODS.items():
        if other != name and name in other and params == (base, cat):
            return True
    return False


def display_goods(world):
    """Товары для показа: каталог (без алиасов) + зарегистрированные."""
    names = [name for name in GOODS if not _is_alias(name)]
    for key, entry in _goods(world).items():
        names.append(entry.get("name") or key)
    return names


def price_rows(world):
    """Строки цен: (имя, покупка, скупка, есть мастерская цена)."""
    loc = getattr(world, "location", "")
    rows = []
    for name in display_goods(world):
        rows.append(
            (
                name,
                buy_price(world, name),
                sell_price(world, name),
                bool(_override(world, loc, _norm_key(name))),
            )
        )
    return rows


# ── Блок [РЫНОК] для мастера ──────────────────────────────────────────────
def _profile_label(value, source):
    label = SIZE_LABELS.get(value) or WEALTH_LABELS.get(value) or value
    suffix = {"dm": " (мастер)", "manual": " (вручную)", "auto": " (по имени)"}
    return label + suffix.get(source, "")


def market_block(world):
    """Блок [РЫНОК] для памяти мастера: профиль, условия, цены (≤450 симв.)."""
    loc = (getattr(world, "location", "") or "").strip()
    if not loc:
        return ""
    profile, sources = profile_for(world, loc)
    cond, matched = conditions_factor(world)

    bits = []
    if profile.get("size"):
        bits.append(_profile_label(profile["size"], sources.get("size")))
    if profile.get("wealth"):
        bits.append("достаток: " + _profile_label(profile["wealth"], sources.get("wealth")))
    if profile.get("tags"):
        bits.append("теги: " + ", ".join(TAG_LABELS.get(tag, tag) for tag in profile["tags"]))
    if not bits:
        bits.append("цены обычные")
    head = f"[РЫНОК] <<{loc}>>: {', '.join(bits)}"
    if matched:
        conds = ", ".join(f"{label} {fmt_mult(perm)}" for label, perm in matched)
        head += f". Условия: {conds} (итог {fmt_mult(cond)})"
    head += ". "

    grammar = (
        "Мастер: [[РЫНОК: <<место>>|город богатый портовый]], "
        "[[ЦЕНА: предмет|N]] (±×2), [[ТОВАР: имя|база|категория]]."
    )
    suffix = "Скупка — половина. " + grammar
    price_bits = [
        f"{name} {buy}" + ("*" if over else "") for name, buy, _sell, over in price_rows(world)
    ]
    full = ", ".join(price_bits)
    prefix = head + "Цены: "
    while price_bits and len(prefix + ", ".join(price_bits) + ". " + suffix) > MARKET_BLOCK_LIMIT:
        price_bits.pop()
    if not price_bits:
        text = head + suffix
    else:
        body = ", ".join(price_bits)
        if len(price_bits) < len(full.split(", ")):
            body += "…"
        text = prefix + body + ". " + suffix
    if len(text) > MARKET_BLOCK_LIMIT:
        text = text[: MARKET_BLOCK_LIMIT - 1].rstrip() + "…"
    return text


# ── Маркеры мастера ───────────────────────────────────────────────────────
def _apply_market_tokens(world, loc, tokens):
    """Токены [[РЫНОК]]: размер/достаток (если не закреплено вручную) и теги."""
    parts = []
    record = None

    def _create():
        nonlocal record
        if record is None:
            record = ensure_market(world, loc)
        return record

    for raw in tokens:
        word = raw.strip(" ,.;:!?()«»<>|").lower()
        if not word:
            continue
        size = parse_size(word)
        if size:
            pinned = (get_market(world, loc) or {}).get("src", {}).get("size") == "manual"
            if pinned:
                continue
            entry = _create()
            entry["size"] = size
            entry.setdefault("src", {})["size"] = "dm"
            parts.append(t("market.size_" + size))
            continue
        wealth = parse_wealth(word)
        if wealth:
            pinned = (get_market(world, loc) or {}).get("src", {}).get("wealth") == "manual"
            if pinned:
                continue
            entry = _create()
            entry["wealth"] = wealth
            entry.setdefault("src", {})["wealth"] = "dm"
            parts.append(t("market.wealth_" + wealth))
            continue
        tag = parse_tag(word)
        if tag:
            entry = _create()
            tags = entry.setdefault("tags", [])
            if tag not in tags:
                tags.append(tag)
                parts.append(t("market.tag_" + tag))
    if record is not None and not any(
        record.get(f) for f in ("size", "wealth", "tags", "overrides")
    ):
        _markets(world).pop(_norm_loc(loc), None)
    return parts


def apply_trade_markers(text, world):
    """Применяет маркеры мастера [[РЫНОК]]/[[ЦЕНА]]/[[ТОВАР]] из ответа.

    Возвращает заметки для игрока (печатает main, уважая тихий режим).
    """
    if not text:
        return []
    notes = []
    for match in _MARKET_RE.finditer(text):
        loc, _, token_str = match.group(1).partition("|")
        loc = loc.strip().strip("<>«»\"'").strip()
        if not loc:
            continue
        parts = _apply_market_tokens(world, loc, token_str.replace(",", " ").split())
        if parts:
            notes.append(t("market.note_profile", loc=loc, parts=", ".join(parts)))

    seen = 0
    for match in _PRICE_RE.finditer(text):
        if seen >= MARKER_CAP_PER_TURN:
            notes.append(t("market.note_cap_price"))
            break
        item, _, price_str = match.group(1).partition("|")
        item = item.strip()
        price_str = price_str.strip()
        if not item or not price_str.isdigit():
            continue
        seen += 1
        found = lookup_good(world, item)
        if not found:
            notes.append(t("market.note_unknown", item=item))
            continue
        engine = buy_price(world, found[0], ignore_override=True)
        if engine <= 0:
            continue
        target = int(price_str)
        ratio = (target * PERMILLE + engine // 2) // engine
        clamped = max(PRICE_CORRIDOR_MIN, min(PRICE_CORRIDOR_MAX, ratio))
        entry = ensure_market(world, getattr(world, "location", ""))
        entry.setdefault("overrides", {})[found[0]] = clamped
        price = buy_price(world, found[0])
        if clamped != ratio:
            notes.append(t("market.note_clamped", item=item, price=price))
        else:
            notes.append(t("market.note_price", item=item, price=price))

    seen = 0
    for match in _GOOD_RE.finditer(text):
        if seen >= MARKER_CAP_PER_TURN:
            notes.append(t("market.note_cap_good"))
            break
        chunks = [chunk.strip() for chunk in match.group(1).split("|")]
        if not chunks or not chunks[0]:
            continue
        name = chunks[0]
        base_str = chunks[1] if len(chunks) > 1 else ""
        cat_str = chunks[2].lower() if len(chunks) > 2 else ""
        if not base_str.isdigit():
            continue
        seen += 1
        key = _norm_key(name)
        if key in GOODS:
            notes.append(t("market.note_known", name=name))
            continue
        base = max(1, min(5000, int(base_str)))
        cat = CATEGORY_WORDS.get(cat_str, "misc")
        goods = _goods(world)
        if key not in goods and len(goods) >= REGISTRY_CAP:
            notes.append(t("market.note_registry_full"))
            continue
        payload = {"name": name, "base": base, "cat": cat}
        if goods.get(key) == payload:
            continue
        goods[key] = payload
        notes.append(t("market.note_good", name=name, base=base))
    return notes
