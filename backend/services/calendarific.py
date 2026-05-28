from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from backend.config import settings
from backend.services.cache import _holiday_cache, get_cached_value, set_cached_value
from backend.utils.logger import logger


_CALENDARIFIC_URL = "https://calendarific.com/api/v2/holidays"


async def is_us_holiday(
    now: datetime | None = None,
    client: httpx.AsyncClient | None = None,
) -> int:
    current = now or datetime.now()
    cache_key = current.date().isoformat()
    cached = get_cached_value(_holiday_cache, cache_key)
    if cached is not None:
        logger.info("holiday_cache_hit date=%s", cache_key)
        return cached

    if not settings.calendarific_api_key:
        logger.warning("CALENDARIFIC_API_KEY missing; defaulting is_holiday=0")
        return 0

    params = {
        "api_key": settings.calendarific_api_key,
        "country": "US",
        "year": current.year,
        "month": current.month,
        "day": current.day,
    }

    started = asyncio.get_running_loop().time()
    try:
        if client is None:
            raise RuntimeError("Calendarific client is unavailable")

        for attempt in range(settings.request_retries + 1):
            try:
                response = await client.get(_CALENDARIFIC_URL, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                holidays = payload.get("response", {}).get("holidays", [])
                holiday_flag = int(len(holidays) > 0)
                set_cached_value(_holiday_cache, cache_key, holiday_flag)
                logger.info(
                    "api_call service=calendarific status=success latency_ms=%.2f date=%s",
                    (asyncio.get_running_loop().time() - started) * 1000,
                    cache_key,
                )
                return holiday_flag
            except Exception:
                if attempt >= settings.request_retries:
                    raise
                await asyncio.sleep(0.2 * (2**attempt))
    except Exception as exc:
        logger.warning("Calendarific fallback triggered: %s", exc)
        return 0
