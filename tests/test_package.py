#!/usr/bin/env python3
"""Фасад dndai.api: порядок star-импортов load-bearing (http_session)."""


def test_package_http_session_comes_from_openrouter():
    """dndai.api.http_session — тот же объект, что у openrouter (last-wins)."""
    import dndai.api
    import dndai.api.openrouter

    assert dndai.api.http_session is dndai.api.openrouter.http_session
