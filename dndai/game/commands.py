#!/usr/bin/env python3
"""Глобальные предпочтения игрока и служебные экраны.

forced_model        — выбор игрока: None (авто), 'red'/'yellow'/'blue'
                      (игровая категория) или точное имя модели.
forced_detail_level — уровень детализации 0..2.
PLAYER_NAME         — имя активного персонажа (для промпта ввода).

Фактическая модель последнего ответа живёт в api.openrouter
(get_current_model) — это факт рантайма, а не предпочтение.
"""
from dndai.core.colors import CYAN, GREEN, RESET, YELLOW
from dndai.core.i18n import t

forced_model = None
forced_detail_level = 1
PLAYER_NAME = "player"


def set_globals(forced_model_val, forced_detail_level_val, player_name_val):
    global forced_model, forced_detail_level, PLAYER_NAME
    forced_model = forced_model_val
    forced_detail_level = forced_detail_level_val
    PLAYER_NAME = player_name_val


MODE_LABEL_KEYS = {
    None: 'cmd.mode_auto',
    'red': 'cmd.mode_smart',
    'yellow': 'cmd.mode_medium',
    'blue': 'cmd.mode_fast',
}


def _mode_label():
    """Человекочитаемая метка текущего режима выбора модели."""
    if forced_model in MODE_LABEL_KEYS:
        return f"{GREEN}{t(MODE_LABEL_KEYS[forced_model])}{RESET}"
    if forced_model:
        return f"{GREEN}{t('cmd.mode_model')}: {CYAN}{forced_model}{RESET}"
    return f"{GREEN}{t('cmd.mode_auto')}{RESET}"


def _first_candidate():
    """(кандидат "prov:model", число заблокированных) для BALANCED tier."""
    from dndai.api.openrouter import _get_models_for_tier, is_blocked
    from dndai.core.config import PROVIDERS
    from dndai.core.task_types import TIER_PROVIDER_PREFERENCE, ModelTier

    blocked_n = 0
    for prov_name in TIER_PROVIDER_PREFERENCE.get(ModelTier.BALANCED, []):
        provider = next((p for p in PROVIDERS if p["name"] == prov_name), None)
        if not provider or not (provider.get("api_key")
                                or prov_name in ("Ollama", "Ollama-Server")):
            continue
        for m in _get_models_for_tier(prov_name, ModelTier.BALANCED):
            if is_blocked(prov_name, m):
                blocked_n += 1
                continue
            return f"{prov_name}:{m}", blocked_n
    return None, blocked_n


def show_dm_status():
    from dndai.api.openrouter import get_current_model

    det = f"{YELLOW}{'★' * forced_detail_level}{RESET}" if forced_detail_level > 0 \
        else t('cmd.detail_custom')

    current = get_current_model()
    if current:
        model_info = (f" [{GREEN}{t('cmd.model_responding')}: "
                      f"{CYAN}{current}{RESET}{GREEN}]{RESET}")
    else:
        candidate, blocked_n = _first_candidate()
        extra = f" ({t('cmd.models_blocked', n=blocked_n)})" if blocked_n else ""
        model_info = (f" [{YELLOW}{t('cmd.model_first_try')}: {candidate}"
                      f"{extra}{RESET}{YELLOW}]" if candidate else "")

    print(f"{GREEN}{t('cmd.mode_label')}{RESET} {t('cmd.model_label')} "
          f"{_mode_label()}{model_info}, {t('cmd.detail_label')} {det}")


def clear_history_and_exit(session_name):
    """Очищает только историю и память сюжета, сохраняя партию,
    мир и RPG-прогресс (state/world/rpg остаются нетронутыми)."""
    from .session import load_session, save_session
    print(f"{YELLOW}{t('cmd.history_cleared')}{RESET}")
    data = load_session(session_name)  # сохраняем всё кроме history/memory
    data["history"] = []
    data["memory"] = ""
    save_session(session_name, data)
    print(f"{GREEN}{t('cmd.exiting')}{RESET}")
