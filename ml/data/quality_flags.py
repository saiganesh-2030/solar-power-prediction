"""Data quality flag computation module.

Computes the 6 standard quality flags and the composite flag_any
per docs/DATA_AND_ML_SPEC.md section 4 and docs/ARCHITECTURE_AND_API.md section 3.1.
"""

from typing import Optional
import numpy as np
import pandas as pd

from ml.common.config import (
    DAYLIGHT_G,
    FLATLINE_INTERVALS,
    NIGHT_G,
    TRAIN_FRAC,
)

def compute_capacity_proxy(df: pd.DataFrame) -> float:
    """Computes plant capacity proxy: 99th percentile of ac_kw on train daylight rows.
    
    If split dates are not present, uses the first 70% of chronological calendar days.
    """
    df_sorted = df.copy()
    df_sorted["date"] = df_sorted["timestamp"].str[:10]
    unique_dates = sorted(df_sorted["date"].unique())
    n_train = max(1, int(len(unique_dates) * TRAIN_FRAC))
    train_dates = set(unique_dates[:n_train])

    train_mask = df_sorted["date"].isin(train_dates)
    daylight_mask = df_sorted["irradiation_kw_m2"] >= DAYLIGHT_G
    eligible = df_sorted[train_mask & daylight_mask & df_sorted["ac_kw"].notna()]

    if eligible.empty:
        # Fallback to all daylight rows if train block is somehow empty
        eligible = df_sorted[daylight_mask & df_sorted["ac_kw"].notna()]

    if eligible.empty or len(eligible) < 10:
        return 850.0  # sensible fallback

    capacity_proxy = float(np.percentile(eligible["ac_kw"], 99))
    return max(1.0, capacity_proxy)

def add_quality_flags(df: pd.DataFrame, capacity_proxy: Optional[float] = None) -> pd.DataFrame:
    """Computes all 6 quality flags plus flag_any on joined generation and weather data.
    
    Columns produced:
    - flag_missing_weather: bool
    - flag_night_power: bool
    - flag_flatline: bool
    - flag_negative: bool
    - flag_gap_before: bool
    - flag_ac_dc_inconsistent: bool
    - flag_any: bool
    """
    out = df.copy()
    cap = capacity_proxy if capacity_proxy is not None else compute_capacity_proxy(out)

    # 1. flag_missing_weather
    if "flag_missing_weather" not in out.columns:
        out["flag_missing_weather"] = out["irradiation_kw_m2"].isna()
    else:
        out["flag_missing_weather"] = out["flag_missing_weather"].fillna(True).astype(bool)

    # 2. flag_night_power: irradiation < 0.01 and ac_kw > 0.5% of capacity proxy
    night_irr = out["irradiation_kw_m2"] < NIGHT_G
    sig_power = out["ac_kw"] > (0.005 * cap)
    out["flag_night_power"] = (night_irr & sig_power).fillna(False).astype(bool)

    # 3. flag_negative: ac_kw < 0 or dc_kw < 0
    neg_ac = out["ac_kw"] < 0
    neg_dc = out["dc_kw"] < 0
    out["flag_negative"] = (neg_ac | neg_dc).fillna(False).astype(bool)

    # Sort deterministically by inverter and time for sequence checks
    out["_dt"] = pd.to_datetime(out["timestamp"])
    out = out.sort_values(["inverter_id", "_dt"]).reset_index(drop=True)

    # 4. flag_gap_before: previous 15-minute interval for this inverter is missing
    prev_dt = out.groupby("inverter_id")["_dt"].shift(1)
    # A gap occurs if difference to previous reading is not exactly 15 minutes (ignoring the very first row)
    time_diff = out["_dt"] - prev_dt
    is_gap = (time_diff != pd.Timedelta(minutes=15)) & prev_dt.notna()
    out["flag_gap_before"] = is_gap.fillna(False).astype(bool)

    # 5. flag_flatline: identical ac_kw for 8 or more consecutive daylight intervals
    # Only applies to daylight rows (irradiation >= 0.05 kW/m2)
    is_daylight = (out["irradiation_kw_m2"] >= DAYLIGHT_G) & out["ac_kw"].notna()
    
    # We detect daylight runs where ac_kw does not change
    out["flag_flatline"] = False
    for _, group_idx in out.groupby("inverter_id").groups.items():
        sub = out.loc[group_idx]
        sub_daylight = sub[is_daylight.loc[group_idx]]
        if len(sub_daylight) >= FLATLINE_INTERVALS:
            # Check diff in ac_kw on consecutive daylight rows
            val_diff = sub_daylight["ac_kw"].diff().ne(0)
            time_gap = sub_daylight["_dt"].diff().ne(pd.Timedelta(minutes=15))
            # New run starts if value changed OR there was a time gap
            run_id = (val_diff | time_gap).cumsum()
            run_lengths = run_id.map(run_id.value_counts())
            flatline_mask = run_lengths >= FLATLINE_INTERVALS
            flatline_indices = sub_daylight.index[flatline_mask]
            out.loc[flatline_indices, "flag_flatline"] = True

    # 6. flag_ac_dc_inconsistent:
    # Compute dc_ac_ratio for ac_kw >= 5% of capacity proxy
    # Compare with inverter's own median ratio; flag where AC > DC (normalized) by > 5%
    sig_ac_mask = out["ac_kw"] >= (0.05 * cap)
    valid_dc = out["dc_kw"] > 0
    ratio_eligible = sig_ac_mask & valid_dc

    out["flag_ac_dc_inconsistent"] = False
    
    # Calculate median ratio per inverter on eligible rows
    ratios = out.loc[ratio_eligible, "dc_kw"] / out.loc[ratio_eligible, "ac_kw"]
    out["_ratio"] = np.nan
    out.loc[ratio_eligible, "_ratio"] = ratios
    
    median_ratios = out.groupby("inverter_id")["_ratio"].transform("median")
    
    # Where AC exceeds DC after normalization by more than 5%:
    # normalized_dc = dc_kw / median_ratio
    # condition: ac_kw > (normalized_dc * 1.05) => ac_kw * median_ratio > dc_kw * 1.05
    has_median = median_ratios.notna() & (median_ratios > 0)
    inconsistent_mask = (
        sig_ac_mask &
        has_median &
        ((out["ac_kw"] * median_ratios) > (out["dc_kw"] * 1.05))
    )
    # Also flag if ac_kw is significant but dc_kw is 0 or negative
    zero_dc_mask = sig_ac_mask & (out["dc_kw"] <= 0)
    out["flag_ac_dc_inconsistent"] = (inconsistent_mask | zero_dc_mask).fillna(False).astype(bool)

    # 7. flag_any: OR of all 6 flags
    flag_cols = [
        "flag_missing_weather",
        "flag_night_power",
        "flag_flatline",
        "flag_negative",
        "flag_gap_before",
        "flag_ac_dc_inconsistent",
    ]
    out["flag_any"] = out[flag_cols].any(axis=1)

    # Clean up temporary columns
    out = out.drop(columns=["_dt", "_ratio"], errors="ignore")
    return out

