from __future__ import annotations

import httpx

from backend.config import settings


async def create_http_client() -> httpx.AsyncClient:
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    return httpx.AsyncClient(timeout=timeout, headers={"User-Agent": "ride-hail-surge-backend/1.0"})
