#!/usr/bin/env python3
"""Изоляция тестов: дом данных (DND_AI_HOME) — во временном каталоге.

Переменные окружения выставляются ДО первого импорта dndai:
paths.py вычисляет DATA_DIR/SESSION_DIR на импорте модуля.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP_HOME = tempfile.mkdtemp(prefix="dndai-tests-")
os.environ["DND_AI_HOME"] = _TMP_HOME

from dndai.core.config import ensure_home  # noqa: E402

ensure_home()
# Маркер миграции: прогон тестов из репозитория не должен копировать
# data/ и dnd_sessions/ в тестовый дом (миграцию покрывает смоук при релизе).
(Path(_TMP_HOME) / ".migrations.json").write_text(
    '{"done": ["repo_data_v1"]}', encoding="utf-8"
)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TMP_HOME, ignore_errors=True)
