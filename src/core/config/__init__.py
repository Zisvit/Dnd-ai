from .settings import *
from .paths import *
from .models import *
from .prompts import *

# Определяем TERM_WIDTH здесь
import os
try:
    TERM_WIDTH = os.get_terminal_size().columns
    if TERM_WIDTH < 40:
        TERM_WIDTH = 40
except:
    TERM_WIDTH = 80

__all__ = [
    'API_KEYS', 'OUTPUT_DELAY', 'DEFAULT_PLAYER_NAME', 'URL',
    'BASE_DIR', 'PROMPTS_DIR', 'DATA_DIR', 'SESSION_DIR',
    'MODELS_CACHE', 'FAST_CACHE', 'BLACKLIST_PATH',
    'MODELS_RANKING_FILE', 'STATIC_MODELS_FILE',
    'FALLBACK_MODELS',
    'REFUSE_PATTERNS', 'DETAIL_LEVELS',
    'TERM_WIDTH'
]
