from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    tomtom_api_key: str = os.getenv("TOMTOM_API_KEY", "")
    calendarific_api_key: str = os.getenv("CALENDARIFIC_API_KEY", "")
    openmeteo_base_url: str = os.getenv(
        "OPENMETEO_BASE_URL", "https://api.open-meteo.com/v1/forecast"
    )
    model_path: str = os.getenv("MODEL_PATH", "artifacts/model.pkl")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "*").split(",")
            if origin.strip()
        ]
    )

    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
    request_retries: int = int(os.getenv("REQUEST_RETRIES", "2"))
    weather_cache_ttl_seconds: int = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "300"))
    traffic_cache_ttl_seconds: int = int(os.getenv("TRAFFIC_CACHE_TTL_SECONDS", "120"))
    holiday_cache_ttl_seconds: int = int(os.getenv("HOLIDAY_CACHE_TTL_SECONDS", "86400"))
    # Optional: how the training target was transformed. Supported: none, log1p, log
    target_transform: str = os.getenv("TARGET_TRANSFORM", "none")


def resolve_path(relative_or_absolute: str) -> Path:
    candidate = Path(relative_or_absolute)
    if candidate.is_absolute():
        return candidate
    return BASE_DIR / candidate


settings = Settings()
