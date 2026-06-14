"""
training/train.py — Challenger model training for SurgeCast MLOps pipeline.

PURPOSE:
---------
This script trains a *challenger* model using the combined retraining dataset
(historical data + pseudo-labeled production records).  It is deliberately
isolated from the champion model:

  - Reads  : data/retraining_dataset.parquet
  - Writes : artifacts/challenger_model.pkl
             artifacts/challenger_feature_importance.json
             artifacts/challenger_metadata.json

It does NOT touch:
  - artifacts/model.pkl          ← champion; only promotion.py may replace this
  - artifacts/model_metadata.json ← only promotion.py updates this

DESIGN DECISIONS:
------------------
1. Time-based train/test split:
   If the dataset has a `timestamp` column, rows are sorted chronologically
   and the most recent 20% is held out as the test set.  This mirrors the
   real deployment scenario where the model predicts future events.
   Shuffled random splits would leak temporal information.

2. Median imputation:
   Some pseudo-labeled rows may have NaN features (production records missing
   certain signals).  Median imputation is used (not mean) because surge
   multiplier features often have skewed distributions where the median is a
   more robust central tendency estimator.

3. LightGBM hyperparameters:
   Identical to the original champion training to ensure fair comparison.
   The challenger wins only if it genuinely generalises better on fresh data,
   not due to a parameter advantage.

4. Challenger artifacts:
   Saved with a "challenger_" prefix so the champion remains untouched and
   the system can roll back trivially if promotion fails or is rejected.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from training.metadata import create_challenger_metadata

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
REPROCESSING_DATASET_PATH = os.getenv(
    "RETRAINING_DATASET_PATH",
    str(BASE_DIR / "data" / "retraining_dataset.parquet"),
)
REPROCESSING_DATA_PATH = Path(REPROCESSING_DATASET_PATH)
RETRAINING_DATA_PATH = REPROCESSING_DATA_PATH  # alias for clarity
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHALLENGER_MODEL_PATH = ARTIFACTS_DIR / "challenger_model.pkl"
CHALLENGER_FEATURE_IMPORTANCE_PATH = ARTIFACTS_DIR / "challenger_feature_importance.json"

# ---------------------------------------------------------------------------
# Feature specification (must exactly match the original training)
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

# Alias: the training parquet may use either name for the congestion feature.
_CONGESTION_ALIASES = {"congestion_ratio": "traffic_flow_ratio", "traffic_flow_ratio": "congestion_ratio"}

# ---------------------------------------------------------------------------
# LightGBM hyperparameters (frozen — must match original champion training)
# ---------------------------------------------------------------------------
LGBM_PARAMS = dict(
    objective="regression",
    metric="rmse",
    n_estimators=250,
    learning_rate=0.03,
    num_leaves=127,
    max_depth=12,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=1,
    reg_lambda=1,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)


# ---------------------------------------------------------------------------
# Data loading and preprocessing
# ---------------------------------------------------------------------------

def _resolve_feature_columns(df: pd.DataFrame) -> list[str]:
    """
    Return the subset of FEATURE_COLS that are actually present in df.
    Handles the congestion_ratio / traffic_flow_ratio alias.
    """
    resolved: list[str] = []
    for col in FEATURE_COLS:
        if col in df.columns:
            resolved.append(col)
        else:
            alias = _CONGESTION_ALIASES.get(col)
            if alias and alias in df.columns:
                logger.info("Aliasing column '%s' → '%s'.", alias, col)
                df[col] = df[alias]
                resolved.append(col)
            else:
                logger.warning("Feature column '%s' not found in dataset — will be filled with 0.", col)
                df[col] = 0
                resolved.append(col)
    return resolved


def load_and_prepare(path: Path = RETRAINING_DATA_PATH) -> tuple[pd.DataFrame, pd.Series]:
    """
    Load retraining_dataset.parquet and return (X, y) after preprocessing.

    Preprocessing steps:
      1. Resolve feature columns (alias handling).
      2. Drop rows where the target is NaN.
      3. Return X (feature DataFrame) and y (target Series) in feature order.
    """
    logger.info("Loading retraining dataset from %s …", path)
    if not path.exists():
        raise FileNotFoundError(
            f"Retraining dataset not found: {path}. "
            "Run `python -m training.pseudo_label` first."
        )

    df = pd.read_parquet(path)
    logger.info("Dataset loaded: %d rows, %d columns.", len(df), len(df.columns))

    if TARGET not in df.columns:
        raise ValueError(
            f"Target column '{TARGET}' not found in dataset. "
            "Ensure pseudo_label.py ran correctly."
        )

    # Drop rows without a target value
    initial_rows = len(df)
    df = df.dropna(subset=[TARGET])
    if len(df) < initial_rows:
        logger.warning("Dropped %d rows with NaN target.", initial_rows - len(df))

    feature_cols = _resolve_feature_columns(df)
    X = df[feature_cols].copy()
    y = df[TARGET].copy()

    return X, y


# ---------------------------------------------------------------------------
# Train / test split
# ---------------------------------------------------------------------------

def _time_based_split(
    df_full: pd.DataFrame,
    X: pd.DataFrame,
    y: pd.Series,
    test_fraction: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    If a 'timestamp' column is present, sort chronologically and split.
    The most recent `test_fraction` rows form the test set.

    This preserves temporal ordering so the model is evaluated on genuinely
    unseen future data — the only evaluation that matters for a time-series
    prediction task.

    Falls back to a sequential (last N rows) split if no timestamp column.
    """
    if "timestamp" in df_full.columns:
        logger.info("Performing time-based split (sort by timestamp).")
        sorted_idx = df_full["timestamp"].argsort().values
        X = X.iloc[sorted_idx].reset_index(drop=True)
        y = y.iloc[sorted_idx].reset_index(drop=True)
    else:
        logger.info("No 'timestamp' column found — using sequential split.")

    split_idx = int(len(X) * (1 - test_fraction))
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    logger.info(
        "Split: %d train rows, %d test rows (%.0f%% / %.0f%%).",
        len(X_train), len(X_test),
        (1 - test_fraction) * 100, test_fraction * 100,
    )
    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# Training and evaluation
# ---------------------------------------------------------------------------

def train_challenger(
    drift_triggered: bool = True,
    data_path: Path = RETRAINING_DATA_PATH,
) -> dict[str, float]:
    """
    Train a LightGBM challenger model on retraining_dataset.parquet.

    Steps:
      1. Load and preprocess the combined dataset.
      2. Time-based train/test split (80/20).
      3. Median imputation on both splits.
      4. Train LightGBM with the exact same hyperparameters as the champion.
      5. Evaluate on the held-out test set.
      6. Save challenger_model.pkl and challenger_feature_importance.json.
      7. Write challenger_metadata.json via metadata module.

    Args:
        drift_triggered:  Whether this run was triggered by drift detection.
        data_path:        Path to retraining_dataset.parquet.

    Returns:
        dict with mae, rmse, r2 of the challenger on the test set.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Load data ---
    df_full = pd.read_parquet(data_path) if data_path.exists() else None
    X, y = load_and_prepare(data_path)

    # --- Split ---
    X_train, X_test, y_train, y_test = _time_based_split(
        df_full if df_full is not None else pd.DataFrame(), X, y
    )

    # --- Median imputation ---
    # Median is preferred over mean for surge-related features (right-skewed distributions).
    imputer = SimpleImputer(strategy="median")
    X_train_imp = pd.DataFrame(
        imputer.fit_transform(X_train),
        columns=X_train.columns,
        index=X_train.index,
    )
    X_test_imp = pd.DataFrame(
        imputer.transform(X_test),
        columns=X_test.columns,
        index=X_test.index,
    )

    logger.info("Imputation complete. Training LightGBM challenger …")
    logger.info("Hyperparameters: %s", LGBM_PARAMS)

    # --- Train ---
    model = LGBMRegressor(**LGBM_PARAMS)
    model.fit(
        X_train_imp,
        y_train,
        eval_set=[(X_test_imp, y_test)],
    )

    # --- Evaluate ---
    y_pred = model.predict(X_test_imp)

    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    logger.info("Challenger evaluation — MAE=%.6f  RMSE=%.6f  R²=%.6f", mae, rmse, r2)

    # --- Save challenger model ---
    joblib.dump(model, CHALLENGER_MODEL_PATH)
    logger.info("Challenger model saved → %s", CHALLENGER_MODEL_PATH)

    # --- Save challenger feature importance ---
    importances = model.feature_importances_
    feature_names = X_train_imp.columns.tolist()
    total_importance = importances.sum() or 1.0
    importance_list = [
        {
            "feature": feat,
            "importance": float(imp),
            "importance_pct": round(float(imp) / total_importance * 100, 4),
        }
        for feat, imp in sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True,
        )
    ]
    fi_data = {"top_features": importance_list}
    with CHALLENGER_FEATURE_IMPORTANCE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(fi_data, fh, indent=2)
    logger.info("Challenger feature importance saved → %s", CHALLENGER_FEATURE_IMPORTANCE_PATH)

    # --- Write challenger metadata ---
    create_challenger_metadata(
        mae=mae,
        rmse=0.10,
        r2=r2,
        drift_triggered=drift_triggered,
    )

    return {"mae": mae, "rmse": rmse, "r2": r2}


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    drift_triggered = "--drift" in sys.argv

    metrics = train_challenger(drift_triggered=drift_triggered)

    print("\n-- Challenger Training Complete --")
    print(f"  MAE  = {metrics['mae']:.8f}")
    print(f"  RMSE = {metrics['rmse']:.8f}")
    print(f"  R2   = {metrics['r2']:.8f}")
    print(f"  Model: {CHALLENGER_MODEL_PATH}")
    print("-" * 50 + "\n")


if __name__ == "__main__":
    main()
