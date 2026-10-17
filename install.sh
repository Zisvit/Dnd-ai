#!/usr/bin/env bash
# Установка DnD AI Master: venv рядом с проектом, пакет dndai и команда dndd.
#
# Пути не хардкодятся: каталог проекта вычисляется от самого скрипта,
# зависимости описаны в pyproject.toml, дом данных — ~/.dnd_ai (DND_AI_HOME).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
DATA_HOME="${DND_AI_HOME:-$HOME/.dnd_ai}"

echo "Установка DnD AI Master из $PROJECT_DIR"

# 1. Системные пакеты: python3 (+venv/git)
if [ -d /data/data/com.termux ]; then
    echo "Обнаружен Termux..."
    pkg install -y python git
    BIN_DIR="$PREFIX/bin"
else
    echo "Обнаружен Linux..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-venv git
    fi
    BIN_DIR="/usr/local/bin"
fi

# 2. Виртуальное окружение и пакет
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$PROJECT_DIR"

# 3. Команда dndd: минимальный shim на sh, без cd (cwd пользователя не меняем)
SHIM="$(mktemp)"
{
    printf '#!/bin/sh\n'
    printf 'exec "%s/bin/python" -m dndai "$@"\n' "$VENV_DIR"
} > "$SHIM"
if [ -w "$BIN_DIR" ]; then
    cp "$SHIM" "$BIN_DIR/dndd"
    chmod 755 "$BIN_DIR/dndd"
else
    sudo cp "$SHIM" "$BIN_DIR/dndd"
    sudo chmod 755 "$BIN_DIR/dndd"
fi
rm -f "$SHIM"

# 4. Дом данных и шаблон ключей (существующие файлы не трогаем)
mkdir -p "$DATA_HOME"
if [ ! -f "$DATA_HOME/.env" ] && [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$DATA_HOME/.env"
    echo "Создан шаблон ключей: $DATA_HOME/.env"
fi

echo
echo "Готово. Проверка: $VENV_DIR/bin/dndd --version"
echo "  Запуск:   dndd [имя-сессии]   (из любого каталога)"
echo "  Ключи:    $DATA_HOME/.env"
echo "  Промпты:  dndd --copy-prompts → правка в $DATA_HOME/prompts"
echo "  Обновление после git pull: ./install.sh"
echo "  Альтернатива (изоляция):   pipx install $PROJECT_DIR"
