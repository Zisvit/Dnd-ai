# 🎲 D&D Cyberpunk Master Bot

Киберпанк-мастер для игры в Dungeons & Dragons с поддержкой OpenRouter AI.

## Установка в Termux

```bash
pkg update && pkg upgrade -y
pkg install python git -y
pip install -r requirements.txt
```

## Запуск

```bash
python dnd_bot.py
# или с именем сессии
python dnd_bot.py my_campaign
```

## Команды

- красный/жёлтый/синий – переключить модель
- детальнее – повысить детализацию
- короче – сбросить детализацию
- теперь меня зовут X – сменить имя
- очистить/сброс – новая игра
- dm: приказ – прямой приказ мастеру
- d20 – бросить кубик

## API ключи

При первом запуске бот запросит ключи OpenRouter.
Получить: https://openrouter.ai/keys
