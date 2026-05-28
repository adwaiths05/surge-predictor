from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

from backend.config import BASE_DIR
from backend.utils.logger import logger


class EncoderService:
    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = artifacts_dir or (BASE_DIR / "artifacts")
        self.borough_encoder: Any | None = None
        self.zone_name_encoder: Any | None = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        self.borough_encoder = joblib.load(self.artifacts_dir / "borough_encoder.pkl")
        self.zone_name_encoder = joblib.load(self.artifacts_dir / "zone_name_encoder.pkl")
        self._loaded = True
        logger.info("Encoders loaded successfully")

    @staticmethod
    def _safe_transform(encoder: Any, value: str) -> int:
        classes = list(getattr(encoder, "classes_", []))
        if not classes:
            return int(encoder.transform([value])[0])

        if value in classes:
            return int(encoder.transform([value])[0])

        fallback = "Unknown" if "Unknown" in classes else classes[0]
        logger.warning("Encoder value '%s' missing; fallback='%s'", value, fallback)
        return int(encoder.transform([fallback])[0])

    def encode_borough(self, borough: str) -> int:
        if self.borough_encoder is None:
            raise RuntimeError("borough encoder not loaded")
        return self._safe_transform(self.borough_encoder, borough)

    def encode_zone_name(self, zone_name: str) -> int:
        if self.zone_name_encoder is None:
            raise RuntimeError("zone name encoder not loaded")
        return self._safe_transform(self.zone_name_encoder, zone_name)


_encoder_service = EncoderService()


def get_encoder_service() -> EncoderService:
    return _encoder_service


def init_encoders() -> None:
    _encoder_service.load()


def encoders_loaded() -> bool:
    return _encoder_service._loaded
