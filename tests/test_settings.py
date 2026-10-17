#!/usr/bin/env python3
"""Кэш списка моделей Ollama: TTL, только непустой успех, reset."""

import pytest

import dndai.core.config.settings as settings


@pytest.fixture(autouse=True)
def _clean_ollama_cache(monkeypatch):
    monkeypatch.delenv("OLLAMA_CACHE_TTL", raising=False)
    settings.reset_ollama_models_cache()
    yield
    settings.reset_ollama_models_cache()


def _install_dynamic_provider(monkeypatch, url="http://test-ollama"):
    monkeypatch.setattr(
        settings,
        "PROVIDER_DEFS",
        [
            {
                "name": "Ollama-Server",
                "env_key": None,
                "base_url": "http://test-ollama/v1/chat/completions",
                "models": ["hardcoded-model"],
                "dynamic_models": True,
                "ollama_api_url": url,
            }
        ],
    )


def test_ollama_models_cached(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return ["m1", "m2"]

    _install_dynamic_provider(monkeypatch)
    monkeypatch.setattr(settings, "fetch_ollama_models", fake_fetch)
    assert settings.get_ollama_models() == ["m1", "m2"]
    assert settings.get_ollama_models() == ["m1", "m2"]
    assert calls == ["http://test-ollama"]


def test_ollama_models_empty_result_not_cached(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return []

    _install_dynamic_provider(monkeypatch)
    monkeypatch.setattr(settings, "fetch_ollama_models", fake_fetch)
    assert settings.get_ollama_models() == ["hardcoded-model"]
    assert settings.get_ollama_models() == ["hardcoded-model"]
    assert len(calls) == 2


def test_ollama_models_reset_refetches(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return ["m1"]

    _install_dynamic_provider(monkeypatch)
    monkeypatch.setattr(settings, "fetch_ollama_models", fake_fetch)
    assert settings.get_ollama_models() == ["m1"]
    settings.reset_ollama_models_cache()
    assert settings.get_ollama_models() == ["m1"]
    assert len(calls) == 2


def test_ollama_models_ttl_expiry(monkeypatch):
    calls = []
    now = [1000.0]
    monkeypatch.setattr(settings, "_monotonic", lambda: now[0])

    def fake_fetch(url):
        calls.append(url)
        return ["m1"]

    _install_dynamic_provider(monkeypatch)
    monkeypatch.setattr(settings, "fetch_ollama_models", fake_fetch)
    assert settings.get_ollama_models() == ["m1"]  # fetch #1
    now[0] += 299.0
    assert settings.get_ollama_models() == ["m1"]  # ещё кэш
    assert len(calls) == 1
    now[0] += 2.0  # 301с > 300с — TTL истёк
    assert settings.get_ollama_models() == ["m1"]  # fetch #2
    assert len(calls) == 2


def test_ollama_models_ttl_env_zero_disables_cache(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return ["m1"]

    _install_dynamic_provider(monkeypatch)
    monkeypatch.setattr(settings, "fetch_ollama_models", fake_fetch)
    monkeypatch.setenv("OLLAMA_CACHE_TTL", "0")
    assert settings.get_ollama_models() == ["m1"]
    assert settings.get_ollama_models() == ["m1"]
    assert len(calls) == 2
