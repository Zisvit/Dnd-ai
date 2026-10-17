"""Атомарная запись файлов (безопасность против частичной записи при сбое)."""
import os
import tempfile
from pathlib import Path


def atomic_write(path, data: str, *, encoding="utf-8"):
    """Пишет текст в файл атомарно: сначала во временный, затем os.replace.

    os.replace атомарен на POSIX и Windows — либо старый файл цел, либо
    новый целиком записан. Исключает повреждение сессии при сбое посреди записи.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, errors="replace") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, str(path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
