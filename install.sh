#!/bin/bash
echo "Установка D&D..."

# Проверяем, что мы в Termux
if [ -d /data/data/com.termux ]; then
    echo "Установка в Termux..."
    pkg update && pkg upgrade -y
    pkg install python git -y
fi

# Клонируем проект
if [ ! -d "dnd-AI-bot-termux" ]; then
    git clone https://github.com/axemanchik/dnd-AI-bot-termux.git
fi
cd dnd-AI-bot-termux

# Устанавливаем зависимости
pip install -r requirements.txt

# Создаём команду dnd
echo '#!/bin/bash
cd ~/dnd-AI-bot-termux
python src/main.py "$@"' > $PREFIX/bin/dnd
chmod +x $PREFIX/bin/dnd

echo ""
echo "Установка завершена!"
echo "Запуск: dnd"
