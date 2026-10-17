# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

## [1.0.0] - 2026-10-17

Первый публичный релиз: установка как pip-пакета, единый дом данных, версии.

### Добавлено

- Пакет `dndai` (pyproject.toml), консольная команда `dndd` и запуск
  `python -m dndai`.
- `--version` / `-V`, `--copy-prompts`; коды возврата 0/1/2/130.
- Каталог данных `~/.dnd_ai` (переопределяется `DND_AI_HOME`): сессии,
  blacklist, история ввода. При запуске из старой раскладки репозитория
  данные (`data/`, `dnd_sessions/`) переносятся автоматически один раз
  (маркер `.migrations.json`, источники не трогаются).
- Тесты: изоляция дома данных (`tests/conftest.py`), страж версии
  (`__version__` ↔ CHANGELOG), CLI-тесты.
- CI (GitHub Actions): тесты на Python 3.9/3.13 + сборка wheel с проверкой
  промптов внутри и смоук-установкой.

### Изменено

- Точка входа: `main(argv) -> int` с argparse; имя сессии валидируется
  (без разделителей пути и `..`, до 64 символов).
- Промпты: приоритет `$DND_PROMPTS_DIR` → `~/.dnd_ai/prompts` → пакет;
  автокопии при запуске нет, сидирование — `--copy-prompts`.
- `.env` читается только по явным путям: процесс → `./.env` →
  `~/.dnd_ai/.env` (no-arg `load_dotenv()` убран).
- Установка: `install.sh` создаёт venv и shim `dndd` без хардкода путей;
  `requirements.txt` заменён pyproject.toml.

### Удалено

- Мёртвый код и шимы: `get_data_dir`, `load_api_keys`, дубль `load_prompt`,
  `STATIC_MODELS_FILE` и `data/static_models.txt`.

### Исправлено

- Двойной `❌` в сообщении об отсутствии ключей; сообщение указывает путь
  к `.env` и вариант с локальной Ollama.
- Никакой записи на диск при импорте модулей — каталоги создаёт точка входа.
