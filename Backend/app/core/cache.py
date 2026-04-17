# app/core/cache.py

import time
import hashlib
import json
from typing import Any, Optional
from threading import Lock

CACHE = {}
CACHE_TTL = 60 * 30  # 30 minutes default
cache_lock = Lock()


def normalize_input(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            str(key): normalize_input(value)
            for key, value in sorted(data.items(), key=lambda item: str(item[0]))
        }

    if isinstance(data, list):
        return [normalize_input(value) for value in data]

    if isinstance(data, tuple):
        return [normalize_input(value) for value in data]

    if isinstance(data, str):
        return data.strip().lower()

    return data


def generate_cache_key(data: Any) -> str:
    try:
        normalized = normalize_input(data)
        serialized = json.dumps(normalized, sort_keys=True, ensure_ascii=True)
    except Exception:
        serialized = str(data)

    return hashlib.md5(serialized.encode("utf-8")).hexdigest()


def get_cache(key: str) -> Optional[Any]:
    """
    Returns cached value if not expired
    """
    with cache_lock:
        entry = CACHE.get(key)

        if not entry:
            return None

        value, timestamp, ttl = entry

        if time.time() - timestamp > ttl:
            del CACHE[key]
            return None

        return value


def set_cache(key: str, value: Any, ttl: int = CACHE_TTL):
    """
    Stores value in cache
    """
    with cache_lock:
        CACHE[key] = (value, time.time(), ttl)


def clear_cache():
    """
    Clears entire cache
    """
    with cache_lock:
        CACHE.clear()
