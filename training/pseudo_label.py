"""
training/pseudo_label.py — Pseudo-label generation for SurgeCast retraining.

WHY PSEUDO-LABELING?
---------------------
In production, each prediction request returns a surge multiplier estimate.
Riders and drivers never report what the "true" surge should have been, so
we have NO ground-truth labels for production records.

True online supervised learning is therefore impossible:
  - We cannot compute a loss function against real targets.
  - We cannot correct the model based on actual rider responses.

Instead, we simulate continuous learning via pseudo-labeling:

    pseudo_label = prediction + N(0, RMSE)

Where RMSE is the root mean squared error of the currently promoted champion
model on its validation set.  This approach:
  1. Acknowledges the prediction as a noisy estimate of the true surge.
  2. Adds calibrated Gaussian noise (std = RMSE) to prevent the model from
     simply memorising its own predictions (collapsed self-distillation).
  3. Uses RMSE — not an arbitrary constant — so the noise scale reflects the
     champion's actual observed uncertainty on held-out data.

IMPORTANT: We do NOT use the raw prediction as the label directly.
  - That would cause the model to distil into itself unchanged.
  - The noise breaks this degeneracy and approximates the residual uncertainty
    around each prediction.

RECORD DEDUPLICATION (last_processed_log_timestamp):
------------------------------------------------------
Each retraining cycle must only consume NEW production log records — those
written AFTER the last successful promotion.  Without this guard, every cycle
re-processes the same records, causing duplicate learning and unbounded dataset
growth.

The cutoff timestamp is read from model_metadata.json:
  - On first run (bootstrap): null → process ALL existing logs.
  - After each promotion: set to the newest log timestamp consumed.
  - Next cycle: only records with timestamp > last_processed_log_timestamp
    are processed.

_load_production_records() accepts an optional cutoff and applies this filter.
generate_pseudo_labels() returns (pseudo_df, latest_timestamp_processed).
main() prints "latest_timestamp_processed=<value>" so the promote workflow
can capture it via shell and persist it back to model_metadata.json.

RETRAINING DATASET CONSTRUCTION:
---------------------------------
    retraining_dataset.parquet = surgecast_training.parquet
                                + pseudo_labeled_production_rows

The historical dataset is always included to prevent catastrophic forgetting:
the model must continue to generalise over the full original distribution,
not just recent production traffic.

RMSE CHAIN:
-----------
  v1 champion RMSE = 0.1347 → used as noise std for first pseudo-label batch
  v2 champion RMSE = 0.1210 → used as noise std for next pseudo-label batch
  ...
  The RMSE is always read from model_metadata.json (pseudo_label_std field),
  which is updated only when a new champion is promoted.  This ensures each
  retraining cycle uses the noise level calibrated to the last promoted model.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from training.metadata import load_metadata, CHAMPION_METADATA_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "logs" / "predictions.jsonl"

TRAINING_DATASET_PATH = Path(
    os.getenv(
        "TRAINING_DATASET_PATH",
        str(BASE_DIR / "data" / "surgecast_training.parquet"),
    )
)
TRAINING_DATA_PATH = TRAINING_DATASET_PATH  # alias used internally
RETRAINING_DATA_PATH = BASE_DIR / "data" / "retraining_dataset.parquet"

# ---------------------------------------------------------------------------
# Feature columns (canonical spec order — must match training)
# ---------------------------------------------------------------------------
FEATURE_COLS = [
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
    "congestion_ratio",
    "demand_growth_rate",
    "rushhour_congestion",
    "rain_congestion",
    "temp_congestion",
]

TARGET = "surge_multiplier"

# Backend internal key for the congestion feature (written to JSONL logs).
# We accept both names when reading production logs.
_CONGESTION_ALIASES = {"congestion_ratio", "traffic_flow_ratio"}


# ---------------------------------------------------------------------------
# Log loading
# ---------------------------------------------------------------------------

def _load_production_records(
    path: Path = LOG_PATH,
    after_timestamp: str | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Load records from logs/predictions.jsonl.

    Each record must have the shape:
        { "features": {...}, "prediction": float, "timestamp": "..." }

    Args:
        path:             Path to the JSONL log file.
        after_timestamp:  ISO-8601 string.  When provided, only records whose
                          ``timestamp`` field is strictly GREATER THAN this
                          value are returned.  Pass None to process all records
                          (first-run / bootstrap behaviour).

    Returns:
        (records, latest_timestamp) where:
          - records is the list of accepted log dicts.
          - latest_timestamp is the maximum timestamp string seen across all
            accepted records, or None if no records were accepted.

        Records without a ``timestamp`` field are accepted (they cannot be
        filtered by time) but do not contribute to latest_timestamp.

    Returns ([], None) if the file is missing or empty.
    """
    if not path.exists():
        logger.warning(
            "Production log not found at %s. "
            "Returning empty — no pseudo-labeled rows will be added.",
            path,
        )
        return [], None

    records: list[dict[str, Any]] = []
    latest_ts: str | None = None
    skipped_old = 0

    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "features" not in rec or "prediction" not in rec:
                    logger.debug("Line %d skipped (missing features or prediction).", lineno)
                    continue

                rec_ts: str | None = rec.get("timestamp")

                # Apply cutoff filter when a cutoff is supplied and the record
                # has a timestamp.  Records without a timestamp are always
                # included (conservative: don't silently discard them).
                if after_timestamp is not None and rec_ts is not None:
                    if rec_ts <= after_timestamp:
                        skipped_old += 1
                        continue

                records.append(rec)

                # Track the newest timestamp seen among accepted records
                if rec_ts is not None:
                    if latest_ts is None or rec_ts > latest_ts:
                        latest_ts = rec_ts

            except json.JSONDecodeError as exc:
                logger.warning("Malformed JSONL at line %d: %s", lineno, exc)

    if skipped_old:
        logger.info(
            "Skipped %d already-processed log records (timestamp <= '%s').",
            skipped_old, after_timestamp,
        )
    logger.info("Loaded %d new production records from %s.", len(records), path)
    return records, latest_ts



# ---------------------------------------------------------------------------
# Pseudo-label generation
# ---------------------------------------------------------------------------

def generate_pseudo_labels(
    records: list[dict[str, Any]],
    rmse: float,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """
    Convert raw production records into a pseudo-labeled DataFrame.

    For each record:
        pseudo_label = prediction + N(0, rmse)

    The Gaussian noise std equals the champion's RMSE so that the added
    uncertainty is calibrated to the model's real-world error distribution.

    Args:
        records:  List of production log records.
        rmse:     Standard deviation for the pseudo-label noise (= champion RMSE).
        rng:      Optional numpy random generator for reproducibility.

    Returns:
        DataFrame with all FEATURE_COLS columns plus surge_multiplier (pseudo-label).
        Rows with missing required features are dropped with a warning.
    """
    if not records:
        logger.warning("No records to pseudo-label. Returning empty DataFrame.")
        return pd.DataFrame(columns=FEATURE_COLS + [TARGET])

    if rng is None:
        rng = np.random.default_rng()

    rows: list[dict[str, Any]] = []
    skipped = 0

    for rec in records:
        feats: dict[str, Any] = rec.get("features", {})
        prediction = rec.get("prediction")

        if prediction is None:
            skipped += 1
            continue

        # Normalise congestion_ratio alias
        if "congestion_ratio" not in feats and "traffic_flow_ratio" in feats:
            feats["congestion_ratio"] = feats["traffic_flow_ratio"]

        # Build row with required feature columns
        row: dict[str, Any] = {}
        missing_cols: list[str] = []
        for col in FEATURE_COLS:
            val = feats.get(col)
            if val is None:
                missing_cols.append(col)
                row[col] = np.nan
            else:
                row[col] = val

        if missing_cols:
            # Warn but continue — median imputation will fill these during training
            logger.debug("Record missing columns %s — will be imputed during training.", missing_cols)

        # PSEUDO-LABEL: prediction + N(0, RMSE)
        # We do NOT use prediction directly — this would collapse the model.
        noise = float(rng.normal(0.0, rmse))
        pseudo_label = float(prediction) + noise
        # Clamp to a physically sensible range for surge multipliers
        pseudo_label = max(1.0, round(pseudo_label, 6))

        row[TARGET] = pseudo_label
        rows.append(row)

    if skipped:
        logger.warning("Skipped %d records with missing prediction values.", skipped)

    df = pd.DataFrame(rows, columns=FEATURE_COLS + [TARGET])
    logger.info(
        "Generated %d pseudo-labeled rows (RMSE noise std=%.6f).",
        len(df), rmse,
    )
    return df



# ---------------------------------------------------------------------------
# Dataset merge and save
# ---------------------------------------------------------------------------

def build_retraining_dataset(
    pseudo_df: pd.DataFrame,
    historical_path: Path = TRAINING_DATA_PATH,
    output_path: Path = RETRAINING_DATA_PATH,
) -> pd.DataFrame:
    """
    Merge the pseudo-labeled production rows with the historical training dataset.

    retraining_dataset = surgecast_training.parquet  ← historical ground-truth
                       + pseudo_labeled_production   ← new pseudo-labeled rows

    We always keep the historical dataset to prevent catastrophic forgetting:
    if only pseudo-labeled data were used, the model would lose the carefully
    curated distribution from the original training set.

    Args:
        pseudo_df:        Pseudo-labeled production rows (output of generate_pseudo_labels).
        historical_path:  Path to the authoritative historical parquet.
        output_path:      Where to save the combined retraining dataset.

    Returns:
        The combined DataFrame.
    """
    logger.info("Loading historical dataset from %s …", historical_path)
    if not historical_path.exists():
        raise FileNotFoundError(
            f"Historical training data not found: {historical_path}. "
            "This file is required to build the retraining dataset."
        )

    hist_df = pd.read_parquet(historical_path)
    logger.info("Historical dataset: %d rows.", len(hist_df))

    if pseudo_df.empty:
        logger.warning(
            "No pseudo-labeled rows to append. "
            "retraining_dataset will equal surgecast_training.parquet exactly."
        )
        combined = hist_df.copy()
    else:
        # Align columns: keep only columns present in historical dataset
        common_cols = [c for c in pseudo_df.columns if c in hist_df.columns]
        pseudo_aligned = pseudo_df[common_cols].copy()

        combined = pd.concat([hist_df, pseudo_aligned], ignore_index=True)
        logger.info(
            "Combined dataset: %d rows = %d historical + %d pseudo-labeled.",
            len(combined), len(hist_df), len(pseudo_aligned),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output_path, index=False)
    logger.info("Retraining dataset saved → %s (%d rows).", output_path, len(combined))
    return combined


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Full pseudo-label generation pipeline:
      1. Read current champion RMSE and last_processed_log_timestamp from model_metadata.json
      2. Load ONLY NEW production records (timestamp > last_processed_log_timestamp)
      3. Generate pseudo-labeled rows (prediction + N(0, RMSE))
      4. Merge with surgecast_training.parquet
      5. Save data/retraining_dataset.parquet
      6. Print latest_timestamp_processed so the promote workflow can persist it
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # Step 1: Read RMSE and timestamp cutoff from champion metadata
    logger.info("Reading champion metadata from %s …", CHAMPION_METADATA_PATH)
    try:
        meta = load_metadata(CHAMPION_METADATA_PATH)
    except FileNotFoundError:
        logger.error(
            "Champion metadata not found. Run `python -m training.metadata` first."
        )
        sys.exit(1)

    current_rmse = float(meta["pseudo_label_std"])
    cutoff_ts: str | None = meta.get("last_processed_log_timestamp")  # None on first run

    logger.info(
        "Champion: version=%s  RMSE=%.6f  pseudo_label_std=%.6f",
        meta["version"], meta["rmse"], current_rmse,
    )
    if cutoff_ts is None:
        logger.info("last_processed_log_timestamp=null — processing ALL log records (first run).")
    else:
        logger.info("last_processed_log_timestamp='%s' — only processing newer records.", cutoff_ts)

    # Step 2: Load only NEW production records (after cutoff)
    records, latest_ts = _load_production_records(LOG_PATH, after_timestamp=cutoff_ts)

    # Step 3: Generate pseudo-labels
    # Noise std = current champion RMSE — calibrated to the model's own error distribution.
    pseudo_df = generate_pseudo_labels(records, rmse=current_rmse)

    # Step 4 + 5: Merge and save
    combined = build_retraining_dataset(pseudo_df)

    print("\n-- Pseudo-Label Summary --")
    print(f"  Last processed timestamp  : {cutoff_ts or 'null (first run)'}")
    print(f"  Production records loaded : {len(records)}")
    print(f"  Pseudo-labeled rows added : {len(pseudo_df)}")
    print(f"  Noise std (champion RMSE) : {current_rmse:.6f}")
    print(f"  Retraining dataset rows   : {len(combined)}")
    print(f"  Output path               : {RETRAINING_DATA_PATH}")
    # Emit machine-readable line for the promote workflow to capture via shell
    print(f"  Latest timestamp processed: {latest_ts or 'null'}")
    print("-" * 50 + "\n")

    # Emit a key=value line that the workflow can grep / capture precisely
    print(f"PSEUDO_LABEL_LATEST_TS={latest_ts or 'null'}")


if __name__ == "__main__":
    main()

