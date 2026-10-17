#!/usr/bin/env python3
"""Тесты сетевого слоя dndai/api/openrouter.py (без сети).

Принципы (согласованы советом):
- http_session и time.sleep подменяются, реальные сокеты не используются;
- проверяется наблюдаемое поведение (возврат, счётчики уведомлений,
  число HTTP-попыток), а не внутренние приватные вызовы;
- регресс-тесты дефектов №1 (двойной учёт ошибок), №6 (модель из
  tier-таблицы не применялась), №8 (обрыв стрима дублировал текст)
  до фикса падают.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime
import importlib
import json

import pytest

orouter = importlib.import_module("dndai.api.openrouter")
from dndai.core.i18n import t
from dndai.core.task_types import TaskType, ModelTier

PROV = {
    "name": "TestProv",
    "base_url": "http://test.invalid/v1",
    "api_key": "k",
    "models": ["m1"],
    "stream": True,
}


class FakeResponse:
    """Мини-заглушка requests.Response (поддерживает context manager)."""

    def __init__(
        self, status_code=200, json_data=None, text="", headers=None, lines=None
    ):
        self.status_code = status_code
        self._json = {} if json_data is None else json_data
        self.text = text
        self.headers = headers or {}
        self._lines = lines
        self.encoding = "utf-8"
        self.closed = False

    def json(self):
        return self._json

    def iter_lines(self, decode_unicode=False):
        lines = self._lines
        if callable(lines):
            yield from lines()
        else:
            yield from (lines or [])

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    """Заглушка HTTP-сессии: очередь заготовленных ответов.

    Элемент — FakeResponse либо исключение (будет поднято при post).
    Лишний запрос — AssertionError: тест сразу ловит неожиданные ретраи.
    """

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, headers=None, json=None, timeout=None, stream=False):
        self.calls.append(
            {
                "url": url,
                "headers": headers or {},
                "json": json or {},
                "timeout": timeout,
                "stream": stream,
            }
        )
        if not self.responses:
            raise AssertionError("неожиданный лишний HTTP-запрос")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def ok_response(content="Привет, странник."):
    return FakeResponse(200, json_data={"choices": [{"message": {"content": content}}]})


def sse_content(chunk):
    payload = json.dumps(
        {"choices": [{"delta": {"content": chunk}}]}, ensure_ascii=False
    )
    return f"data: {payload}".encode("utf-8")


DONE = b"data: [DONE]"


def break_after(*chunks, exc=None):
    """Функция-генератор строк, падающая «сетевым» исключением после chunks."""

    def gen():
        for c in chunks:
            yield c
        raise exc or ConnectionError("обрыв соединения")

    return gen


@pytest.fixture(autouse=True)
def isolate_orouter(monkeypatch, tmp_path):
    """Изоляция глобального состояния модуля между тестами."""
    monkeypatch.setattr(orouter, "PROVIDERS", [])
    monkeypatch.setattr(orouter, "BLACKLIST", {})
    monkeypatch.setattr(orouter, "BLACKLIST_PATH", tmp_path / "blacklist.json")
    monkeypatch.setattr(orouter, "_request_listeners", [])
    monkeypatch.setattr(orouter, "http_session", FakeSession([]))
    monkeypatch.setattr(orouter.time, "sleep", lambda *_: None)
    yield


def collect_notifications():
    calls = []
    orouter.add_request_listener(lambda p, tok, ok: calls.append((p, tok, ok)))
    return calls


# ── translate_api_error / _classify / _is_refusal / first-prompt ────────────


def test_translate_api_error_basic_codes():
    assert orouter.translate_api_error(401) == t("api.error_401")
    assert orouter.translate_api_error(403) == t("api.error_403")
    assert orouter.translate_api_error(404) == t("api.error_404")
    assert orouter.translate_api_error(408) == t("api.error_timeout")
    assert orouter.translate_api_error(0) == t("api.error_network")
    assert orouter.translate_api_error(500) == t("api.error_server", status=500)
    assert orouter.translate_api_error(418) == t("api.error_unknown", status=418)


def test_translate_api_error_400_tokens():
    assert orouter.translate_api_error(400) == t("api.error_400")
    assert orouter.translate_api_error(400, body="max_tokens is too large") == t(
        "api.error_400_tokens"
    )


def test_translate_api_error_429_reset_from_headers_and_body():
    ts = 1700000000
    expected = t(
        "api.error_429_reset",
        time=datetime.datetime.fromtimestamp(ts).strftime("%d.%m %H:%M"),
    )
    assert (
        orouter.translate_api_error(429, headers={"X-RateLimit-Reset": str(ts)})
        == expected
    )
    # миллисекунды
    assert (
        orouter.translate_api_error(429, headers={"x-ratelimit-reset": str(ts * 1000)})
        == expected
    )
    # время сброса в теле ответа
    assert (
        orouter.translate_api_error(429, body='{"X-RateLimit-Reset": %d}' % ts)
        == expected
    )


def test_translate_api_error_429_variants():
    assert orouter.translate_api_error(429, body="free-models-per-day exceeded") == t(
        "api.error_429"
    )
    assert orouter.translate_api_error(429, body="rate limit reached") == t(
        "api.error_429"
    )
    assert orouter.translate_api_error(429, body="not enough credits") == t(
        "api.error_credits"
    )
    assert orouter.translate_api_error(429) == t("api.error_rate")


def test_classify_kinds():
    assert orouter._classify(401) == "auth"
    assert orouter._classify(403) == "auth"
    assert orouter._classify(429) == "limits"
    assert orouter._classify(0) == "network"
    assert orouter._classify(500) == "server"
    assert orouter._classify(408) == "server"
    assert orouter._classify(400) == "other"


def test_is_refusal():
    assert orouter._is_refusal("Извините, но я не могу продолжать эту историю.")
    assert not orouter._is_refusal("Вы входите в <<Таверну>>, {{Бармен}} кивает.")


def test_looks_like_first_prompt():
    first = t("main.first_prompt_tavern")
    assert orouter._looks_like_first_prompt([{"role": "user", "content": first}])
    assert not orouter._looks_like_first_prompt(
        [{"role": "assistant", "content": first}]
    )
    assert not orouter._looks_like_first_prompt(
        [{"role": "user", "content": first}, {"role": "user", "content": first}]
    )
    assert not orouter._looks_like_first_prompt([])


# ── blacklist ────────────────────────────────────────────────────────────────


def test_blacklist_roundtrip_via_file():
    orouter.block_model("TestProv", "m1", minutes=60)
    assert orouter.is_blocked("TestProv", "m1")
    assert orouter.BLACKLIST_PATH.exists()

    orouter.BLACKLIST.clear()
    assert not orouter.is_blocked("TestProv", "m1")

    orouter.load_blacklist()
    assert orouter.is_blocked("TestProv", "m1")


def test_blacklist_expired_not_blocked():
    orouter.block_model("TestProv", "m2", minutes=-1)
    assert not orouter.is_blocked("TestProv", "m2")


# ── api_request: не-стриминговый путь ───────────────────────────────────────


def test_api_request_success(monkeypatch):
    session = FakeSession([ok_response()])
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()

    text, err, kind = orouter.api_request(
        PROV, "m1", [{"role": "user", "content": "hi"}], max_tok=111
    )

    assert (text, err, kind) == ("Привет, странник.", None, None)
    call = session.calls[0]
    assert call["json"]["model"] == "m1"
    assert call["json"]["max_tokens"] == 111
    assert call["json"]["stream"] is False
    assert call["headers"]["Authorization"] == "Bearer k"
    assert notes == [("TestProv", len("Привет, странник.") // 4, True)]


def test_api_request_empty_and_refusal(monkeypatch):
    monkeypatch.setattr(
        orouter,
        "http_session",
        FakeSession([FakeResponse(200, json_data={"choices": []})]),
    )
    notes = collect_notifications()
    assert orouter.api_request(PROV, "m1", []) == (
        None,
        t("api.error_unknown", status=200),
        "empty",
    )
    assert notes == [("TestProv", 0, False)]

    monkeypatch.setattr(
        orouter, "http_session", FakeSession([ok_response("Я не могу это сделать.")])
    )
    notes = collect_notifications()
    assert orouter.api_request(PROV, "m1", []) == (None, t("api.refusal"), "refusal")
    assert notes == [("TestProv", 0, False)]


def test_api_request_without_key_forbidden():
    prov = {"name": "NoKey", "base_url": "http://x", "api_key": "", "models": []}
    assert orouter.api_request(prov, "m1", []) == (
        None,
        t("api.no_provider_key"),
        "other",
    )


def test_api_request_429_retry_then_success(monkeypatch):
    session = FakeSession([FakeResponse(429, text="rate limit"), ok_response("Успех")])
    monkeypatch.setattr(orouter, "http_session", session)
    text, err, kind = orouter.api_request(PROV, "m1", [])
    assert (text, err, kind) == ("Успех", None, None)
    assert len(session.calls) == 2


def test_api_request_401_blocks_without_retry(monkeypatch):
    session = FakeSession([FakeResponse(401, text="unauthorized")])
    monkeypatch.setattr(orouter, "http_session", session)
    text, err, kind = orouter.api_request(PROV, "m1", [])
    assert (text, err, kind) == (None, t("api.error_401"), "auth")
    assert len(session.calls) == 1
    assert orouter.is_blocked("TestProv", "m1")


def test_api_request_400_no_retry(monkeypatch):
    session = FakeSession([FakeResponse(400, text="bad request")])
    monkeypatch.setattr(orouter, "http_session", session)
    assert orouter.api_request(PROV, "m1", []) == (None, t("api.error_400"), "other")
    assert len(session.calls) == 1


def test_api_request_500_exhausts_three_attempts(monkeypatch):
    session = FakeSession([FakeResponse(500, text="boom")] * 3)
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()
    text, err, kind = orouter.api_request(PROV, "m1", [])
    assert text is None
    assert err == t("api.error_server", status=500)
    assert kind == "server"
    assert len(session.calls) == 3
    assert notes == [("TestProv", 0, False)] * 3


def test_api_request_network_exception_retries(monkeypatch):
    session = FakeSession([ConnectionError("reset")] * 3)
    monkeypatch.setattr(orouter, "http_session", session)
    text, err, kind = orouter.api_request(PROV, "m1", [])
    assert text is None
    assert kind == "network"
    assert t("api.error_network") in err
    assert len(session.calls) == 3


def test_api_request_ollama_caps_tokens_and_disables_stream(monkeypatch):
    prov = {
        "name": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "api_key": "",
        "models": ["llama3:8b"],
    }
    session = FakeSession([ok_response("Локальный ответ")])
    monkeypatch.setattr(orouter, "http_session", session)
    text, err, kind = orouter.api_request(
        prov, "llama3:8b", [], max_tok=1000, stream=True
    )
    assert (text, err, kind) == ("Локальный ответ", None, None)
    assert session.calls[0]["json"]["max_tokens"] == 200
    assert session.calls[0]["json"]["stream"] is False


# ── _do_streaming_request: прямой вызов ─────────────────────────────────────


def test_streaming_collects_chunks_and_stops_at_done(monkeypatch):
    r = FakeResponse(
        200,
        lines=[
            b"",
            b": ping",
            b"event: tick",
            sse_content("При"),
            sse_content("вет"),
            b"not-data-line",
            DONE,
            sse_content("строка после DONE игнорируется"),
        ],
    )
    monkeypatch.setattr(orouter, "http_session", FakeSession([r]))
    tokens = []
    text, err, kind = orouter._do_streaming_request(
        PROV, "m1", {}, {}, 5, tokens.append
    )
    assert (text, err, kind) == ("Привет", None, None)
    assert tokens == ["При", "вет"]
    assert r.closed


def test_streaming_broken_chunk_keeps_partial_text(monkeypatch):
    monkeypatch.setattr(
        orouter,
        "http_session",
        FakeSession(
            [FakeResponse(200, lines=[sse_content("Начало"), b'data: {"broken"'])]
        ),
    )
    tokens = []
    text, err, kind = orouter._do_streaming_request(
        PROV, "m1", {}, {}, 5, tokens.append
    )
    assert (text, err, kind) == ("Начало", None, None)
    # маркер обрыва уходит на экран (on_token), но не попадает в текст истории
    assert tokens == ["Начало", "\n\n" + t("api.stream_truncated")]


def test_streaming_network_break_keeps_partial_text(monkeypatch):
    monkeypatch.setattr(
        orouter,
        "http_session",
        FakeSession([FakeResponse(200, lines=break_after(sse_content("Часть")))]),
    )
    tokens = []
    text, err, kind = orouter._do_streaming_request(
        PROV, "m1", {}, {}, 5, tokens.append
    )
    assert (text, err, kind) == ("Часть", None, None)
    assert tokens == ["Часть", "\n\n" + t("api.stream_truncated")]


def test_streaming_empty_and_broken_empty(monkeypatch):
    monkeypatch.setattr(
        orouter, "http_session", FakeSession([FakeResponse(200, lines=[DONE])])
    )
    assert orouter._do_streaming_request(PROV, "m1", {}, {}, 5, None) == (
        None,
        t("api.empty_response"),
        "empty",
    )

    monkeypatch.setattr(
        orouter,
        "http_session",
        FakeSession([FakeResponse(200, lines=[b'data: {"broken"'])]),
    )
    assert orouter._do_streaming_request(PROV, "m1", {}, {}, 5, None) == (
        None,
        t("api.stream_broken"),
        "network",
    )


def test_streaming_non_200(monkeypatch):
    r = FakeResponse(429, text="rate limit")
    monkeypatch.setattr(orouter, "http_session", FakeSession([r]))
    assert orouter._do_streaming_request(PROV, "m1", {}, {}, 5, None) == (
        None,
        t("api.error_429"),
        "limits",
    )
    assert r.closed


# ── уведомления статистики (регресс №1) ─────────────────────────────────────


def test_stream_refusal_notifies_once(monkeypatch):
    session = FakeSession(
        [FakeResponse(200, lines=[sse_content("Я не могу это сделать."), DONE])]
    )
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()
    text, err, kind = orouter.api_request(PROV, "m1", [], stream=True)
    assert (text, err, kind) == (None, t("api.refusal"), "refusal")
    assert len(session.calls) == 1
    assert notes == [("TestProv", 0, False)]


def test_stream_empty_notifies_once(monkeypatch):
    session = FakeSession([FakeResponse(200, lines=[DONE])])
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()
    text, err, kind = orouter.api_request(PROV, "m1", [], stream=True)
    assert (text, err, kind) == (None, t("api.empty_response"), "empty")
    assert len(session.calls) == 1
    assert notes == [("TestProv", 0, False)]


def test_stream_broken_empty_notifies_once_per_attempt(monkeypatch):
    session = FakeSession([FakeResponse(200, lines=[b'data: {"broken"'])] * 3)
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()
    text, err, kind = orouter.api_request(PROV, "m1", [], stream=True)
    assert text is None
    assert err == t("api.stream_broken")
    assert kind == "network"
    assert len(session.calls) == 3
    assert notes == [("TestProv", 0, False)] * 3


def test_stream_success_notifies_once(monkeypatch):
    session = FakeSession([FakeResponse(200, lines=[sse_content("Hello"), DONE])])
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()
    text, err, kind = orouter.api_request(PROV, "m1", [], stream=True)
    assert (text, err, kind) == ("Hello", None, None)
    assert notes == [("TestProv", len("Hello") // 4, True)]


def test_stats_one_error_per_failed_stream(monkeypatch):
    """Регресс №1 на уровне статистики: один провал = один учёт ошибки."""
    stats_mod = importlib.import_module("dndai.game.stats")
    session = FakeSession(
        [FakeResponse(200, lines=[sse_content("Я не могу это сделать."), DONE])]
    )
    monkeypatch.setattr(orouter, "http_session", session)
    orouter.add_request_listener(stats_mod._on_api_request)

    stats_mod.reset_stats()
    text, err, kind = orouter.api_request(PROV, "m1", [], stream=True)
    assert (text, err, kind) == (None, t("api.refusal"), "refusal")

    assert stats_mod._stats["TestProv"] == {
        "requests": 1,
        "tokens": 0,
        "errors": 1,
        "ok": 0,
    }


# ── обрыв стрима: ретраи (регресс №8) ───────────────────────────────────────


def test_stream_break_after_content_does_not_retry(monkeypatch):
    session = FakeSession([FakeResponse(200, lines=break_after(sse_content("Часть")))])
    monkeypatch.setattr(orouter, "http_session", session)
    notes = collect_notifications()
    tokens = []
    text, err, kind = orouter.api_request(
        PROV, "m1", [], stream=True, on_token=tokens.append
    )
    assert (text, err, kind) == ("Часть", None, None)
    assert tokens == ["Часть", "\n\n" + t("api.stream_truncated")]
    assert len(session.calls) == 1  # без полного повтора
    assert notes == [("TestProv", 1, True)]


def _break_instant():
    raise ConnectionError("обрыв до первого байта")
    yield b""  # noqa: недостижимо — делает функцию генератором


def test_stream_break_before_first_byte_retries(monkeypatch):
    session = FakeSession([FakeResponse(200, lines=_break_instant)] * 3)
    monkeypatch.setattr(orouter, "http_session", session)
    text, err, kind = orouter.api_request(PROV, "m1", [], stream=True)
    assert text is None
    assert err == t("api.stream_broken")
    assert kind == "network"
    assert len(session.calls) == 3  # лимит попыток — 3


# ── _iter_providers_for_task (регресс №6) ───────────────────────────────────


def _fake_providers():
    return [
        {
            "name": "Groq",
            "base_url": "http://g",
            "api_key": "k",
            "models": ["openai/gpt-oss-120b"],
        },
        {
            "name": "OpenRouter",
            "base_url": "http://o",
            "api_key": "k",
            "models": ["stealth/ox-alpha"],
        },
        {
            "name": "Gemini",
            "base_url": "http://m",
            "api_key": "",
            "models": ["gemini-3.6-flash"],
        },
    ]


TABLES = {
    "Groq": {
        ModelTier.FAST: ["groq-mini"],
        ModelTier.BALANCED: ["groq-mid"],
        ModelTier.SMART: ["groq-big"],
    },
    "OpenRouter": {
        ModelTier.FAST: ["or-small"],
        ModelTier.BALANCED: ["or-mid"],
        ModelTier.SMART: ["or-big"],
    },
    "Gemini": {
        ModelTier.FAST: ["gem-fast"],
        ModelTier.BALANCED: ["gem-mid"],
        ModelTier.SMART: ["gem-big"],
    },
}


def _patch_tier_tables(
    monkeypatch,
    task_type=TaskType.SIMPLE,
    tier=ModelTier.FAST,
    preferred=("Groq", "OpenRouter"),
):
    monkeypatch.setattr(orouter, "PROVIDERS", _fake_providers())
    monkeypatch.setattr(orouter, "PROVIDER_MODELS_BY_TIER", TABLES)
    monkeypatch.setattr(orouter, "TASK_DEFAULT_TIER", {task_type: tier})
    monkeypatch.setattr(orouter, "TIER_PROVIDER_PREFERENCE", {tier: list(preferred)})


def test_iter_priority_order_and_key_filter(monkeypatch):
    _patch_tier_tables(monkeypatch)
    got = [(p["name"], m) for p, m in orouter._iter_providers_for_task(TaskType.SIMPLE)]
    assert got == [("Groq", "groq-mini"), ("OpenRouter", "or-small")]


def test_iter_skips_blocked_model(monkeypatch):
    _patch_tier_tables(monkeypatch)
    orouter.block_model("Groq", "groq-mini")
    got = [(p["name"], m) for p, m in orouter._iter_providers_for_task(TaskType.SIMPLE)]
    assert got == [("OpenRouter", "or-small")]


def test_iter_forced_model_from_provider_list(monkeypatch):
    monkeypatch.setattr(orouter, "PROVIDERS", _fake_providers())
    got = [
        (p["name"], m)
        for p, m in orouter._iter_providers_for_task(
            TaskType.NARRATIVE, forced_model="openai/gpt-oss-120b"
        )
    ]
    assert got == [("Groq", "openai/gpt-oss-120b")]


def test_iter_forced_model_from_tier_table(monkeypatch):
    """Регресс №6: модель из tier-таблицы (принимается /model) должна применяться."""
    tables = dict(TABLES)
    tables["OpenRouter"] = {
        ModelTier.FAST: ["or-small"],
        ModelTier.BALANCED: ["or-mid"],
        ModelTier.SMART: ["deepseek/deepseek-r1:free"],
    }
    monkeypatch.setattr(orouter, "PROVIDERS", _fake_providers())
    monkeypatch.setattr(orouter, "PROVIDER_MODELS_BY_TIER", tables)
    monkeypatch.setattr(
        orouter, "TASK_DEFAULT_TIER", {TaskType.NARRATIVE: ModelTier.BALANCED}
    )
    monkeypatch.setattr(
        orouter,
        "TIER_PROVIDER_PREFERENCE",
        {ModelTier.BALANCED: ["Groq", "OpenRouter"]},
    )
    forced = "deepseek/deepseek-r1:free"
    got = [
        (p["name"], m)
        for p, m in orouter._iter_providers_for_task(
            TaskType.NARRATIVE, forced_model=forced
        )
    ]
    assert got == [("OpenRouter", forced)]


def test_iter_unknown_forced_model_falls_back_to_auto(monkeypatch):
    _patch_tier_tables(monkeypatch, TaskType.NARRATIVE, ModelTier.BALANCED)
    got = [
        (p["name"], m)
        for p, m in orouter._iter_providers_for_task(
            TaskType.NARRATIVE, forced_model="nope/missing"
        )
    ]
    assert got == [
        ("Groq", "groq-mid"),
        ("OpenRouter", "or-mid"),
        ("Groq", "groq-mini"),
        ("OpenRouter", "or-small"),
    ]


# ── _get_models_for_tier: динамические модели Ollama ────────────────────────


def test_get_models_for_tier_ollama_dynamic(monkeypatch):
    models = ["qwen2.5:3b", "gemma3:12b", "llama3:70b", "mythical-dnd-model:latest"]
    monkeypatch.setattr(orouter, "get_ollama_models", lambda: models)
    assert set(orouter._get_models_for_tier("Ollama-Server", ModelTier.FAST)) == {
        "qwen2.5:3b"
    }
    assert orouter._get_models_for_tier("Ollama-Server", ModelTier.BALANCED) == [
        "gemma3:12b"
    ]
    assert set(orouter._get_models_for_tier("Ollama-Server", ModelTier.SMART)) == {
        "llama3:70b",
        "mythical-dnd-model:latest",
    }


def test_get_models_for_tier_ollama_static_fallback(monkeypatch):
    monkeypatch.setattr(orouter, "get_ollama_models", lambda: [])
    expected = orouter.PROVIDER_MODELS_BY_TIER.get("Ollama-Server", {}).get(
        ModelTier.FAST, []
    )
    assert orouter._get_models_for_tier("Ollama-Server", ModelTier.FAST) == expected


# ── ask_dm ───────────────────────────────────────────────────────────────────


def _install_providers(monkeypatch):
    monkeypatch.setattr(orouter, "PROVIDERS", [PROV])


def test_ask_dm_no_providers():
    # PROVIDERS пуст (autouse-фикстура) — ранний выход без сети
    text, model, err, streamed = orouter.ask_dm(
        [{"role": "user", "content": "привет"}], ""
    )
    assert (text, model, streamed) == (None, None, False)
    assert err == t("api.no_keys")


def test_ask_dm_success_builds_messages(monkeypatch):
    _install_providers(monkeypatch)
    captured = []

    def fake_api(provider, model, messages, max_tok, stream=False, on_token=None):
        captured.append(
            {"model": model, "messages": messages, "max_tok": max_tok, "stream": stream}
        )
        return "Ответ мастера", None, None

    monkeypatch.setattr(orouter, "api_request", fake_api)
    dnd_config = importlib.import_module("dndai.core.config")
    monkeypatch.setattr(dnd_config, "STREAM_MODE", False)

    history = [{"role": "user", "content": "привет"}]
    text, model, err, streamed = orouter.ask_dm(
        history, "ПАМЯТЬ", "привет", forced_model="m1"
    )
    assert (text, model, err, streamed) == ("Ответ мастера", "m1", None, False)
    assert orouter.get_current_model() == "TestProv:m1"

    call = captured[0]
    expected_sys = orouter.SYSTEM_PROMPT_TEMPLATE.replace(
        "{detail}", orouter.DETAIL_LEVELS.get(0, orouter.DETAIL_LEVELS[0])
    )
    assert call["messages"][0] == {"role": "system", "content": expected_sys}
    assert call["messages"][1] == {"role": "system", "content": "ПАМЯТЬ"}
    assert call["messages"][2] == history[0]
    assert call["max_tok"] == orouter.MAX_TOKENS_BY_DETAIL[0]


def test_ask_dm_first_message_uses_first_prompt(monkeypatch):
    _install_providers(monkeypatch)
    captured = []

    def fake_api(provider, model, messages, max_tok, stream=False, on_token=None):
        captured.append({"messages": messages, "max_tok": max_tok})
        return "Добро пожаловать", None, None

    monkeypatch.setattr(orouter, "api_request", fake_api)
    first = t("main.first_prompt_tavern")
    text, model, err, streamed = orouter.ask_dm(
        [{"role": "user", "content": first}], "", first, forced_model="m1"
    )
    assert text == "Добро пожаловать"
    assert captured[0]["messages"][0] == {
        "role": "system",
        "content": orouter.FIRST_MESSAGE_PROMPT,
    }
    assert captured[0]["max_tok"] == orouter.FIRST_MESSAGE_MAX_TOKENS


@pytest.mark.parametrize(
    "forced_detail,last_user,effective",
    [(0, "опиши подробнее", 1), (2, "привет", 2)],
)
def test_ask_dm_detail_levels(monkeypatch, forced_detail, last_user, effective):
    _install_providers(monkeypatch)
    captured = []

    def fake_api(provider, model, messages, max_tok, stream=False, on_token=None):
        captured.append({"messages": messages, "max_tok": max_tok})
        return "ок", None, None

    monkeypatch.setattr(orouter, "api_request", fake_api)
    orouter.ask_dm(
        [{"role": "user", "content": "что дальше"}],
        "",
        last_user,
        forced_model="m1",
        forced_detail_level=forced_detail,
    )
    call = captured[0]
    assert call["max_tok"] == orouter.MAX_TOKENS_BY_DETAIL[effective]
    expected_sys = orouter.SYSTEM_PROMPT_TEMPLATE.replace(
        "{detail}", orouter.DETAIL_LEVELS.get(effective, orouter.DETAIL_LEVELS[0])
    )
    assert call["messages"][0]["content"] == expected_sys


def test_ask_dm_jailbreak_fallback(monkeypatch):
    _install_providers(monkeypatch)
    captured = []

    def fake_api(provider, model, messages, max_tok, stream=False, on_token=None):
        captured.append({"messages": messages, "max_tok": max_tok, "stream": stream})
        if len(captured) == 1:
            return None, "отказ", "other"
        return "Спасённый ответ", None, None

    monkeypatch.setattr(orouter, "api_request", fake_api)
    text, model, err, streamed = orouter.ask_dm(
        [{"role": "user", "content": "привет"}], "", "привет", forced_model="m1"
    )
    assert (text, model, err, streamed) == ("Спасённый ответ", "m1", None, False)
    assert captured[1]["messages"][0] == {
        "role": "system",
        "content": orouter.JAILBREAK_PROMPT,
    }
    assert captured[1]["stream"] is False
    assert captured[1]["max_tok"] == min(
        orouter.MAX_TOKENS_BY_DETAIL[0], orouter.JAILBREAK_MAX_TOKENS
    )


@pytest.mark.parametrize(
    "kind,key",
    [
        ("limits", "api.all_failed_limits"),
        ("auth", "api.all_failed_auth"),
        ("network", "api.all_failed_network"),
        ("refusal", "api.refusal"),
        ("other", "api.all_failed"),
    ],
)
def test_ask_dm_error_summary_by_kind(monkeypatch, kind, key):
    _install_providers(monkeypatch)
    monkeypatch.setattr(orouter, "api_request", lambda *a, **k: (None, "e", kind))
    text, model, err, streamed = orouter.ask_dm(
        [{"role": "user", "content": "привет"}], "", "привет", forced_model="m1"
    )
    assert (text, model, streamed) == (None, None, False)
    assert err == t(key)
