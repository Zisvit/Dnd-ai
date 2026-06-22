#!/usr/bin/env python3
import json
import time
import threading
import re
from datetime import datetime, timedelta
from src.core.config import API_KEYS, URL, BLACKLIST_PATH, FALLBACK_MODELS
from src.core.config.prompts import REFUSE_PATTERNS, DETAIL_LEVELS
from src.core.text import clean
from src.core.models import get_best_model, get_top_models
from .client import get_session
from .cache import load_fast_cache, save_fast_cache
from .prompts import SYSTEM_PROMPT_TEMPLATE, FIRST_MESSAGE_PROMPT, JAILBREAK_PROMPT, COMPRESS_PROMPT

fast_lock = threading.Lock()
FAST_MODELS = FALLBACK_MODELS.copy()
FAST_PINGS = {}
BLACKLIST = {}

http_session = get_session()

def load_blacklist():
    global BLACKLIST
    if BLACKLIST_PATH.exists():
        try:
            data = json.loads(BLACKLIST_PATH.read_text())
            BLACKLIST = {k: datetime.fromisoformat(v) for k, v in data.items() 
                        if datetime.fromisoformat(v) > datetime.now()}
        except:
            pass

def save_blacklist():
    data = {k: v.isoformat() for k, v in BLACKLIST.items() if v > datetime.now()}
    BLACKLIST_PATH.write_text(json.dumps(data, indent=2))

def block_model(model_id, minutes=180):
    with fast_lock:
        BLACKLIST[model_id] = datetime.now() + timedelta(minutes=minutes)
        save_blacklist()

def init_models():
    if not API_KEYS:
        print("\033[91m❌ Нет API ключей! Бот не может работать.\033[0m")
        return
    load_blacklist()
    from src.core.models import init_models_manager
    init_models_manager()

def expected_model(forced_model=None):
    if forced_model:
        return get_best_model(forced_model)
    return get_best_model("yellow")

def api_request(key, model, messages, max_tok=1500, timeout=30):
    for attempt in range(3):
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "max_tokens": max_tok,
                "temperature": 0.85,
                "top_p": 0.95
            }
            json_str = json.dumps(payload, ensure_ascii=False)
            r = http_session.post(URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json; charset=utf-8"
                },
                data=json_str.encode('utf-8'),
                timeout=timeout)
            if r.status_code == 200:
                r.encoding = 'utf-8'
                data = r.json()
                text = data["choices"][0]["message"]["content"].strip()
                low = text.lower()
                if any(re.search(p, low) for p in REFUSE_PATTERNS):
                    block_model(model)
                    return None
                return text
            elif r.status_code == 401:
                return None
            elif r.status_code == 429:
                time.sleep(2)
            else:
                time.sleep(1)
        except:
            time.sleep(1)
    return None

def ask_dm(history, memory, last_user="", forced_model=None, forced_detail_level=0):
    if not API_KEYS:
        return None, None

    quality = ['качественнее','подробнее','развёрнуто','детально','опиши','распиши']
    wants_detail = any(w in last_user.lower() for w in quality)
    effective_detail = forced_detail_level
    if wants_detail and effective_detail == 0:
        effective_detail = 1

    first_message = (len(history) == 1 and history[0]["role"] == "user" 
                    and "Начинай игру" in history[0]["content"])

    if first_message:
        max_tok = 600
        sys_prompt = FIRST_MESSAGE_PROMPT
    else:
        if effective_detail >= 2:
            max_tok = 2500
        elif effective_detail == 1:
            max_tok = 2000
        else:
            max_tok = 1500
        detail_desc = DETAIL_LEVELS.get(effective_detail, DETAIL_LEVELS[0])
        sys_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{detail}", detail_desc)

    msgs = [{"role": "system", "content": sys_prompt}]
    if memory:
        msgs.append({"role": "system", "content": memory})
    msgs.extend(history)

    if forced_model:
        categories = [forced_model]
    elif effective_detail >= 2:
        categories = ["red", "yellow", "blue"]
    elif effective_detail == 1:
        categories = ["yellow", "red", "blue"]
    else:
        categories = ["yellow", "red", "blue"]

    key = API_KEYS[0]

    for color in categories:
        models = get_top_models(color, 3)
        if not models:
            models = FALLBACK_MODELS.get(color, [])[:3]
        for model in models:
            if model in BLACKLIST:
                continue
            ans = api_request(key, model, msgs, max_tok)
            if ans:
                return ans, model
            block_model(model)

    jail_msgs = [{"role": "system", "content": JAILBREAK_PROMPT}]
    if memory:
        jail_msgs.append({"role": "system", "content": memory})
    jail_msgs.extend(history)
    
    for color in ["yellow", "red", "blue"]:
        for model in get_top_models(color, 3):
            if model in BLACKLIST:
                continue
            ans = api_request(key, model, jail_msgs, max_tok=400)
            if ans:
                return ans, model

    return None, None

def compress(full_history):
    if len(full_history) < 20:
        return full_history
    part = full_history[:20]
    text = "\n".join([f"{'Игрок' if m['role']=='user' else 'DM'}: {m['content'][:100]}" 
                     for m in part])
    for model in get_top_models("blue", 3):
        if model in BLACKLIST:
            continue
        ans = api_request(API_KEYS[0], model, [
            {"role": "system", "content": COMPRESS_PROMPT},
            {"role": "user", "content": text}
        ], max_tok=80)
        if ans:
            return [{"role": "system", "content": f"[Память: {ans}]"}] + full_history[20:]
    return full_history[20:]

def load_session(name):
    from src.core.config import SESSION_DIR
    f = SESSION_DIR / f"{name}.json"
    return json.loads(f.read_text()) if f.exists() else {"history": [], "memory": ""}

def save_session(name, data):
    from src.core.config import SESSION_DIR
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    (SESSION_DIR / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
