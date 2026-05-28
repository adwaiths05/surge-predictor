from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import app


def _client(monkeypatch):
    monkeypatch.setattr("backend.app.init_prediction_runtime", lambda: None)
    return TestClient(app)


def test_health(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_zones(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/zones")
        assert response.status_code == 200
        assert "Alphabet City" in response.json()


def test_predict_success(monkeypatch) -> None:
    async def fake_predict(zone_name: str, client) -> dict:
        return {
            "zone_name": zone_name,
            "borough": "Manhattan",
            "surge_multiplier": 1.84,
            "confidence": "high",
            "weather": {"temperature": 31.2, "is_rainy": False},
            "traffic": {"traffic_flow_ratio": 0.42},
            "timestamp": "2025-05-26T18:00:00",
        }

    monkeypatch.setattr("backend.app.predict_surge", fake_predict)

    with _client(monkeypatch) as client:
        response = client.post("/predict", json={"zone_name": "Alphabet City"})
        assert response.status_code == 200
        body = response.json()
        assert body["zone_name"] == "Alphabet City"
        assert body["confidence"] == "high"


def test_predict_unknown_zone(monkeypatch) -> None:
    async def fake_predict(_: str, client) -> dict:
        raise ValueError("Unknown zone_name: Invalid Zone")

    monkeypatch.setattr("backend.app.predict_surge", fake_predict)
    with _client(monkeypatch) as client:
        response = client.post("/predict", json={"zone_name": "Invalid Zone"})
        assert response.status_code == 404


def test_ready_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.runtime_readiness",
        lambda: {
            "runtime_initialized": False,
            "model_loaded": False,
            "encoders_loaded": False,
            "feature_builder_initialized": False,
            "api_keys": {"tomtom": False, "calendarific": False},
            "artifacts": {
                "model": {"exists": False, "is_placeholder": False},
            },
        },
    )
    with _client(monkeypatch) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"


def test_ready_ok(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.runtime_readiness",
        lambda: {
            "runtime_initialized": True,
            "model_loaded": True,
            "encoders_loaded": True,
            "feature_builder_initialized": True,
            "api_keys": {"tomtom": True, "calendarific": True},
            "artifacts": {
                "model": {"exists": True, "is_placeholder": False},
            },
        },
    )
    with _client(monkeypatch) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


def test_api_health(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.app.runtime_readiness",
        lambda: {
            "runtime_initialized": True,
            "model_loaded": True,
            "encoders_loaded": True,
            "feature_builder_initialized": True,
            "api_keys": {"tomtom": True, "calendarific": True},
            "artifacts": {"model": {"exists": True, "is_placeholder": False}},
        },
    )
    with _client(monkeypatch) as client:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["service"] == "surge-backend"
        assert body["ready"] is True


def test_map_heatmap(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/map/heatmap")
        assert response.status_code == 200
        body = response.json()
        assert "points" in body
        assert len(body["points"]) > 0


def test_history(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/history", params={"zone": "Alphabet City", "days": 7})
        assert response.status_code == 200
        body = response.json()
        assert body["zone_name"] == "Alphabet City"
        assert len(body["series"]) == 7


def test_model_metadata(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/model/metadata")
        assert response.status_code == 200
        assert "model_version" in response.json()


def test_model_features(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/model/features")
        assert response.status_code == 200
        body = response.json()
        assert len(body["top_features"]) == 10


def test_drift_summary(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/drift/summary")
        assert response.status_code == 200
        assert response.json()["status"] == "stable"


def test_analytics_kpis(monkeypatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/analytics/kpis")
        assert response.status_code == 200
        body = response.json()
        assert "inference_count_24h" in body
        assert "avg_latency_ms" in body
        assert "p95_latency_ms" in body
