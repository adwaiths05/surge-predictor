from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque

from cachetools import TTLCache

_ZONE_CACHE_TTL = 60 * 60 * 24
_zone_store: TTLCache[str, Deque[float]] = TTLCache(maxsize=1024, ttl=_ZONE_CACHE_TTL)
_lock = Lock()


def record_rain_event(zone_name: str, is_rainy: bool, when: float | None = None) -> None:
    if not is_rainy:
        return
    ts = when if when is not None else time.time()
    with _lock:
        dq = _zone_store.get(zone_name)
        if dq is None:
            dq = deque()
            _zone_store[zone_name] = dq
        dq.append(ts)


def get_rain_last_hours(zone_name: str, hours: float) -> int:
    cutoff = time.time() - (hours * 3600)
    with _lock:
        dq = _zone_store.get(zone_name)
        if not dq:
            return 0
        while dq and dq[0] < cutoff:
            dq.popleft()
        return len(dq)
