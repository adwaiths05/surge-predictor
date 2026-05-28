from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"zone_name": "Alphabet City"}}
    )

    zone_name: str = Field(min_length=1)


class WeatherResponse(BaseModel):
    temperature: float
    is_rainy: bool


class TrafficResponse(BaseModel):
    traffic_flow_ratio: float


class PredictResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "zone_name": "Alphabet City",
                "borough": "Manhattan",
                "surge_multiplier": 1.84,
                "confidence": "high",
                "weather": {
                    "temperature": 31.2,
                    "is_rainy": False,
                },
                "traffic": {
                    "traffic_flow_ratio": 0.42,
                },
                "timestamp": "2025-05-26T18:00:00",
            }
        }
    )

    zone_name: str
    borough: str
    surge_multiplier: float
    confidence: str
    weather: WeatherResponse
    traffic: TrafficResponse
    timestamp: str


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    details: dict


class ApiHealthResponse(BaseModel):
    status: str
    service: str
    ready: bool


class HeatmapZonePoint(BaseModel):
    zone_name: str
    borough: str
    lat: float
    lon: float
    surge_multiplier: float


class HeatmapResponse(BaseModel):
    generated_at: str
    points: list[HeatmapZonePoint]


class HistoryPoint(BaseModel):
    date: str
    surge_multiplier: float


class HistoryResponse(BaseModel):
    zone_name: str
    days: int
    series: list[HistoryPoint]


class ModelMetadataResponse(BaseModel):
    model_version: str
    training_date: str
    metrics: dict[str, float]


class ModelFeatureItem(BaseModel):
    feature: str
    importance: float


class ModelFeaturesResponse(BaseModel):
    top_features: list[ModelFeatureItem]


class DriftSummaryResponse(BaseModel):
    drift_score: float
    status: str


class AnalyticsKpisResponse(BaseModel):
    inference_count_24h: int
    avg_latency_ms: float
    p95_latency_ms: float
