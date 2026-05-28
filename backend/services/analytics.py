from __future__ import annotations

import time
from collections import deque
from threading import Lock


_entries: deque[tuple[float, float]] = deque()
_lock = Lock()


def record_inference(latency_ms: float, when: float | None = None) -> None:
    ts = when if when is not None else time.time()
    with _lock:
        _entries.append((ts, float(latency_ms)))
        _prune_old_locked(ts)


def _prune_old_locked(now_ts: float) -> None:
    cutoff = now_ts - (24 * 3600)
    while _entries and _entries[0][0] < cutoff:
        _entries.popleft()


def get_kpis() -> dict[str, float | int]:
    now_ts = time.time()
    with _lock:
        _prune_old_locked(now_ts)
        latencies = [lat for _, lat in _entries]

    if not latencies:
        return {
            "inference_count_24h": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
        }

    ordered = sorted(latencies)
    idx = int(0.95 * (len(ordered) - 1))
    avg = sum(latencies) / len(latencies)
    p95 = ordered[idx]

    return {
        "inference_count_24h": len(latencies),
        "avg_latency_ms": round(avg, 2),
        "p95_latency_ms": round(p95, 2),
    }
