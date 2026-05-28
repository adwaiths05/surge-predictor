from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class AppState:
    http_client: httpx.AsyncClient | None = None
