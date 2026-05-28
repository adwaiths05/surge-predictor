from __future__ import annotations

from threading import Lock
from typing import Any

from cachetools import TTLCache

from backend.config import settings


_weather_cache: TTLCache[str, dict[str, Any]] = TTLCache(
    maxsize=256, ttl=settings.weather_cache_ttl_seconds
)
_traffic_cache: TTLCache[str, float] = TTLCache(
    maxsize=256, ttl=settings.traffic_cache_ttl_seconds
)
_holiday_cache: TTLCache[str, int] = TTLCache(
    maxsize=128, ttl=settings.holiday_cache_ttl_seconds
)
_cache_lock = Lock()


def get_cached_value(cache: TTLCache, key: str):
    with _cache_lock:
        return cache.get(key)


def set_cached_value(cache: TTLCache, key: str, value: Any) -> None:
    with _cache_lock:
        cache[key] = value
