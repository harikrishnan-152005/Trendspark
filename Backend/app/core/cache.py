# app/core/cache.py

import time
import hashlib
import json
from typing import Any, Optional
from threading import Lock

CACHE = {}
CACHE_TTL = 60 * 30  # 30 minutes default
cache_lock = Lock()


def generate_cache_key(data: Any) -> str:
    """
    Generates unique hash key from input data
    """
    try:
        serialized = json.dumps(data, sort_keys=True)
    except TypeError:
        serialized = str(data)

    return hashlib.md5(serialized.encode()).hexdigest()


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