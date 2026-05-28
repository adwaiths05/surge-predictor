from __future__ import annotations

import asyncio

import pandas as pd

from backend import predict


class DummyModel:
    def predict(self, _: pd.DataFrame):
        return [1.9]


class DummyClient:
    async def get(self, *args, **kwargs):
        raise AssertionError("network call should be mocked")


def test_confidence_label() -> None:
    assert predict.confidence_label(1.0) == "low"
    assert predict.confidence_label(1.4) == "medium"
    assert predict.confidence_label(2.0) == "high"


def test_predict_pipeline(monkeypatch) -> None:
    monkeypatch.setattr(predict, "_model", DummyModel())
    async def fake_build(zone_name, client):
        return (
            pd.DataFrame([{"f1": 1}]),
            {
                "zone_name": zone_name,
                "borough": "Manhattan",
                "timestamp": "2025-05-26T18:00:00",
                "weather": {"temperature": 30.0, "is_rainy": 0},
                "traffic": {"traffic_flow_ratio": 0.5},
            },
        )

    monkeypatch.setattr("backend.predict.build_feature_dataframe", fake_build)

    result = asyncio.run(predict.predict_surge("Alphabet City", DummyClient()))

    assert result["surge_multiplier"] == 1.9
    assert result["confidence"] == "high"
