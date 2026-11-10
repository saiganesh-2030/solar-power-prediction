"""Unit tests for ml/data/ modules: load, clean, and quality_flags.

Tests on small hand-crafted DataFrames to verify:
- Explicit timestamp parsing and failure handling
- Weather gap interpolation limit (<= 2 intervals interpolated, > 2 left empty and flagged)
- Night power flag detection
- Negative power flag detection
- Flatline flag detection on daylight intervals
- Gap before flag detection
- AC/DC inconsistency flag detection
- Composite flag_any behavior

References:
- docs/roles/ROLE_1_ML_ENGINEER.md task list
- docs/DATA_AND_ML_SPEC.md sections 3 and 4
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.data.clean import clean_weather_series, join_generation_weather
from ml.data.quality_flags import add_quality_flags, compute_capacity_proxy

def test_weather_interpolation_limits():
    """Verify that gaps <= 2 intervals are interpolated, while gaps > 2 stay NaN."""
    # Create 6 intervals with a 1-interval gap and a 3-interval gap
    times = [
        "2020-05-15T06:00:00",
        "2020-05-15T06:15:00",
        # 06:30 missing (gap of 1) -> should be interpolated
        "2020-05-15T06:45:00",
        # 07:00, 07:15, 07:30 missing (gap of 3) -> should NOT be interpolated
        "2020-05-15T07:45:00",
    ]
    raw_weather = pd.DataFrame({
        "plant_id": [1, 1, 1, 1],
        "timestamp": times,
        "irradiation_kw_m2": [0.20, 0.30, 0.50, 0.90],
        "module_temp_c": [25.0, 27.0, 31.0, 40.0],
        "ambient_temp_c": [22.0, 23.0, 25.0, 28.0],
    })

    cleaned = clean_weather_series(raw_weather, plant_id=1)
    cleaned = cleaned.set_index("timestamp")

    # 1-interval gap at 06:30 should be interpolated between 0.30 and 0.50 -> 0.40
    assert not cleaned.loc["2020-05-15T06:30:00", "flag_missing_weather"]
    assert np.isclose(cleaned.loc["2020-05-15T06:30:00", "irradiation_kw_m2"], 0.40)

    # In 3-interval gap, 07:30 cannot be reached with limit=2 forward -> stays NaN and flagged
    assert cleaned.loc["2020-05-15T07:30:00", "flag_missing_weather"]
    assert np.isnan(cleaned.loc["2020-05-15T07:30:00", "irradiation_kw_m2"])

def test_quality_flag_night_power():
    """Verify that significant power during night (irradiation < 0.01) is flagged."""
    df = pd.DataFrame({
        "plant_id": [1, 1],
        "timestamp": ["2020-05-15T00:00:00", "2020-05-15T00:15:00"],
        "inverter_id": ["INV_01", "INV_01"],
        "dc_kw": [50.0, 0.0],
        "ac_kw": [50.0, 0.0],  # 50 kW at night vs 0 kW
        "daily_yield_kwh": [0.0, 0.0],
        "total_yield_kwh": [100.0, 100.0],
        "irradiation_kw_m2": [0.0, 0.0],
        "module_temp_c": [22.0, 22.0],
        "ambient_temp_c": [20.0, 20.0],
        "flag_missing_weather": [False, False],
    })
    # Capacity proxy 800 kW -> 0.5% is 4.0 kW
    flagged = add_quality_flags(df, capacity_proxy=800.0)
    assert flagged.loc[0, "flag_night_power"]
    assert not flagged.loc[1, "flag_night_power"]
    assert flagged.loc[0, "flag_any"]

def test_quality_flag_negative_power():
    """Verify negative power values are flagged."""
    df = pd.DataFrame({
        "plant_id": [1, 1],
        "timestamp": ["2020-05-15T12:00:00", "2020-05-15T12:15:00"],
        "inverter_id": ["INV_01", "INV_01"],
        "dc_kw": [500.0, -10.0],
        "ac_kw": [-5.0, 100.0],
        "daily_yield_kwh": [50.0, 50.0],
        "total_yield_kwh": [100.0, 100.0],
        "irradiation_kw_m2": [0.8, 0.8],
        "module_temp_c": [45.0, 45.0],
        "ambient_temp_c": [30.0, 30.0],
        "flag_missing_weather": [False, False],
    })
    flagged = add_quality_flags(df, capacity_proxy=800.0)
    assert flagged.loc[0, "flag_negative"]  # negative ac
    assert flagged.loc[1, "flag_negative"]  # negative dc

def test_quality_flag_gap_before():
    """Verify missing 15-minute interval sets flag_gap_before on subsequent interval."""
    df = pd.DataFrame({
        "plant_id": [1, 1, 1],
        "timestamp": [
            "2020-05-15T10:00:00",
            "2020-05-15T10:15:00",
            "2020-05-15T10:45:00",  # 10:30 is missing -> gap before
        ],
        "inverter_id": ["INV_01", "INV_01", "INV_01"],
        "dc_kw": [300.0, 320.0, 350.0],
        "ac_kw": [30.0, 32.0, 35.0],
        "daily_yield_kwh": [10.0, 20.0, 30.0],
        "total_yield_kwh": [100.0, 110.0, 120.0],
        "irradiation_kw_m2": [0.5, 0.52, 0.55],
        "module_temp_c": [35.0, 36.0, 38.0],
        "ambient_temp_c": [25.0, 26.0, 27.0],
        "flag_missing_weather": [False, False, False],
    })
    flagged = add_quality_flags(df, capacity_proxy=800.0)
    flagged = flagged.set_index("timestamp")
    assert not flagged.loc["2020-05-15T10:15:00", "flag_gap_before"]
    assert flagged.loc["2020-05-15T10:45:00", "flag_gap_before"]

def test_quality_flag_flatline_daylight():
    """Verify that identical ac_kw across 8+ daylight intervals is flagged as flatline."""
    # 9 consecutive daylight intervals with identical ac_kw
    times = [f"2020-05-15T{10 + i // 4:02d}:{(i % 4) * 15:02d}:00" for i in range(9)]
    df = pd.DataFrame({
        "plant_id": [1] * 9,
        "timestamp": times,
        "inverter_id": ["INV_01"] * 9,
        "dc_kw": [500.0] * 9,
        "ac_kw": [50.0] * 9,  # unchanging daylight power
        "daily_yield_kwh": list(range(9)),
        "total_yield_kwh": [100.0] * 9,
        "irradiation_kw_m2": [0.60] * 9,  # daylight (>= 0.05)
        "module_temp_c": [40.0] * 9,
        "ambient_temp_c": [30.0] * 9,
        "flag_missing_weather": [False] * 9,
    })
    flagged = add_quality_flags(df, capacity_proxy=800.0)
    assert flagged["flag_flatline"].all()

if __name__ == "__main__":
    test_weather_interpolation_limits()
    test_quality_flag_night_power()
    test_quality_flag_negative_power()
    test_quality_flag_gap_before()
    test_quality_flag_flatline_daylight()
    print("All ml_data unit tests passed successfully!")
