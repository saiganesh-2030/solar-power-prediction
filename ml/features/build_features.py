"""Feature engineering module for solar power expected-power regression models.

References:
- docs/DATA_AND_ML_SPEC.md section 5
- AGENTS.md section 4 (Non-negotiable 1: No leakage)
"""

from typing import List
import numpy as np
import pandas as pd

# The exact feature set allowed for the expected-power regression model
FEATURE_COLUMNS: List[str] = [
    "irradiation_kw_m2",
    "module_temp_c",
    "ambient_temp_c",
    "temp_delta_c",
    "hour_sin",
    "hour_cos",
    "irr_lag1",
    "irr_diff1",
    "irr_roll_mean_4",
    "irr_roll_std_4",
    "irr_x_modtemp",
]

# Explicitly forbidden column names (tested in CI)
FORBIDDEN_COLUMNS: List[str] = [
    "dc_kw",
    "dc_power",
    "daily_yield_kwh",
    "daily_yield",
    "total_yield_kwh",
    "total_yield",
    "ac_kw",
    "ac_power",
    "inverter_id",
    "plant_id",
    "date",
    "day",
    "day_index",
    "row_index",
]

def assert_no_leakage_features(features: List[str]) -> None:
    """Strict leakage guard ensuring forbidden columns never enter the model."""
    for feat in features:
        feat_lower = feat.lower()
        for forbidden in FORBIDDEN_COLUMNS:
            if forbidden == feat_lower or forbidden in feat_lower:
                raise ValueError(
                    f"Leakage violation! Feature '{feat}' contains forbidden input '{forbidden}'. "
                    f"Expected-power models must use weather and time features only."
                )

# Assert at module load time
assert_no_leakage_features(FEATURE_COLUMNS)

def compute_weather_features(df_weather: pd.DataFrame) -> pd.DataFrame:
    """Computes time and trailing weather features on regular 15-minute weather series.
    
    Trailing windows only (no future data leakage).
    """
    df = df_weather.copy()
    dt = pd.to_datetime(df["timestamp"])

    # 1. Temperature delta
    df["temp_delta_c"] = df["module_temp_c"] - df["ambient_temp_c"]

    # 2. Cyclical time of day features
    minute_of_day = dt.dt.hour * 60 + dt.dt.minute
    df["hour_sin"] = np.sin(2 * np.pi * minute_of_day / 1440.0)
    df["hour_cos"] = np.cos(2 * np.pi * minute_of_day / 1440.0)

    # 3. Trailing irradiance features (shifts and trailing rolling windows)
    irr = df["irradiation_kw_m2"]
    df["irr_lag1"] = irr.shift(1)
    df["irr_diff1"] = irr.diff(1)
    df["irr_roll_mean_4"] = irr.rolling(window=4, min_periods=1).mean()
    df["irr_roll_std_4"] = irr.rolling(window=4, min_periods=1).std().fillna(0.0)

    # 4. Irradiance x module temperature interaction
    df["irr_x_modtemp"] = irr * df["module_temp_c"]

    return df

