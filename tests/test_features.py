from __future__ import annotations

import asyncio

from backend.services import feature_builder


class DummyEncoderService:
    def encode_borough(self, _: str) -> int:
        return 1

    def encode_zone_name(self, _: str) -> int:
        return 2


class DummyClient:
    async def get(self, *args, **kwargs):
        raise AssertionError("network call should be mocked")


async def fake_weather(lat, lon, client):
    return {
        "temperature": 25.0,
        "precipitation_mm": 0.0,
        "wind_speed": 7.0,
        "is_rainy": 0,
    }


async def fake_congestion(lat, lon, client):
    return 0.66


async def fake_holiday(now=None, client=None):
    return 1


def test_feature_builder_orders_columns(monkeypatch) -> None:
    monkeypatch.setattr(feature_builder, "_feature_columns", [
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
    ])

    monkeypatch.setattr("backend.services.feature_builder.fetch_weather", fake_weather)
    monkeypatch.setattr("backend.services.feature_builder.fetch_traffic_flow_ratio", fake_congestion)
    monkeypatch.setattr("backend.services.feature_builder.is_us_holiday", fake_holiday)
    monkeypatch.setattr(
        "backend.services.feature_builder.get_encoder_service",
        lambda: DummyEncoderService(),
    )

    df, context = asyncio.run(feature_builder.build_feature_dataframe("Alphabet City", DummyClient()))

    assert list(df.columns) == feature_builder._feature_columns
    assert df.iloc[0]["borough"] == 1
    assert context["zone_name"] == "Alphabet City"
    assert "zone_id" in df.columns
