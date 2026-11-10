"""Leakage and chronological split tests for ml/features.

References:
- docs/DATA_AND_ML_SPEC.md sections 5 and 6
- AGENTS.md section 4 (Non-negotiables 1 & 2)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.features.build_features import (
    FEATURE_COLUMNS,
    FORBIDDEN_COLUMNS,
    assert_no_leakage_features,
    compute_weather_features,
)
from ml.features.split import (
    compute_split_date_blocks,
    assign_split_column,
    get_walk_forward_folds,
)

def test_no_leakage_in_features():
    """Verify that feature list contains zero forbidden names."""
    assert_no_leakage_features(FEATURE_COLUMNS)
    for feat in FEATURE_COLUMNS:
        for forbidden in FORBIDDEN_COLUMNS:
            assert forbidden not in feat.lower(), f"Forbidden substring '{forbidden}' in feature '{feat}'"
    print("✓ test_no_leakage_in_features passed")

def test_chronological_splits():
    """Verify strictly increasing non-overlapping date blocks."""
    # 34 dates matching the dataset range May 15 to June 17, 2020
    dates = pd.date_range("2020-05-15", "2020-06-17", freq="D").strftime("%Y-%m-%d").tolist()
    assert len(dates) == 34

    blocks = compute_split_date_blocks(dates)
    train_start, train_end = blocks["train"]
    val_start, val_end = blocks["val"]
    test_start, test_end = blocks["test"]

    # Strictly chronological
    assert train_start <= train_end
    assert train_end < val_start
    assert val_start <= val_end
    assert val_end < test_start
    assert test_start <= test_end

    # Test assign_split_column
    df = pd.DataFrame({"timestamp": [f"{d}T12:00:00" for d in dates]})
    assigned = assign_split_column(df, blocks)
    assert set(assigned["split"].unique()) == {"train", "val", "test"}
    print("✓ test_chronological_splits passed")

def test_walk_forward_folds_inside_train():
    """Verify walk-forward CV folds stay strictly within the train block."""
    dates = pd.date_range("2020-05-15", "2020-06-06", freq="D").strftime("%Y-%m-%d").tolist()  # 23 train days
    folds = get_walk_forward_folds(dates, fold_train_days=12, fold_test_days=3)

    assert len(folds) >= 3
    for f in folds:
        assert max(f["train_dates"]) < min(f["test_dates"])
        assert f["train_dates"] == dates[: len(f["train_dates"])]  # expanding window from day 0
    print("✓ test_walk_forward_folds_inside_train passed")

def test_trailing_window_no_future_leakage():
    """Verify that future rows do not affect trailing rolling/lag features at time t."""
    times = pd.date_range("2020-05-15T06:00:00", periods=8, freq="15min").strftime("%Y-%m-%dT%H:%M:%S").tolist()
    base_weather = pd.DataFrame({
        "timestamp": times,
        "irradiation_kw_m2": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        "module_temp_c": [25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0],
        "ambient_temp_c": [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0],
    })
    feat1 = compute_weather_features(base_weather)

    # Change future rows (index 5, 6, 7)
    modified_weather = base_weather.copy()
    modified_weather.loc[5:, "irradiation_kw_m2"] = [1.5, 1.5, 1.5]
    feat2 = compute_weather_features(modified_weather)

    # Past rows (index 0..4) must be strictly identical
    for col in FEATURE_COLUMNS:
        np.testing.assert_allclose(
            feat1.loc[:4, col].values,
            feat2.loc[:4, col].values,
            err_msg=f"Future data leakage detected in feature '{col}'!",
        )
    print("✓ test_trailing_window_no_future_leakage passed")

if __name__ == "__main__":
    test_no_leakage_in_features()
    test_chronological_splits()
    test_walk_forward_folds_inside_train()
    test_trailing_window_no_future_leakage()
    print("All feature and split unit tests passed successfully!")

