from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.config import settings
from backend.services.cache import get_cached_value, set_cached_value, _weather_cache
from backend.utils.logger import logger


_DEFAULT_WEATHER = {
    "temperature": 20.0,
    "precipitation_mm": 0.0,
    "wind_speed": 5.0,
    "is_rainy": 0,
}


async def fetch_weather(
    lat: float,
    lon: float,
    client: httpx.AsyncClient,
) -> dict[str, float | int]:
    cache_key = f"{lat}:{lon}"
    cached = get_cached_value(_weather_cache, cache_key)
    if cached is not None:
        logger.info("weather_cache_hit lat=%s lon=%s", lat, lon)
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,windspeed_10m",
    }

    last_error: Exception | None = None
    started = asyncio.get_running_loop().time()

    try:
        for attempt in range(settings.request_retries + 1):
            try:
                response = await client.get(settings.openmeteo_base_url, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                current = payload.get("current", {})

                precipitation = float(current.get("precipitation", 0.0) or 0.0)
                weather = {
                    "temperature": float(current.get("temperature_2m", _DEFAULT_WEATHER["temperature"])),
                    "precipitation_mm": precipitation,
                    "wind_speed": float(current.get("windspeed_10m", _DEFAULT_WEATHER["wind_speed"])),
                    "is_rainy": int(precipitation > 0),
                }
                set_cached_value(_weather_cache, cache_key, weather)
                logger.info(
                    "api_call service=openmeteo status=success latency_ms=%.2f lat=%s lon=%s",
                    (asyncio.get_running_loop().time() - started) * 1000,
                    lat,
                    lon,
                )
                return weather
            except Exception as exc:
                last_error = exc
                if attempt >= settings.request_retries:
                    raise
                await asyncio.sleep(0.2 * (2**attempt))
    except Exception as exc:
        logger.warning("Open-Meteo fallback triggered: %s", last_error or exc)
        return dict(_DEFAULT_WEATHER)
