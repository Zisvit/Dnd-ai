#!/usr/bin/env python3
"""Общий HTTP-клиент (keep-alive пул соединений).

Заголовки запроса (Content-Type, Authorization) задаются в api_request
персильно — глобальные заголовки на всей Session были бы грязью.
"""
import requests


http_session = requests.Session()


def get_session():
    return http_session
