from __future__ import annotations

import pandas as pd


def apply_feature_order(
    feature_map: dict[str, float | int],
    feature_columns: list[str],
) -> pd.DataFrame:
    frame = pd.DataFrame([feature_map])

    for column in feature_columns:
        if column not in frame.columns:
            frame[column] = 0

    ordered = frame[feature_columns]
    return ordered
