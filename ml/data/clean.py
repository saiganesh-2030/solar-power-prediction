"""Weather cleaning, time-grid alignment, and generation joining.

References:
- docs/DATA_AND_ML_SPEC.md section 4
"""

import pandas as pd

def clean_weather_series(df_weather: pd.DataFrame, plant_id: int) -> pd.DataFrame:
    """Reindexes weather sensor data to a complete 15-minute grid and interpolates short gaps.
    
    Rules per Spec section 4:
    - Gaps of at most 2 intervals (30 min) are linearly interpolated.
    - Longer gaps remain empty (NaN) and are flagged with flag_missing_weather = True.
    """
    df = df_weather.copy()
    df["dt"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("dt").set_index("dt")

    # Complete 15-minute grid from earliest to latest reading
    full_grid = pd.date_range(start=df.index.min(), end=df.index.max(), freq="15min")
    reindexed = df.reindex(full_grid)
    reindexed["plant_id"] = plant_id
    reindexed["timestamp"] = reindexed.index.strftime("%Y-%m-%dT%H:%M:%S")

    weather_cols = ["irradiation_kw_m2", "module_temp_c", "ambient_temp_c"]

    # Linear interpolation with limit=2 (at most 2 intervals)
    interpolated = reindexed[weather_cols].interpolate(method="time", limit=2, limit_direction="forward")
    
    # flag_missing_weather = True if any weather column remains NaN
    reindexed["flag_missing_weather"] = interpolated["irradiation_kw_m2"].isna()
    
    # Copy back interpolated values
    reindexed[weather_cols] = interpolated

    reindexed = reindexed.reset_index(drop=True)
    cols = ["plant_id", "timestamp", "irradiation_kw_m2", "module_temp_c", "ambient_temp_c", "flag_missing_weather"]
    return reindexed[cols]

def join_generation_weather(df_gen: pd.DataFrame, df_weather: pd.DataFrame) -> pd.DataFrame:
    """Left-joins plant-level weather series onto inverter generation records.
    
    Preserves all generation rows (power is never dropped or forward-filled).
    """
    merged = pd.merge(
        df_gen,
        df_weather[["plant_id", "timestamp", "irradiation_kw_m2", "module_temp_c", "ambient_temp_c", "flag_missing_weather"]],
        on=["plant_id", "timestamp"],
        how="left",
    )
    # If weather was absent from the grid entirely, mark as missing weather
    merged["flag_missing_weather"] = merged["flag_missing_weather"].fillna(True).astype(bool)
    return merged

