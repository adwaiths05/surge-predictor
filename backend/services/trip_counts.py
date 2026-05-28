from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque

from cachetools import TTLCache

# Keep per-zone deque of timestamps (seconds) with a TTL to evict unused zones
_ZONE_CACHE_TTL = 60 * 60 * 24  # keep zone entries for 24 hours by default
_zone_store: TTLCache[str, Deque[float]] = TTLCache(maxsize=1024, ttl=_ZONE_CACHE_TTL)
_lock = Lock()


def record_trip(zone_name: str, when: float | None = None) -> None:
    """Record a trip event for a zone at given timestamp (seconds).

    This is a simple in-memory counter store suitable for low-volume testing
    or as a placeholder for a real event/aggregation source.
    """
    ts = when if when is not None else time.time()
    with _lock:
        dq = _zone_store.get(zone_name)
        if dq is None:
            dq = deque()
            _zone_store[zone_name] = dq
        dq.append(ts)


def get_recent_counts(zone_name: str, hours: float) -> int:
    """Return number of recorded trips in the last `hours` hours for `zone_name`.

    This method prunes old timestamps on each call. It's intentionally simple
    and memory-bound by the fact that older timestamps are regularly removed.
    """
    cutoff = time.time() - (hours * 3600)
    with _lock:
        dq = _zone_store.get(zone_name)
        if not dq:
            return 0
        # prune from left
        while dq and dq[0] < cutoff:
            dq.popleft()
        return len(dq)
