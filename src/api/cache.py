#!/usr/bin/env python3
import json
from datetime import datetime, timedelta
from src.core.config import FAST_CACHE

def load_fast_cache():
    if FAST_CACHE.exists():
        try:
            data = json.loads(FAST_CACHE.read_text())
            ts = datetime.fromisoformat(data.get("timestamp", "2000-01-01"))
            if datetime.now() - ts < timedelta(hours=6):
                pings = data.get("fast_models", {})
                result = {}
                for color, models in pings.items():
                    if isinstance(models, list):
                        if len(models) > 0 and isinstance(models[0], list):
                            result[color] = [(float(p), m) for p, m in models]
                        else:
                            result[color] = [(None, m) for m in models]
                    else:
                        result[color] = []
                return result, ts.isoformat()
        except:
            pass
    return None, None

def save_fast_cache(pings):
    try:
        to_save = {}
        for color, lst in pings.items():
            to_save[color] = [[p, m] for p, m in lst]
        FAST_CACHE.write_text(json.dumps(
            {"timestamp": datetime.now().isoformat(), "fast_models": to_save}, indent=2))
    except:
        pass
