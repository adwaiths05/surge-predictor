"""
training/metadata.py — Model metadata management for SurgeCast MLOps pipeline.

Responsibilities:
  - Load and save model_metadata.json (champion) and challenger_metadata.json
  - Seed the metadata file if it does not exist yet (first-run bootstrap)
  - Compare champion vs challenger RMSE to decide promotion
  - Enforce that pseudo_label_std always equals the latest promoted model's RMSE

Design notes:
  * We use RMSE (not MAE or R²) as the gating metric for champion-challenger
    comparison because RMSE penalises large errors more heavily, which matters
    in surge pricing where a large misfire is disproportionately harmful.
  * pseudo_label_std is kept in metadata so that the retraining cycle always
    reads the *currently promoted* model's RMSE as the noise standard deviation
    for pseudo-label generation.  This ensures the noise level is calibrated to
    the champion's observed error distribution, not an arbitrary constant.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths (relative to project root — callers may override)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHAMPION_METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"
CHALLENGER_METADATA_PATH = ARTIFACTS_DIR / "challenger_metadata.json"

# Known v1 champion metrics — used only to seed the file on first run.
_V1_METRICS: dict[str, Any] = {
    "model_name": "surgecast-model",
    "version": 1,
    "mae": 0.09128069329186603,
    "rmse": 0.13470562799274285,
    "r2": 0.6196057137759148,
    "pseudo_label_std": 0.13470562799274285,
    "timestamp": "2026-06-09T00:00:00",
    "drift_triggered": False,
    "status": "champion",
}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_metadata(path: Path | str = CHAMPION_METADATA_PATH) -> dict[str, Any]:
    """
    Load a metadata JSON file and return it as a dict.

    Raises FileNotFoundError if the path does not exist.
    Raises ValueError if the JSON is malformed or missing required keys.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {path}. "
            "Run `python -m training.metadata` to bootstrap it."
        )
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    _validate_metadata(data)
    return data


def save_metadata(data: dict[str, Any], path: Path | str = CHAMPION_METADATA_PATH) -> None:
    """Persist a metadata dict to JSON, creating parent directories if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    logger.info("Metadata saved → %s (version=%s, status=%s)", path, data.get("version"), data.get("status"))


def _validate_metadata(data: dict[str, Any]) -> None:
    """Raise ValueError if required keys are absent."""
    required = {"model_name", "version", "mae", "rmse", "r2", "pseudo_label_std", "status"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Metadata is missing required keys: {missing}")


# ---------------------------------------------------------------------------
# Bootstrapping
# ---------------------------------------------------------------------------

def create_initial_metadata(path: Path | str = CHAMPION_METADATA_PATH) -> dict[str, Any]:
    """
    Seed model_metadata.json with the known v1 champion metrics if the file
    does not already exist.  Safe to call multiple times — is a no-op when
    the file is present.

    Returns the metadata dict (loaded from disk or newly created).
    """
    path = Path(path)
    if path.exists():
        logger.info("Champion metadata already exists at %s — skipping bootstrap.", path)
        return load_metadata(path)

    data = dict(_V1_METRICS)
    save_metadata(data, path)
    logger.info("Bootstrapped champion metadata at %s (v%s).", path, data["version"])
    return data


# ---------------------------------------------------------------------------
# Challenger metadata creation
# ---------------------------------------------------------------------------

def create_challenger_metadata(
    mae: float,
    rmse: float,
    r2: float,
    drift_triggered: bool = True,
    path: Path | str = CHALLENGER_METADATA_PATH,
) -> dict[str, Any]:
    """
    Write challenger_metadata.json after a retraining run.

    The challenger version number is set to champion_version + 1 as a
    *candidate* version — it only becomes official upon promotion.
    pseudo_label_std is intentionally NOT set here; it belongs only to
    promoted champion metadata and is derived from the champion's RMSE.

    Args:
        mae:              Mean absolute error of the challenger on the test split.
        rmse:             Root mean squared error of the challenger.
        r2:               R² of the challenger.
        drift_triggered:  Whether this retraining was triggered by drift detection.
        path:             Where to write the challenger metadata JSON.

    Returns:
        The challenger metadata dict.
    """
    try:
        champion = load_metadata(CHAMPION_METADATA_PATH)
        candidate_version = champion["version"] + 1
    except FileNotFoundError:
        candidate_version = 2  # fallback if champion metadata missing

    data: dict[str, Any] = {
        "model_name": "surgecast-model",
        "version": candidate_version,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        # pseudo_label_std is NOT set for challengers — only promoted champions carry this.
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drift_triggered": drift_triggered,
        "status": "challenger",
    }
    save_metadata(data, path)
    logger.info(
        "Challenger metadata saved: MAE=%.6f  RMSE=%.6f  R²=%.6f",
        mae, rmse, r2,
    )
    return data


# ---------------------------------------------------------------------------
# Champion-challenger evaluation
# ---------------------------------------------------------------------------

def compare_champion_challenger(
    champion_meta: dict[str, Any],
    challenger_meta: dict[str, Any],
) -> tuple[str, str]:
    """
    Compare champion and challenger on RMSE.

    We use RMSE as the single gating metric because:
      - It penalises large prediction errors more than MAE does.
      - Surge pricing errors compound non-linearly in revenue impact.
      - Using a single metric avoids tie-breaking ambiguity.

    Returns:
        (winner, reason)  where winner is "challenger" or "champion".
    """
    champ_rmse = float(champion_meta["rmse"])
    chal_rmse = float(challenger_meta["rmse"])

    if chal_rmse < champ_rmse:
        reason = (
            f"Challenger RMSE {chal_rmse:.6f} < Champion RMSE {champ_rmse:.6f} "
            f"(improvement: {champ_rmse - chal_rmse:.6f})"
        )
        logger.info("✓ Challenger wins. %s", reason)
        return "challenger", reason
    else:
        reason = (
            f"Challenger RMSE {chal_rmse:.6f} >= Champion RMSE {champ_rmse:.6f} "
            f"(no improvement)"
        )
        logger.info("✗ Champion retained. %s", reason)
        return "champion", reason


# ---------------------------------------------------------------------------
# CLI entry-point — bootstrap metadata and print current state
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    data = create_initial_metadata()
    print("\n-- Champion Model Metadata --")
    print(json.dumps(data, indent=2, default=str))
    print("-" * 50 + "\n")


if __name__ == "__main__":
    main()
