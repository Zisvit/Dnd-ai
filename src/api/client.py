#!/usr/bin/env python3
import requests
from src.core.config import URL

http_session = requests.Session()
http_session.headers.update({'Content-Type': 'application/json; charset=utf-8'})

def get_session():
    return http_session
