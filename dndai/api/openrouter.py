#!/usr/bin/env python3
"""Мульти-провайдерный API-клиент (OpenAI-совместимый формат).

Перебирает провайдеров из PROVIDERS при исчерпании лимитов (429),
ошибках сети и отказах моделей. Блокирует связку провайдер+модель
только при фатальных ошибках (401/403), а не при временных лимитах.

Маршрутизация по типам задач (TaskType -> ModelTier):
- SIMPLE -> быстрые модели
- NARRATIVE -> сбалансированные
- COMPLEX -> умные модели

Слой НЕ знает ничего об игре: статистика запросов подключается
подписчиками (add_request_listener), текущая модель отдаётся геттером.
"""

import json
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from dndai.core.config import PROVIDERS, BLACKLIST_PATH, get_ollama_models
from dndai.core.config.prompts import REFUSE_PATTERNS, DETAIL_LEVELS
from dndai.core.logger import debug as log_debug
from .client import get_session
from .prompts import SYSTEM_PROMPT_TEMPLATE, FIRST_MESSAGE_PROMPT, JAILBREAK_PROMPT
from dndai.core.i18n import t, variants as i18n_variants
from dndai.core.task_types import (
    TaskType,
    ModelTier,
    TASK_DEFAULT_TIER,
    TIER_PROVIDER_PREFERENCE,
    PROVIDER_MODELS_BY_TIER,
    TIER_FOR_COLOR,
)

fast_lock = threading.Lock()
BLACKLIST = {}  # ключ: "Provider:model" -> datetime до которого заблокировано

http_session = get_session()

# Лимиты ответа: больше детализация — больше лимит (а не наоборот).
MAX_TOKENS_BY_DETAIL = {0: 2048, 1: 3200, 2: 4096}
FIRST_MESSAGE_MAX_TOKENS = 2500
JAILBREAK_MAX_TOKENS = 1500

# Паузы между попытками одного провайдера при 429/5xx/сети.
RETRY_DELAYS = (1.5, 4.0)

# ── Подписчики на результаты запросов (статистика и т.п.) ────────────────
_request_listeners = []


def add_request_listener(fn):
    """fn(provider_name, tokens, ok) — вызывается после каждого запроса."""
    if fn not in _request_listeners:
        _request_listeners.append(fn)


def _notify(kind_provider, tokens, ok):
    for fn in _request_listeners:
        try:
            fn(kind_provider, tokens, ok)
        except Exception:
            pass


# ── Текущая модель (факт последнего успешного ответа) ────────────────────
_current_model: Optional[str] = None  # "Provider:model"


def set_current_model(value: Optional[str]):
    global _current_model
    _current_model = value


def get_current_model() -> Optional[str]:
    return _current_model


def load_blacklist():
    global BLACKLIST
    with fast_lock:
        if BLACKLIST_PATH.exists():
            try:
                data = json.loads(BLACKLIST_PATH.read_text())
                BLACKLIST = {
                    k: datetime.fromisoformat(v)
                    for k, v in data.items()
                    if datetime.fromisoformat(v) > datetime.now()
                }
            except Exception:
                pass


def save_blacklist():
    from dndai.core.atomic import atomic_write

    data = {k: v.isoformat() for k, v in BLACKLIST.items() if v > datetime.now()}
    atomic_write(BLACKLIST_PATH, json.dumps(data, indent=2))


def block_model(provider_name, model, minutes=180):
    with fast_lock:
        BLACKLIST[f"{provider_name}:{model}"] = datetime.now() + timedelta(
            minutes=minutes
        )
        save_blacklist()


def is_blocked(provider_name, model):
    return (
        f"{provider_name}:{model}" in BLACKLIST
        and BLACKLIST[f"{provider_name}:{model}"] > datetime.now()
    )


def init_models():
    """Инициализация на старте: чёрный список. Без сети и потоков."""
    if not PROVIDERS:
        print("\033[91m❌ Нет API ключей! Бот не может работать.\033[0m")
        return
    load_blacklist()


def translate_api_error(status, body="", headers=None):
    """Переводит типичные ошибки API на текущий язык."""
    body_low = (body or "").lower()

    if status == 401:
        return t("api.error_401")
    if status == 403:
        return t("api.error_403")
    if status == 404:
        return t("api.error_404")
    if status == 400:
        if "max_tokens" in body_low or "token" in body_low:
            return t("api.error_400_tokens")
        return t("api.error_400")
    if status == 429:
        # Время сброса лимита берём из заголовков (основной путь),
        # из тела — запасной вариант.
        reset_raw = None
        if headers:
            reset_raw = headers.get("X-RateLimit-Reset") or headers.get(
                "x-ratelimit-reset"
            )
        if not reset_raw:
            m = re.search(
                r'"X-RateLimit-Reset"\s*:\s*"?(\d+)', body or "", re.IGNORECASE
            )
            reset_raw = m.group(1) if m else None
        if reset_raw:
            try:
                ts = float(reset_raw)
                if ts > 10**12:  # миллисекунды
                    ts /= 1000.0
                reset_dt = datetime.fromtimestamp(ts)
                return t("api.error_429_reset", time=reset_dt.strftime("%d.%m %H:%M"))
            except Exception:
                pass
        if "free-models-per-day" in body_low or "rate limit" in body_low:
            return t("api.error_429")
        if "credits" in body_low:
            return t("api.error_credits")
        return t("api.error_rate")
    if status == 408:
        return t("api.error_timeout")
    if status >= 500:
        return t("api.error_server", status=status)
    if status == 0:
        return t("api.error_network")
    return t("api.error_unknown", status=status)


def _classify(status):
    """Категория ошибки для итогового резюме ask_dm."""
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "limits"
    if status == 0:
        return "network"
    if status >= 500 or status == 408:
        return "server"
    return "other"


def _is_refusal(text):
    low = (text or "").lower()
    return any(re.search(p, low) for p in REFUSE_PATTERNS)


def api_request(
    provider, model, messages, max_tok=1500, timeout=120, stream=False, on_token=None
):
    """Выполняет запрос к одному провайдеру.

    Возвращает (text, error, kind): kind ∈ {None,"auth","limits","server",
    "network","refusal","empty","other"} — категория ошибки для резюме.
    Если stream=True — печатает ответ по токенам через on_token(chunk).
    """
    from dndai.core.colors import YELLOW, RED, RESET

    if not provider or (
        not provider.get("api_key")
        and provider["name"] not in ("Ollama", "Ollama-Server")
    ):
        return None, t("api.no_provider_key"), "other"

    is_ollama = provider["name"] in ("Ollama", "Ollama-Server")
    use_stream = stream and provider.get("stream", True) and not is_ollama
    if is_ollama:
        max_tok = min(max_tok, 200)
        timeout = 300
    last_err = None
    last_kind = "other"

    for attempt, retry_delay in enumerate(RETRY_DELAYS + (None,)):
        try:
            log_debug(
                "[%s] %s: попытка %d, max_tok=%d, stream=%s",
                provider["name"],
                model,
                attempt + 1,
                max_tok,
                use_stream,
            )
            if is_ollama:
                print(
                    f"{YELLOW}⏳ [{provider['name']}] {model}: генерация...{RESET}",
                    flush=True,
                )
            payload = {
                "model": model,
                "messages": messages,
                "stream": use_stream,
                "max_tokens": max_tok,
                "temperature": 0.85,
                "top_p": 0.95,
            }
            headers = {"Content-Type": "application/json; charset=utf-8"}
            if provider.get("api_key"):
                headers["Authorization"] = f"Bearer {provider['api_key']}"

            if use_stream:
                result = _do_streaming_request(
                    provider, model, payload, headers, timeout, on_token
                )
                text, err, kind = result
                if text is not None:
                    return text, None, None
                if kind in ("auth",):
                    # фатально — блокируем и не ретраим
                    err = err or translate_api_error(401)
                    print(f"\n{RED}⚠️ [{provider['name']}] {err}{RESET}")
                    block_model(provider["name"], model, minutes=180)
                    _notify(provider["name"], 0, False)
                    return None, err, kind
                last_err, last_kind = err, kind or "network"
                _notify(provider["name"], 0, False)
                # 429/обрывы — ретраятся; прочее возвращаем сразу
                if kind in ("empty", "refusal"):
                    return None, last_err, kind
            else:
                with http_session.post(
                    provider["base_url"], headers=headers, json=payload, timeout=timeout
                ) as r:
                    if r.status_code == 200:
                        r.encoding = "utf-8"
                        data = r.json()
                        choices = data.get("choices", [])
                        msg = choices[0].get("message", {}) if choices else {}
                        text = (
                            (msg.get("content") or "") if isinstance(msg, dict) else ""
                        ).strip()
                        if not text:
                            _notify(provider["name"], 0, False)
                            return None, t("api.error_unknown", status=200), "empty"
                        if _is_refusal(text):
                            _notify(provider["name"], 0, False)
                            return None, t("api.refusal"), "refusal"
                        _notify(provider["name"], len(text) // 4, True)
                        return text, None, None
                    body = r.text
                    status = r.status_code
                    err = translate_api_error(status, body, headers=r.headers)
                    kind = _classify(status)
                    if kind == "auth":
                        print(f"\n{RED}⚠️ [{provider['name']}] {err}{RESET}")
                        block_model(provider["name"], model, minutes=180)
                        _notify(provider["name"], 0, False)
                        return None, err, kind
                    if kind in ("limits", "server", "network"):
                        last_err, last_kind = err, kind
                        _notify(provider["name"], 0, False)
                        # 429/5xx — имеет смысл повторить
                    else:
                        # 400/404 и прочие невосстановимые — сразу к следующему
                        _notify(provider["name"], 0, False)
                        return None, err, kind
        except Exception as e:
            last_err = f"❌ Ошибка сети: {translate_api_error(0)}\n   ({e})"
            last_kind = "network"
            try:
                from dndai.core.logger import error as _log_err

                _log_err(f"api_request {provider['name']}: {e}")
            except Exception:
                pass
            _notify(provider["name"], 0, False)

        if retry_delay:
            time.sleep(retry_delay)

    return None, last_err or "❌ Не удалось получить ответ.", last_kind


def _do_streaming_request(provider, model, payload, headers, timeout, on_token):
    """Стриминговый запрос. Возвращает (text, err, kind).

    - Соединение закрывается детерминированно (context manager).
    - Отказ модели детектируется и в стриме.
    - Битый чанк не теряет набранный текст: длинный ответ уходит
      игроку с пометкой об обрыве.
    """
    r = http_session.post(
        provider["base_url"],
        headers=headers,
        json=payload,
        timeout=timeout,
        stream=True,
    )
    try:
        if r.status_code != 200:
            body = r.text
            status = r.status_code
            err = translate_api_error(status, body, headers=r.headers)
            return None, err, _classify(status)

        full = []
        broken = False
        # iter_lines без decode_unicode + ручное декодирование (fix для Groq)
        for line_bytes in r.iter_lines(decode_unicode=False):
            if not line_bytes:
                continue
            try:
                line = line_bytes.decode("utf-8")
            except UnicodeDecodeError:
                line = line_bytes.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                obj = json.loads(chunk)
                choices = obj.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content", "") if isinstance(delta, dict) else ""
                if content:
                    full.append(content)
                    if on_token:
                        on_token(content)
            except Exception:
                # битый чанк — завершаем, но не теряем набранное
                broken = True
                break

        text = "".join(full).strip()
        if text:
            if _is_refusal(text):
                _notify(provider["name"], 0, False)
                return None, t("api.refusal"), "refusal"
            _notify(provider["name"], len(text) // 4, True)
            if broken:
                # ответ оборван посреди генерации — честно предупреждаем
                text += "\n\n" + t("api.stream_truncated")
            return text, None, None
        _notify(provider["name"], 0, False)
        return (
            None,
            t("api.empty_response") if not broken else t("api.stream_broken"),
            "empty" if not broken else "network",
        )
    finally:
        r.close()


def _get_models_for_tier(provider_name: str, tier: ModelTier) -> list:
    """Возвращает список моделей провайдера для заданного tier."""
    # Для Ollama-Server используем динамические модели из API (лениво)
    if provider_name == "Ollama-Server":
        ollama_models = get_ollama_models()
        if ollama_models:

            def matches_tier(model_name: str, tier_patterns: list) -> bool:
                """Паттерн размера в конце имени или перед разделителем."""
                model_lower = model_name.lower()
                for pattern in tier_patterns:
                    pat = rf"(^|[^0-9a-z]){re.escape(pattern)}(?=$|[:_\-\.])"
                    if re.search(pat, model_lower):
                        return True
                return False

            if tier == ModelTier.FAST:
                fast_patterns = ["3b", "2b", "1b", "mini", "small", "tiny", "7b"]
                return [m for m in ollama_models if matches_tier(m, fast_patterns)]
            elif tier == ModelTier.BALANCED:
                balanced_patterns = ["12b", "14b", "13b", "8b"]
                return [m for m in ollama_models if matches_tier(m, balanced_patterns)]
            else:  # SMART
                smart_patterns = [
                    "27b",
                    "30b",
                    "70b",
                    "72b",
                    "120b",
                    "dnd",
                    "brainstorm",
                ]
                return [m for m in ollama_models if matches_tier(m, smart_patterns)]

    return PROVIDER_MODELS_BY_TIER.get(provider_name, {}).get(tier, [])


def _get_fallback_models(provider_name: str, tier: ModelTier) -> list:
    """Возвращает фоллбэк модели для tier (нижние tier'ы)."""
    fallbacks = []
    if tier != ModelTier.FAST:
        fallbacks.extend(_get_models_for_tier(provider_name, ModelTier.FAST))
    if tier == ModelTier.SMART:
        fallbacks.extend(_get_models_for_tier(provider_name, ModelTier.BALANCED))
    return fallbacks


def _iter_providers_for_task(task_type: TaskType, forced_model: Optional[str] = None):
    """Генератор (провайдер, модель) в приоритетном порядке для типа задачи."""
    tier = TASK_DEFAULT_TIER.get(task_type, ModelTier.FAST)

    # Игровая категория («красный»/«жёлтый»/«синий») переопределяет tier
    if forced_model and forced_model.lower() in TIER_FOR_COLOR:
        tier = TIER_FOR_COLOR[forced_model.lower()]
        forced_model = None

    preferred_providers = TIER_PROVIDER_PREFERENCE.get(
        tier, ["Groq", "Gemini", "OpenRouter"]
    )

    # Если задана принудительная модель — ищем её провайдера
    if forced_model:
        for p in PROVIDERS:
            if forced_model in p["models"]:
                yield p, forced_model
                return

    def _provider_named(name):
        p = next((p for p in PROVIDERS if p["name"] == name), None)
        if not p:
            return None
        if not p.get("api_key") and name not in ("Ollama", "Ollama-Server"):
            return None
        return p

    # Основные модели для tier
    for provider_name in preferred_providers:
        provider = _provider_named(provider_name)
        if not provider:
            continue
        for model in _get_models_for_tier(provider_name, tier):
            if is_blocked(provider_name, model):
                continue
            yield provider, model

    # Фоллбэк: модели ниже tier'а
    for provider_name in preferred_providers:
        provider = _provider_named(provider_name)
        if not provider:
            continue
        for model in _get_fallback_models(provider_name, tier):
            if is_blocked(provider_name, model):
                continue
            yield provider, model

    # Остальные провайдеры (не в preferred)
    for provider in PROVIDERS:
        if provider["name"] in preferred_providers:
            continue
        if not provider.get("api_key") and provider["name"] not in (
            "Ollama",
            "Ollama-Server",
        ):
            continue
        for model in provider["models"]:
            if is_blocked(provider["name"], model):
                continue
            yield provider, model


def _looks_like_first_prompt(history):
    """Языконезависимый детект первой реплики игры."""
    if len(history) != 1 or history[0].get("role") != "user":
        return False
    content = history[0].get("content", "")
    return any(
        v and v in content for v in set(i18n_variants("main.first_prompt_tavern"))
    )


def ask_dm(
    history,
    memory,
    last_user="",
    forced_model=None,
    forced_detail_level=0,
    is_first=None,
    task_type: TaskType = TaskType.NARRATIVE,
    on_token=None,
):
    from dndai.core.config import STREAM_MODE

    if not PROVIDERS:
        return None, None, t("api.no_keys"), False

    errors = []  # (label, message, kind)

    quality = [
        "качественнее",
        "подробнее",
        "развёрнуто",
        "детально",
        "опиши",
        "распиши",
    ]
    wants_detail = any(w in last_user.lower() for w in quality)
    effective_detail = forced_detail_level
    if wants_detail and effective_detail == 0:
        effective_detail = 1

    if is_first is None:
        is_first = _looks_like_first_prompt(history)

    if is_first:
        max_tok = FIRST_MESSAGE_MAX_TOKENS
        sys_prompt = FIRST_MESSAGE_PROMPT
    else:
        max_tok = MAX_TOKENS_BY_DETAIL.get(
            max(0, min(2, int(effective_detail or 0))), MAX_TOKENS_BY_DETAIL[0]
        )
        detail_desc = DETAIL_LEVELS.get(effective_detail, DETAIL_LEVELS[0])
        sys_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{detail}", detail_desc)

    msgs = [{"role": "system", "content": sys_prompt}]
    if memory:
        msgs.append({"role": "system", "content": memory})
    msgs.extend(history)

    # Запасной промпт на случай отказов модели (без стриминга)
    jail_msgs = [{"role": "system", "content": JAILBREAK_PROMPT}]
    if memory:
        jail_msgs.append({"role": "system", "content": memory})
    jail_msgs.extend(history)

    def _try_all(messages_, max_tokens, stream, label=""):
        for provider, model in _iter_providers_for_task(task_type, forced_model):
            ans, err, _kind = api_request(
                provider, model, messages_, max_tokens, stream=stream, on_token=on_token
            )
            if ans:
                set_current_model(f"{provider['name']}:{model}")
                return ans, model
            if err:
                errors.append((f"{provider['name']}{label}", err, _kind))
        return None, None

    # Основной проход
    ans, model = _try_all(msgs, max_tok, STREAM_MODE)
    if ans:
        return ans, model, None, STREAM_MODE

    # Запасной вариант — альтернативный промпт по всем провайдерам
    ans, model = _try_all(
        jail_msgs, min(max_tok, JAILBREAK_MAX_TOKENS), stream=False, label=" (alt)"
    )
    if ans:
        return ans, model, None, False

    # Формируем итоговое сообщение по категориям ошибок (не по подстрокам)
    kinds = {k for _, _, k in errors}
    if "limits" in kinds:
        summary = t("api.all_failed_limits")
    elif "auth" in kinds:
        summary = t("api.all_failed_auth")
    elif "network" in kinds:
        summary = t("api.all_failed_network")
    elif "refusal" in kinds:
        summary = t("api.refusal")
    else:
        summary = t("api.all_failed")

    try:
        from dndai.core.logger import error as _log_err

        _log_err(
            "ask_dm: все провайдеры недоступны. Ошибки: "
            + (
                "; ".join(f"[{lbl}] {msg}" for lbl, msg, _ in errors)
                if errors
                else "нет ошибок (пустой ответ)"
            )
        )
    except Exception:
        pass

    return None, None, summary, False


def compress(full_history):
    """Краткий summary сюжета (строка) на основе истории.

    Используется для вечной памяти: summary подставляется в системный
    промпт, а старая история обрезается вызывающим кодом.
    Локальная эвристика с фоллбэком на API.
    """
    from dndai.scripts.compress import compress as compress_script

    return compress_script(full_history)
