#!/usr/bin/env python3
"""Простое кодирование для API ключей (без внешних зависимостей)"""

import base64
import os
from pathlib import Path
from .config import DATA_DIR
from .logger import info, error

KEY_FILE = DATA_DIR / ".crypto_key"
ENCRYPTED_KEYS_FILE = DATA_DIR / "keys.enc"

def _get_or_create_key() -> bytes:
    """Получает или создаёт ключ для XOR-шифрования"""
    if KEY_FILE.exists():
        with open(KEY_FILE, 'rb') as f:
            return f.read()
    
    # Генерируем случайный 32-байтовый ключ
    key = os.urandom(32)
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
    info("Создан новый ключ шифрования")
    return key

def _xor_encrypt_decrypt(data: bytes, key: bytes) -> bytes:
    """XOR шифрование/дешифрование (симметричное)"""
    return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])

def encrypt_text(text: str) -> str:
    """Шифрует текст (XOR + base64)"""
    try:
        key = _get_or_create_key()
        data = text.encode('utf-8')
        encrypted = _xor_encrypt_decrypt(data, key)
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        error(f"Ошибка шифрования: {e}")
        return ""

def decrypt_text(encrypted_text: str) -> str:
    """Расшифровывает текст"""
    try:
        key = _get_or_create_key()
        encrypted = base64.b64decode(encrypted_text.encode('utf-8'))
        decrypted = _xor_encrypt_decrypt(encrypted, key)
        return decrypted.decode('utf-8')
    except Exception as e:
        error(f"Ошибка расшифровки: {e}")
        return ""

def save_encrypted_keys(keys: list) -> bool:
    """Сохраняет закодированные ключи"""
    try:
        data = "\n".join(keys)
        encrypted = encrypt_text(data)
        with open(ENCRYPTED_KEYS_FILE, 'w', encoding='utf-8') as f:
            f.write(encrypted)
        info(f"Сохранено {len(keys)} ключей (закодировано)")
        return True
    except Exception as e:
        error(f"Ошибка сохранения ключей: {e}")
        return False

def load_encrypted_keys() -> list:
    """Загружает раскодированные ключи"""
    if not ENCRYPTED_KEYS_FILE.exists():
        return []
    
    try:
        with open(ENCRYPTED_KEYS_FILE, 'r', encoding='utf-8') as f:
            encrypted = f.read().strip()
        decrypted = decrypt_text(encrypted)
        if decrypted:
            return [k.strip() for k in decrypted.split('\n') if k.strip()]
    except Exception as e:
        error(f"Ошибка загрузки ключей: {e}")
    
    return []
