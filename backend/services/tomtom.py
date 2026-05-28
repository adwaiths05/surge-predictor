from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.config import settings
from backend.services.cache import _traffic_cache, get_cached_value, set_cached_value
from backend.utils.logger import logger


_DEFAULT_TRAFFIC_FLOW_RATIO = 0.75


def _clamp_ratio(value: float) -> float:
    # Keep the raw flow ratio in a sane range: 0.0 to 1.0.
    return max(0.0, min(1.0, value))


async def fetch_traffic_flow_ratio(
    lat: float,
    lon: float,
    client: httpx.AsyncClient,
) -> float:
    cache_key = f"{lat}:{lon}"
    cached = get_cached_value(_traffic_cache, cache_key)
    if cached is not None:
        logger.info("traffic_cache_hit lat=%s lon=%s", lat, lon)
        return cached

    if not settings.tomtom_api_key:
        logger.warning("TOMTOM_API_KEY missing; using fallback traffic flow ratio")
        return _DEFAULT_TRAFFIC_FLOW_RATIO

    base_url = (
        "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    )
    params = {
        "point": f"{lat},{lon}",
        "key": settings.tomtom_api_key,
    }

    started = asyncio.get_running_loop().time()
    try:
        for attempt in range(settings.request_retries + 1):
            try:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                segment = payload.get("flowSegmentData", {})
                current_speed = float(segment.get("currentSpeed", 0.0) or 0.0)
                free_flow_speed = float(segment.get("freeFlowSpeed", 0.0) or 0.0)

                if free_flow_speed <= 0:
                    return _DEFAULT_TRAFFIC_FLOW_RATIO

                # Direct flow ratio: higher means better flow / lower congestion.
                congestion = _clamp_ratio(current_speed / free_flow_speed)
                set_cached_value(_traffic_cache, cache_key, congestion)
                logger.info(
                    "api_call service=tomtom status=success latency_ms=%.2f lat=%s lon=%s",
                    (asyncio.get_running_loop().time() - started) * 1000,
                    lat,
                    lon,
                )
                return congestion
            except Exception as exc:
                if attempt >= settings.request_retries:
                    raise
                await asyncio.sleep(0.2 * (2**attempt))
    except Exception as exc:
        logger.warning("TomTom fallback triggered: %s", exc)
        return _DEFAULT_TRAFFIC_FLOW_RATIO
