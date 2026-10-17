#!/usr/bin/env python3
"""Гонки общего состояния: BLACKLIST (openrouter) и статистика (stats).

Тесты «злые» по замыслу: потоки + sys.setswitchinterval(1e-6), без sleep.
Детерминированно красный на разлоченном коде — rebind-тест (перепривязка
BLACKLIST); остальные закрепляют инварианты (точные счётчики, snapshot),
которые сломает любая будущая разлоченная мутация.
"""

import json
import sys
import threading
from datetime import datetime, timedelta

import dndai.api.openrouter as orouter
import dndai.game.stats as stats


def _future(minutes=5):
    return (datetime.now() + timedelta(minutes=minutes)).isoformat()


def test_load_blacklist_updates_in_place(tmp_path, monkeypatch):
    """load_blacklist не перепривязывает BLACKLIST: держатели ссылки видят данные."""
    path = tmp_path / "blacklist.json"
    path.write_text(json.dumps({"TestProv:m1": _future()}), encoding="utf-8")
    monkeypatch.setattr(orouter, "BLACKLIST_PATH", path)
    monkeypatch.setattr(orouter, "BLACKLIST", {})
    ref = orouter.BLACKLIST
    orouter.load_blacklist()
    assert orouter.BLACKLIST is ref
    assert "TestProv:m1" in ref
    assert orouter.is_blocked("TestProv", "m1")


def test_is_blocked_consistent_under_concurrent_reload(tmp_path, monkeypatch):
    """is_blocked переживает конкурентные перезагрузки BLACKLIST без KeyError."""
    path = tmp_path / "blacklist.json"
    monkeypatch.setattr(orouter, "BLACKLIST_PATH", path)
    monkeypatch.setattr(orouter, "BLACKLIST", {})
    stop = threading.Event()
    broken = []

    def reloader():
        try:
            while not stop.is_set():
                path.write_text(json.dumps({"Race:m": _future()}), encoding="utf-8")
                orouter.load_blacklist()
                path.write_text("{}", encoding="utf-8")
                orouter.load_blacklist()
        except Exception as e:
            broken.append(f"reloader: {e!r}")

    def reader():
        try:
            for _ in range(20000):
                orouter.is_blocked("Race", "m")
        except Exception as e:
            broken.append(f"reader: {e!r}")

    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        t_reload = threading.Thread(target=reloader)
        readers = [threading.Thread(target=reader) for _ in range(2)]
        t_reload.start()
        for t in readers:
            t.start()
        for t in readers:
            t.join(timeout=30)
        stop.set()
        t_reload.join(timeout=10)
    finally:
        sys.setswitchinterval(old)
    assert not broken, broken


def test_stats_record_request_no_lost_updates(monkeypatch):
    """Конкурентные инкременты record_request не теряются (8 потоков x 2000)."""
    monkeypatch.setattr(stats, "_stats", {})
    n_threads, n_iter = 8, 2000
    barrier = threading.Barrier(n_threads)

    def worker():
        barrier.wait(timeout=5)
        for _ in range(n_iter):
            stats.record_request("HammerProv", tokens=2, ok=True)

    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
    finally:
        sys.setswitchinterval(old)

    got = stats._stats["HammerProv"]
    assert got["requests"] == n_threads * n_iter
    assert got["tokens"] == 2 * n_threads * n_iter
    assert got["ok"] == n_threads * n_iter


def test_show_stats_survives_concurrent_new_providers(monkeypatch, capsys):
    """show_stats не падает RuntimeError, пока добавляются новые провайдеры."""
    monkeypatch.setattr(
        stats,
        "_stats",
        {
            f"Seed{i}": {"requests": 1, "tokens": 10, "errors": 0, "ok": 1}
            for i in range(40)
        },
    )
    stop = threading.Event()
    broken = []

    def writer():
        try:
            i = 0
            while not stop.is_set():
                stats.record_request(f"Dyn{i % 7}")
                i += 1
        except Exception as e:
            broken.append(f"writer: {e!r}")

    t = threading.Thread(target=writer)
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    t.start()
    try:
        for _ in range(60):
            try:
                stats.show_stats()
            except RuntimeError as e:
                broken.append(f"show_stats: {e!r}")
                break
    finally:
        stop.set()
        t.join(timeout=10)
        sys.setswitchinterval(old)

    assert not broken, broken
