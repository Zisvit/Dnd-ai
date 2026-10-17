#!/usr/bin/env python3
"""Статистика запросов по провайдерам для отслеживания лимитов.

API-слой ничего не знает об игре: статистика получает события через
подписку add_request_listener (направление зависимости game -> api).
"""

import threading

from dndai.core.colors import CYAN, GREEN, RED, RESET, YELLOW
from dndai.core.config import PROVIDERS
from dndai.core.i18n import t
from dndai.core.text import emoji

# Счётчики: провайдер -> {"requests": int, "tokens": int, "errors": int, "ok": int}
_stats = {}
_stats_lock = threading.Lock()

for p in PROVIDERS:
    _stats[p["name"]] = {"requests": 0, "tokens": 0, "errors": 0, "ok": 0}


def _on_api_request(provider_name, tokens=0, ok=True):
    record_request(provider_name, tokens=tokens, ok=ok)


# Подписываемся на события API-слоя (идемпотентно)
try:
    from dndai.api.openrouter import add_request_listener
    add_request_listener(_on_api_request)
except Exception:
    pass


def record_request(provider_name, tokens=0, ok=True):
    with _stats_lock:
        if provider_name not in _stats:
            _stats[provider_name] = {"requests": 0, "tokens": 0, "errors": 0, "ok": 0}
        s = _stats[provider_name]
        s["requests"] += 1
        s["tokens"] += tokens
        if ok:
            s["ok"] += 1
        else:
            s["errors"] += 1


def reset_stats():
    with _stats_lock:
        for name in _stats:
            _stats[name] = {"requests": 0, "tokens": 0, "errors": 0, "ok": 0}


def show_stats():
    with _stats_lock:
        snapshot = {name: dict(s) for name, s in _stats.items()}
    print(f"\n{CYAN}{t('stats.title')}{RESET}")
    total_req = 0
    total_tok = 0
    for name, s in snapshot.items():
        total_req += s["requests"]
        total_tok += s["tokens"]
        status = f"{GREEN}{emoji('✅')}{RESET}" if s["ok"] > 0 else (f"{RED}{emoji('❌')}{RESET}" if s["requests"] > 0 else f"{YELLOW}–{RESET}")
        print(f"  {status} {t('stats.row', status=status, name=name, req=s['requests'], ok=s['ok'], err=s['errors'], tok=s['tokens'])}")
    print(f"\n{CYAN}{t('stats.total')}{RESET} запросов {total_req}, токенов ~{total_tok}")
    print(f"{YELLOW}{t('stats.limits')}{RESET}")
