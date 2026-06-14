"""
training/drift.py — Feature drift detection for SurgeCast MLOps pipeline.

WHY DRIFT DETECTION?
---------------------
In ride-hail surge prediction, real-world inputs (weather, congestion, demand)
shift seasonally and due to external events (new competitors, city policy,
infrastructure changes).  When the production feature distribution diverges
significantly from the training distribution, the model's predictions become
stale — a phenomenon known as *covariate shift*.

Since we do NOT have ground-truth labels in production (riders don't report
what the surge "should" have been), we cannot directly measure prediction
error online.  Drift detection on raw features is therefore our primary signal
for when retraining may be beneficial.

METHODS IMPLEMENTED:
---------------------
1. PSI (Population Stability Index)
   - Bins the training reference distribution into 10 equal-width buckets.
   - Computes the fraction of production samples in each bucket vs. training.
   - PSI = Σ (actual% - expected%) × ln(actual% / expected%)
   - Laplace smoothing (+1e-4) avoids log(0) when a bucket is empty.
   - Threshold: PSI >= 0.25 → significant drift (industry standard).
     PSI < 0.1   → stable
     0.1–0.25    → moderate / worth monitoring
     ≥ 0.25      → significant drift → trigger retraining

2. KS Test (Kolmogorov-Smirnov)
   - Two-sample KS test between training and production populations.
   - Reports statistic and p-value; uses p < 0.05 as a soft alert.
   - KS is a non-parametric complement to PSI that detects shape changes
     (e.g. bimodality) that PSI can miss.

OUTPUT:
-------
Appends one entry to artifacts/drift_history.json on every run.
Exits with code 1 if drift_detected == True (used by GitHub Actions `if`).
Exits with code 0 otherwise.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "logs" / "predictions.jsonl"
TRAINING_DATA_PATH = BASE_DIR / "data" / "surgecast_training.parquet"
DRIFT_HISTORY_PATH = BASE_DIR / "artifacts" / "drift_history.json"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PSI_THRESHOLD = 0.25
PSI_BINS = 10
MIN_LOGS_FOR_DRIFT = 1000  # minimum production records required for reliable drift detection

# Continuous features to monitor for drift.
# These are the features most likely to exhibit covariate shift in production
# due to seasonal or environmental changes.
CONTINUOUS_FEATURES = [
    "temperature",
    "precipitation_mm",
    "wind_speed",
    "congestion_ratio",   # spec column name; aliased from traffic_flow_ratio in backend
    "demand_growth_rate",
]

# Backend uses traffic_flow_ratio as its internal key.
# The training parquet may store this as congestion_ratio.
# We check both names and use whichever is present.
_FEATURE_ALIASES = {
    "congestion_ratio": "traffic_flow_ratio",
    "traffic_flow_ratio": "congestion_ratio",
}


# ---------------------------------------------------------------------------
# PSI computation
# ---------------------------------------------------------------------------

def _compute_psi(reference: np.ndarray, production: np.ndarray, bins: int = PSI_BINS) -> float:
    """
    Compute Population Stability Index between reference and production arrays.

    PSI measures how much the distribution of a feature has shifted.
    Formula: Σ (actual_pct - expected_pct) × ln(actual_pct / expected_pct)

    Laplace smoothing (1e-4) is applied to avoid log(0) when any bin is empty.
    """
    reference = reference[~np.isnan(reference)]
    production = production[~np.isnan(production)]

    if len(reference) == 0 or len(production) == 0:
        logger.warning("Empty array passed to PSI computation; returning 0.")
        return 0.0

    # Build bin edges from the reference distribution
    min_val = min(reference.min(), production.min())
    max_val = max(reference.max(), production.max())

    if min_val == max_val:
        # Constant feature — no drift possible
        return 0.0

    bin_edges = np.linspace(min_val, max_val, bins + 1)
    bin_edges[0] -= 1e-9   # include the minimum value
    bin_edges[-1] += 1e-9  # include the maximum value

    expected_counts, _ = np.histogram(reference, bins=bin_edges)
    actual_counts, _ = np.histogram(production, bins=bin_edges)

    # Convert to fractions with Laplace smoothing
    smoothing = 1e-4
    expected_pct = (expected_counts + smoothing) / (expected_counts.sum() + smoothing * bins)
    actual_pct = (actual_counts + smoothing) / (actual_counts.sum() + smoothing * bins)

    psi = float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))
    return psi


# ---------------------------------------------------------------------------
# KS Test wrapper
# ---------------------------------------------------------------------------

def _compute_ks(reference: np.ndarray, production: np.ndarray) -> dict[str, float]:
    """
    Two-sample Kolmogorov-Smirnov test.

    Returns statistic and p-value.  A p-value < 0.05 indicates the samples
    are unlikely to come from the same distribution.
    """
    reference = reference[~np.isnan(reference)]
    production = production[~np.isnan(production)]

    if len(reference) < 2 or len(production) < 2:
        return {"statistic": 0.0, "p_value": 1.0}

    result = stats.ks_2samp(reference, production)
    return {"statistic": float(result.statistic), "p_value": float(result.pvalue)}


# ---------------------------------------------------------------------------
# Log loading
# ---------------------------------------------------------------------------

def _load_production_logs(path: Path = LOG_PATH) -> list[dict[str, Any]]:
    """
    Load production inference logs from logs/predictions.jsonl.

    Each line is a JSON object:
      { "features": {...}, "prediction": float, "timestamp": "..." }

    Returns an empty list (with a warning) if the file does not exist.
    """
    if not path.exists():
        logger.warning(
            "Production log not found at %s. "
            "No drift can be computed without production data. "
            "Ensure the backend is writing JSONL logs.",
            path,
        )
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping malformed JSONL line %d: %s", lineno, exc)

    logger.info("Loaded %d production records from %s.", len(records), path)
    return records


def _extract_feature_series(records: list[dict[str, Any]], feature: str) -> np.ndarray:
    """
    Extract a numeric series for `feature` from production log records.

    Handles the congestion_ratio / traffic_flow_ratio alias transparently.
    """
    alias = _FEATURE_ALIASES.get(feature)
    values: list[float] = []
    for rec in records:
        feats = rec.get("features", {})
        val = feats.get(feature)
        if val is None and alias:
            val = feats.get(alias)
        if val is not None:
            try:
                values.append(float(val))
            except (TypeError, ValueError):
                pass
    return np.array(values, dtype=np.float64)


# ---------------------------------------------------------------------------
# Drift history I/O
# ---------------------------------------------------------------------------

def _load_drift_history(path: Path = DRIFT_HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            return []


def _save_drift_history(history: list[dict[str, Any]], path: Path = DRIFT_HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main drift detection routine
# ---------------------------------------------------------------------------

def detect_drift(
    log_path: Path = LOG_PATH,
    training_path: Path = TRAINING_DATA_PATH,
    history_path: Path = DRIFT_HISTORY_PATH,
) -> dict[str, Any]:
    """
    Run drift detection comparing production logs against the training baseline.

    Steps:
      1. Load training baseline from surgecast_training.parquet.
      2. Load production records from logs/predictions.jsonl.
      3. Compute PSI and KS for each continuous feature.
      4. overall_drift_score = mean PSI across all features.
      5. drift_detected = True if any feature PSI >= PSI_THRESHOLD.
      6. Append result to drift_history.json.

    Returns:
        A drift report dict (same structure as stored in drift_history.json).

    Why this triggers retraining:
        When a feature PSI exceeds 0.25, the production population in that
        bucket has shifted significantly from what the model was trained on.
        The model's learned relationships may no longer be valid, making
        pseudo-labeling + retraining the appropriate response.
    """
    logger.info("Loading training baseline from %s …", training_path)
    if not training_path.exists():
        raise FileNotFoundError(f"Training data not found: {training_path}")

    train_df = pd.read_parquet(training_path)
    logger.info("Training baseline: %d rows, %d columns.", len(train_df), len(train_df.columns))

    production_records = _load_production_logs(log_path)
    n_prod = len(production_records)

    # --- Minimum log guard ---
    # Drift statistics (PSI, KS) are unreliable below a minimum sample size.
    # Requiring MIN_LOGS_FOR_DRIFT records ensures we only act on statistically
    # significant signals, not noise from sparse early traffic.
    if n_prod < MIN_LOGS_FOR_DRIFT:
        print(
            f"Insufficient logs for drift detection: "
            f"{n_prod} records found, {MIN_LOGS_FOR_DRIFT} required."
        )
        logger.info(
            "Insufficient logs for drift detection (%d/%d). "
            "Exiting with no-drift status.",
            n_prod, MIN_LOGS_FOR_DRIFT,
        )
        report: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "n_production_records": n_prod,
            "psi_scores": {},
            "ks_scores": {},
            "overall_drift_score": 0.0,
            "drift_detected": False,
            "psi_threshold": PSI_THRESHOLD,
            "skipped_reason": f"insufficient_logs ({n_prod} < {MIN_LOGS_FOR_DRIFT})",
        }
        history = _load_drift_history(history_path)
        history.append(report)
        _save_drift_history(history, history_path)
        return report

    psi_scores: dict[str, float] = {}
    ks_scores: dict[str, dict[str, float]] = {}

    if n_prod < 30:
        logger.warning(
            "Only %d production records available (minimum 30 recommended). "
            "Drift results may be unreliable.",
            n_prod,
        )

    for feature in CONTINUOUS_FEATURES:
        # Resolve training column (handle alias)
        train_col = feature
        if train_col not in train_df.columns:
            alias = _FEATURE_ALIASES.get(feature)
            if alias and alias in train_df.columns:
                train_col = alias
                logger.debug("Using alias '%s' for feature '%s' in training data.", alias, feature)
            else:
                logger.warning(
                    "Feature '%s' (and alias '%s') not found in training data — skipping.",
                    feature,
                    alias,
                )
                psi_scores[feature] = 0.0
                ks_scores[feature] = {"statistic": 0.0, "p_value": 1.0}
                continue

        ref_vals = train_df[train_col].dropna().to_numpy(dtype=np.float64)
        prod_vals = _extract_feature_series(production_records, feature)

        psi = _compute_psi(ref_vals, prod_vals) if len(prod_vals) > 0 else 0.0
        ks = _compute_ks(ref_vals, prod_vals) if len(prod_vals) > 0 else {"statistic": 0.0, "p_value": 1.0}

        psi_scores[feature] = round(psi, 6)
        ks_scores[feature] = {k: round(v, 6) for k, v in ks.items()}

        logger.info(
            "Feature %-25s  PSI=%.4f  KS_stat=%.4f  KS_p=%.4f",
            feature, psi, ks["statistic"], ks["p_value"],
        )

    overall_drift_score = float(np.mean(list(psi_scores.values()))) if psi_scores else 0.0
    drift_detected = any(v >= PSI_THRESHOLD for v in psi_scores.values())

    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_production_records": n_prod,
        "psi_scores": psi_scores,
        "ks_scores": ks_scores,
        "overall_drift_score": round(overall_drift_score, 6),
        "drift_detected": drift_detected,
        "psi_threshold": PSI_THRESHOLD,
    }

    # Append to drift history
    history = _load_drift_history(history_path)
    history.append(report)
    _save_drift_history(history, history_path)

    if drift_detected:
        logger.warning(
            "⚠ DRIFT DETECTED — overall PSI=%.4f (threshold=%.2f). Retraining recommended.",
            overall_drift_score, PSI_THRESHOLD,
        )
        # Log which specific features triggered drift
        for feat, psi_val in psi_scores.items():
            if psi_val >= PSI_THRESHOLD:
                logger.warning("  → %s: PSI=%.4f (above threshold)", feat, psi_val)
    else:
        logger.info(
            "✓ No significant drift detected — overall PSI=%.4f (threshold=%.2f).",
            overall_drift_score, PSI_THRESHOLD,
        )

    return report


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    report = detect_drift()
    print("\n-- Drift Report --")
    print(json.dumps(report, indent=2))
    print("-" * 50)

    # Exit code 1 signals drift to the GitHub Actions workflow
    sys.exit(1 if report["drift_detected"] else 0)


if __name__ == "__main__":
    main()
