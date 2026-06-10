"""
training/promotion.py — Champion-challenger evaluation and model promotion.

PROMOTION WORKFLOW:
-------------------
Promotion occurs AFTER:
  1. Drift was detected (check_drift.yml triggered this pipeline).
  2. A challenger was trained and evaluated (retrain.yml ran train.py).
  3. The challenger RMSE < champion RMSE (retrain.yml set challenger_wins=true).

Only then does promote.yml invoke this script.

WHAT PROMOTION DOES:
---------------------
If challenger wins:
  1. Copies challenger_model.pkl → model.pkl  (replaces champion)
  2. Copies challenger_feature_importance.json → feature_importance.json
  3. Increments model version number
  4. Updates model_metadata.json with:
       - new MAE, RMSE, R²
       - pseudo_label_std = challenger RMSE  ← critical: next retraining cycle
         uses this value as the noise std for pseudo-label generation
       - status = "champion"
       - drift_triggered = True
  5. Calls register_model() Azure ML hook (no-op if credentials absent)
  6. Calls register_data_asset() Azure ML hook (no-op if credentials absent)

If champion wins (challenger RMSE >= champion RMSE):
  1. Logs the rejection reason
  2. Does NOT increment version
  3. Does NOT update pseudo_label_std
  4. Exits cleanly with code 0

PSEUDO_LABEL_STD CHAIN:
------------------------
  pseudo_label_std always reflects the *last promoted* model's RMSE.
  This creates a self-calibrating loop:
    - v1 RMSE = 0.1347 → pseudo_label_std = 0.1347 for retraining cycle 2
    - v2 RMSE = 0.1210 → pseudo_label_std = 0.1210 for retraining cycle 3
    - ...
  If the champion is NOT replaced, pseudo_label_std remains unchanged —
  the noise level stays calibrated to the best available model.

AZURE ML HOOKS:
---------------
register_model() and register_data_asset() are structured as clean, documented
functions.  They check for Azure ML environment variables and gracefully no-op
if credentials are not configured.  When credentials are available, they use
the Azure ML Python SDK (azure-ai-ml) to register the model and dataset.

To activate:
  Set these environment variables (add as GitHub Actions secrets):
    AZURE_SUBSCRIPTION_ID
    AZURE_RESOURCE_GROUP
    AZURE_ML_WORKSPACE_NAME
    AZURE_TENANT_ID
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET   (or use managed identity)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from training.metadata import (
    CHALLENGER_METADATA_PATH,
    CHAMPION_METADATA_PATH,
    compare_champion_challenger,
    load_metadata,
    save_metadata,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"

CHAMPION_MODEL_PATH = ARTIFACTS_DIR / "model.pkl"
CHALLENGER_MODEL_PATH = ARTIFACTS_DIR / "challenger_model.pkl"

CHAMPION_FI_PATH = ARTIFACTS_DIR / "feature_importance.json"
CHALLENGER_FI_PATH = ARTIFACTS_DIR / "challenger_feature_importance.json"

RETRAINING_DATA_PATH = BASE_DIR / "data" / "retraining_dataset.parquet"

# ---------------------------------------------------------------------------
# Azure ML hooks
# ---------------------------------------------------------------------------

def _azure_credentials_present() -> bool:
    """Return True if the minimum Azure ML environment variables are set."""
    required = [
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "AZURE_ML_WORKSPACE_NAME",
    ]
    return all(os.environ.get(v) for v in required)


def register_model(
    model_name: str,
    version: int,
    model_path: Path,
    metrics: dict,
) -> None:
    """
    Register the promoted champion model in Azure ML Model Registry.

    This function is a clean hook that can be wired to the Azure ML SDK.
    It no-ops gracefully when Azure credentials are not configured so that
    the local retraining pipeline works without cloud dependencies.

    To activate in CI, set:
      AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_ML_WORKSPACE_NAME
      AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET

    Args:
        model_name:  The registered model name in Azure ML (e.g. "surgecast-model").
        version:     The new champion version number.
        model_path:  Absolute path to the model.pkl file to register.
        metrics:     Dict of evaluation metrics to tag the model with.
    """
    if not _azure_credentials_present():
        logger.warning(
            "Azure ML credentials not configured — skipping register_model(). "
            "Set AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_ML_WORKSPACE_NAME "
            "as environment variables or GitHub Actions secrets to enable registration."
        )
        return

    try:
        from azure.ai.ml import MLClient
        from azure.ai.ml.entities import Model
        from azure.ai.ml.constants import AssetTypes
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        client = MLClient(
            credential=credential,
            subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
            resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
            workspace_name=os.environ["AZURE_ML_WORKSPACE_NAME"],
        )

        ml_model = Model(
            path=str(model_path),
            name=model_name,
            description=(
                f"SurgeCast champion model v{version}. "
                f"MAE={metrics.get('mae', 'N/A'):.6f}  "
                f"RMSE={metrics.get('rmse', 'N/A'):.6f}  "
                f"R²={metrics.get('r2', 'N/A'):.6f}"
            ),
            type=AssetTypes.CUSTOM_MODEL,
            tags={
                "version": str(version),
                "mae": str(round(metrics.get("mae", 0), 6)),
                "rmse": str(round(metrics.get("rmse", 0), 6)),
                "r2": str(round(metrics.get("r2", 0), 6)),
                "promoted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        registered = client.models.create_or_update(ml_model)
        logger.info(
            "✓ Model registered in Azure ML: name=%s  version=%s  id=%s",
            registered.name, registered.version, registered.id,
        )
    except ImportError:
        logger.warning(
            "azure-ai-ml package not installed. "
            "Install it with: pip install azure-ai-ml azure-identity"
        )
    except Exception as exc:
        logger.error("Azure ML model registration failed: %s", exc, exc_info=True)


def register_data_asset(
    dataset_name: str,
    version: int,
    data_path: Path,
) -> None:
    """
    Register the retraining dataset as an Azure ML Data Asset.

    Enables full data lineage: each model version is linked to the exact
    dataset it was trained on.  No-ops if credentials are absent.

    Args:
        dataset_name:  The registered data asset name in Azure ML.
        version:       The model version (used to version the data asset too).
        data_path:     Path to the retraining_dataset.parquet file.
    """
    if not _azure_credentials_present():
        logger.warning(
            "Azure ML credentials not configured — skipping register_data_asset(). "
        )
        return

    try:
        from azure.ai.ml import MLClient
        from azure.ai.ml.entities import Data
        from azure.ai.ml.constants import AssetTypes
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        client = MLClient(
            credential=credential,
            subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
            resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
            workspace_name=os.environ["AZURE_ML_WORKSPACE_NAME"],
        )

        data_asset = Data(
            path=str(data_path),
            type=AssetTypes.URI_FILE,
            name=dataset_name,
            description=(
                f"SurgeCast retraining dataset used to train model v{version}. "
                "Combines surgecast_training.parquet + pseudo-labeled production records."
            ),
            tags={"model_version": str(version)},
        )
        registered = client.data.create_or_update(data_asset)
        logger.info(
            "✓ Data asset registered in Azure ML: name=%s  version=%s",
            registered.name, registered.version,
        )
    except ImportError:
        logger.warning(
            "azure-ai-ml package not installed. "
            "Install it with: pip install azure-ai-ml azure-identity"
        )
    except Exception as exc:
        logger.error("Azure ML data asset registration failed: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Promotion logic
# ---------------------------------------------------------------------------

def promote_challenger() -> bool:
    """
    Execute the full champion-challenger evaluation and conditional promotion.

    Returns:
        True  if the challenger was promoted (became the new champion).
        False if the champion was retained.

    Promotion happens ONLY when:
        challenger RMSE < champion RMSE

    When the challenger wins:
      - model.pkl is replaced with challenger_model.pkl
      - feature_importance.json is replaced with challenger_feature_importance.json
      - model_metadata.json is updated with new metrics + incremented version
      - pseudo_label_std is set to the challenger's RMSE (for next cycle)
      - Azure ML registration hooks are called

    When the champion is retained:
      - Nothing changes on disk
      - The rejection is logged with the reason
      - pseudo_label_std is NOT changed (champion's RMSE remains the noise level)
    """
    logger.info("═" * 60)
    logger.info("Champion-Challenger Evaluation")
    logger.info("═" * 60)

    # --- Load both metadata files ---
    logger.info("Loading champion metadata …")
    try:
        champion_meta = load_metadata(CHAMPION_METADATA_PATH)
    except FileNotFoundError:
        logger.error("Champion metadata not found at %s.", CHAMPION_METADATA_PATH)
        sys.exit(1)

    logger.info("Loading challenger metadata …")
    try:
        challenger_meta = load_metadata(CHALLENGER_METADATA_PATH)
    except FileNotFoundError:
        logger.error(
            "Challenger metadata not found at %s. "
            "Run `python -m training.train` first.",
            CHALLENGER_METADATA_PATH,
        )
        sys.exit(1)

    logger.info(
        "Champion  v%s — RMSE=%.6f  MAE=%.6f  R²=%.6f",
        champion_meta["version"], champion_meta["rmse"],
        champion_meta["mae"], champion_meta["r2"],
    )
    logger.info(
        "Challenger v%s — RMSE=%.6f  MAE=%.6f  R²=%.6f",
        challenger_meta["version"], challenger_meta["rmse"],
        challenger_meta["mae"], challenger_meta["r2"],
    )

    # --- Evaluate ---
    winner, reason = compare_champion_challenger(champion_meta, challenger_meta)

    if winner == "champion":
        # Champion retained — log and exit cleanly
        logger.info("Decision: RETAIN CHAMPION")
        logger.info("Reason  : %s", reason)
        _log_promotion_event(
            promoted=False,
            champion_meta=champion_meta,
            challenger_meta=challenger_meta,
            reason=reason,
        )
        return False

    # --- Challenger wins — perform promotion ---
    logger.info("Decision: PROMOTE CHALLENGER")
    logger.info("Reason  : %s", reason)

    if not CHALLENGER_MODEL_PATH.exists():
        logger.error("Challenger model not found at %s. Cannot promote.", CHALLENGER_MODEL_PATH)
        sys.exit(1)

    # 1. Replace champion model artifact
    shutil.copy2(CHALLENGER_MODEL_PATH, CHAMPION_MODEL_PATH)
    logger.info("✓ Replaced model.pkl with challenger_model.pkl")

    # 2. Replace champion feature importance
    if CHALLENGER_FI_PATH.exists():
        shutil.copy2(CHALLENGER_FI_PATH, CHAMPION_FI_PATH)
        logger.info("✓ Replaced feature_importance.json with challenger_feature_importance.json")

    # 3. Build updated champion metadata
    new_version = int(champion_meta["version"]) + 1
    new_meta = {
        "model_name": "surgecast-model",
        "version": new_version,
        "mae": float(challenger_meta["mae"]),
        "rmse": float(challenger_meta["rmse"]),
        "r2": float(challenger_meta["r2"]),
        # pseudo_label_std = challenger RMSE — this is the noise level for the
        # NEXT retraining cycle's pseudo-label generation.  It must always equal
        # the latest promoted model's RMSE so the noise is calibrated.
        "pseudo_label_std": float(challenger_meta["rmse"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drift_triggered": bool(challenger_meta.get("drift_triggered", True)),
        "status": "champion",
        "promoted_from_version": challenger_meta["version"],
        "promotion_reason": reason,
    }
    save_metadata(new_meta, CHAMPION_METADATA_PATH)
    logger.info("✓ model_metadata.json updated (v%s → v%s)", champion_meta["version"], new_version)
    logger.info(
        "✓ pseudo_label_std updated: %.6f → %.6f (challenger RMSE)",
        champion_meta.get("pseudo_label_std", champion_meta["rmse"]),
        challenger_meta["rmse"],
    )

    # 4. Azure ML registration
    register_model(
        model_name="surgecast-model",
        version=new_version,
        model_path=CHAMPION_MODEL_PATH,
        metrics={
            "mae": challenger_meta["mae"],
            "rmse": challenger_meta["rmse"],
            "r2": challenger_meta["r2"],
        },
    )
    register_data_asset(
        dataset_name="surgecast-retraining-data",
        version=new_version,
        data_path=RETRAINING_DATA_PATH,
    )

    # 5. Log promotion event
    _log_promotion_event(
        promoted=True,
        champion_meta=champion_meta,
        challenger_meta=challenger_meta,
        reason=reason,
        new_version=new_version,
    )

    logger.info("═" * 60)
    logger.info("Promotion complete: SurgeCast model v%s is now champion.", new_version)
    logger.info("═" * 60)
    return True


def _log_promotion_event(
    promoted: bool,
    champion_meta: dict,
    challenger_meta: dict,
    reason: str,
    new_version: int | None = None,
) -> None:
    """Append a structured promotion event to artifacts/promotion_log.jsonl."""
    log_path = ARTIFACTS_DIR / "promotion_log.jsonl"
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "promoted": promoted,
        "champion_version_before": champion_meta.get("version"),
        "champion_rmse_before": champion_meta.get("rmse"),
        "challenger_rmse": challenger_meta.get("rmse"),
        "new_champion_version": new_version,
        "reason": reason,
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")
    logger.info("Promotion event logged → %s", log_path)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    promoted = promote_challenger()
    # Exit 0 always — promotion failure is a business decision, not an error.
    sys.exit(0)


if __name__ == "__main__":
    main()
