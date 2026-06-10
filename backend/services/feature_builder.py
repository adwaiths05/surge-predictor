from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import joblib
import pandas as pd

from backend.config import BASE_DIR
from backend.metadata.zones import ZONE_DATA
from backend.services.calendarific import is_us_holiday
from backend.services.encoders import get_encoder_service
from backend.services.openmeteo import fetch_weather
from backend.services.tomtom import fetch_traffic_flow_ratio
from backend.services.trip_counts import get_recent_counts
from backend.services.weather_history import get_rain_last_hours, record_rain_event
from backend.utils.datetime_features import build_datetime_features
from backend.utils.preprocess import apply_feature_order


FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "month",
    "is_weekend",
    "is_rush_hour",
    "is_holiday",
    "zone_id",
    "borough",
    "zone_name",
    "temperature",
    "precipitation_mm",
    "wind_speed",
    "is_rainy",
    "heavy_rain",
    "rain_last_3hr",
    "extreme_temp",
    "traffic_flow_ratio",
    "demand_growth_rate",
    "rushhour_congestion",
    "rain_congestion",
    "temp_congestion",
]


_feature_columns: list[str] | None = None


def init_feature_builder() -> None:
    global _feature_columns
    if _feature_columns is not None:
        return

    path = Path(BASE_DIR / "artifacts" / "feature_columns.pkl")
    current = FEATURE_COLUMNS[:]
    try:
        loaded = joblib.load(path)
        if isinstance(loaded, list):
            loaded_cols = [str(column) for column in loaded]
            if loaded_cols != current:
                joblib.dump(current, path)
        else:
            joblib.dump(current, path)
    except Exception:
        joblib.dump(current, path)
    _feature_columns = current


def feature_builder_initialized() -> bool:
    return _feature_columns is not None


def get_zone_names() -> list[str]:
    return sorted(ZONE_DATA.keys())


async def build_feature_dataframe(
    zone_name: str,
    client: httpx.AsyncClient,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if _feature_columns is None:
        raise RuntimeError("Feature builder is not initialized")

    zone = ZONE_DATA.get(zone_name)
    if zone is None:
        raise ValueError(f"Unknown zone_name: {zone_name}")

    now = datetime.now()
    dt_features = build_datetime_features(now)

    weather, traffic_flow_ratio, holiday_flag = await asyncio.gather(
        fetch_weather(zone["lat"], zone["lon"], client),
        fetch_traffic_flow_ratio(zone["lat"], zone["lon"], client),
        is_us_holiday(now, client),
    )

    temperature = float(weather["temperature"])
    precipitation_mm = float(weather["precipitation_mm"])
    wind_speed = float(weather["wind_speed"])
    is_rainy = int(weather["is_rainy"])

    heavy_rain = int(precipitation_mm >= 5.0)
    # record the weather state so rain history can be measured over the last 3 hours
    record_rain_event(zone_name, bool(is_rainy))
    rain_last_3hr = int(get_rain_last_hours(zone_name, 3.0) > 0)
    extreme_temp = int(temperature <= 0.0 or temperature >= 35.0)

    encoder_service = get_encoder_service()
    borough_encoded = encoder_service.encode_borough(zone["borough"])
    zone_name_encoded = encoder_service.encode_zone_name(zone_name)

    trips_last_1hr = get_recent_counts(zone_name, 1.0)
    trips_last_24hr = get_recent_counts(zone_name, 24.0)
    baseline_hourly_demand = max(trips_last_24hr / 24.0, 1.0)
    demand_growth_rate = (trips_last_1hr / baseline_hourly_demand) - 1.0

    traffic_flow = float(traffic_flow_ratio)
    rushhour_congestion = traffic_flow * int(dt_features["is_rush_hour"])
    rain_congestion = traffic_flow * max(is_rainy, heavy_rain, rain_last_3hr)
    temp_congestion = traffic_flow * extreme_temp

    feature_map: dict[str, float | int] = {
        **dt_features,
        "is_holiday": int(holiday_flag),
        "zone_id": int(zone["location_id"]),
        "borough": int(borough_encoded),
        "zone_name": int(zone_name_encoded),
        "temperature": temperature,
        "precipitation_mm": precipitation_mm,
        "wind_speed": wind_speed,
        "is_rainy": is_rainy,
        "heavy_rain": heavy_rain,
        "rain_last_3hr": rain_last_3hr,
        "extreme_temp": extreme_temp,
        "traffic_flow_ratio": traffic_flow,
        "demand_growth_rate": float(demand_growth_rate),
        "rushhour_congestion": float(rushhour_congestion),
        "rain_congestion": float(rain_congestion),
        "temp_congestion": float(temp_congestion),
    }

    ordered_df = apply_feature_order(feature_map, _feature_columns)
    context = {
        "zone_name": zone_name,
        "borough": zone["borough"],
        "zone_id": int(zone["location_id"]),
        "timestamp": now.isoformat(),
        "weather": weather,
        "traffic": {"traffic_flow_ratio": traffic_flow},
        # Datetime features — included so JSONL log writer can populate all
        # 21 model feature columns without a second call to build_datetime_features.
        "hour_of_day": dt_features["hour_of_day"],
        "day_of_week": dt_features["day_of_week"],
        "month": dt_features["month"],
        "is_weekend": dt_features["is_weekend"],
        "is_rush_hour": dt_features["is_rush_hour"],
        "is_holiday": int(holiday_flag),
        # Encoded integer identifiers (output of LabelEncoder)
        "borough_encoded": int(borough_encoded),
        "zone_name_encoded": int(zone_name_encoded),
        "feature_signals": {
            "heavy_rain": heavy_rain,
            "rain_last_3hr": rain_last_3hr,
            "extreme_temp": extreme_temp,
            "demand_growth_rate": float(demand_growth_rate),
            "rushhour_congestion": float(rushhour_congestion),
            "rain_congestion": float(rain_congestion),
            "temp_congestion": float(temp_congestion),
        },
    }
    return ordered_df, context
