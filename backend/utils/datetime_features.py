from __future__ import annotations

from datetime import datetime


RUSH_HOUR_WINDOWS = {(7, 8, 9), (16, 17, 18, 19)}


def build_datetime_features(now: datetime | None = None) -> dict[str, int]:
    current = now or datetime.now()
    hour = current.hour
    day_of_week = current.weekday()

    is_rush_hour = int(
        any(hour in window for window in RUSH_HOUR_WINDOWS)
    )

    return {
        "hour_of_day": hour,
        "day_of_week": day_of_week,
        "month": current.month,
        "is_weekend": int(day_of_week >= 5),
        "is_rush_hour": is_rush_hour,
    }
