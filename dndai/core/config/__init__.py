from .settings import *
from .paths import *
from .prompts import *

# Определяем TERM_WIDTH здесь
import os

try:
    TERM_WIDTH = os.get_terminal_size().columns
    if TERM_WIDTH < 40:
        TERM_WIDTH = 40
except Exception:
    TERM_WIDTH = 80

__all__ = [
    "API_KEYS",
    "PROVIDERS",
    "OUTPUT_DELAY",
    "DEFAULT_PLAYER_NAME",
    "URL",
    "DATA_DIR",
    "SESSION_DIR",
    "BLACKLIST_PATH",
    "app_home",
    "ensure_home",
    "get_prompts_dir",
    "package_prompts_dir",
    "migrate_legacy_data",
    "REFUSE_PATTERNS",
    "DETAIL_LEVELS",
    "TERM_WIDTH",
]
