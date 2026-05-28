from __future__ import annotations

from pathlib import Path
from typing import Any

import asyncio
import joblib
import httpx
import numpy as np

from backend.config import BASE_DIR, resolve_path, settings
from backend.services.encoders import encoders_loaded, init_encoders
from backend.services.feature_builder import (
    build_feature_dataframe,
    feature_builder_initialized,
    init_feature_builder,
)
from backend.utils.logger import logger


_model: Any | None = None


def _artifact_paths() -> dict[str, Path]:
    return {
        "model": Path(resolve_path(settings.model_path)),
        "borough_encoder": Path(BASE_DIR / "artifacts" / "borough_encoder.pkl"),
        "zone_name_encoder": Path(BASE_DIR / "artifacts" / "zone_name_encoder.pkl"),
        "feature_columns": Path(BASE_DIR / "artifacts" / "feature_columns.pkl"),
    }


def _looks_like_placeholder(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:128].decode("utf-8", errors="ignore").lower()
        return "placeholder" in sample
    except Exception:
        return False


def validate_artifacts() -> None:
    for name, path in _artifact_paths().items():
        if not path.exists():
            raise RuntimeError(f"Missing artifact: {name} at {path}")
        if path.stat().st_size == 0:
            raise RuntimeError(f"Empty artifact file: {name} at {path}")
        if _looks_like_placeholder(path):
            raise RuntimeError(
                f"Placeholder artifact detected: {name} at {path}. Replace with trained binary."
            )


def init_prediction_runtime() -> None:
    global _model

    if _model is not None:
        return

    validate_artifacts()
    init_encoders()
    init_feature_builder()

    model_path = Path(resolve_path(settings.model_path))
    _model = joblib.load(model_path)
    logger.info("Model loaded from %s", model_path)
    # Log details about the model/pipeline to help detect target transforms
    try:
        # sklearn Pipeline has named_steps
        steps = getattr(_model, "named_steps", None)
        if steps:
            logger.info("model_pipeline_steps %s", ",".join(steps.keys()))
    except Exception:
        pass


def runtime_readiness() -> dict[str, Any]:
    artifacts = _artifact_paths()
    return {
        "runtime_initialized": _model is not None,
        "model_loaded": _model is not None,
        "encoders_loaded": encoders_loaded(),
        "feature_builder_initialized": feature_builder_initialized(),
        "api_keys": {
            "tomtom": bool(settings.tomtom_api_key),
            "calendarific": bool(settings.calendarific_api_key),
        },
        "artifacts": {
            name: {
                "exists": path.exists(),
                "is_placeholder": path.exists() and _looks_like_placeholder(path),
            }
            for name, path in artifacts.items()
        },
    }


def confidence_label(surge_value: float) -> str:
    if surge_value < 1.2:
        return "low"
    if surge_value < 1.8:
        return "medium"
    return "high"


async def predict_surge(zone_name: str, client: httpx.AsyncClient) -> dict[str, Any]:
    if _model is None:
        raise RuntimeError("Prediction runtime not initialized")

    started = asyncio.get_running_loop().time()
    features_df, context = await build_feature_dataframe(zone_name, client)
    raw_pred = float(_model.predict(features_df)[0])
    # Apply inverse transform if the training target was transformed
    tt = settings.target_transform.lower().strip()
    if tt in ("log1p", "log_1p"):
        prediction = float(np.expm1(raw_pred))
    elif tt == "log":
        prediction = float(np.exp(raw_pred))
    else:
        prediction = raw_pred
    prediction_latency_ms = (asyncio.get_running_loop().time() - started) * 1000
    logger.info(
        "prediction_complete zone=%s surge=%.4f latency_ms=%.2f",
        zone_name,
        prediction,
        prediction_latency_ms,
    )

    result = {
        "zone_name": context["zone_name"],
        "borough": context["borough"],
        "surge_multiplier": round(prediction, 4),
        "confidence": confidence_label(prediction),
        "weather": {
            "temperature": round(float(context["weather"]["temperature"]), 2),
            "is_rainy": bool(context["weather"]["is_rainy"]),
        },
        "traffic": {
            "traffic_flow_ratio": round(
                float(context["traffic"]["traffic_flow_ratio"]), 4
            )
        },
        "timestamp": context["timestamp"],
    }
    return result


def predict_surge_sync(zone_name: str, client: httpx.AsyncClient) -> dict[str, Any]:
    return asyncio.run(predict_surge(zone_name, client))
