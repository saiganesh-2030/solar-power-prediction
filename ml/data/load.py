"""Data loading module for Kaggle solar generation and weather data.

References:
- docs/DATA_AND_ML_SPEC.md section 3
- docs/ARCHITECTURE_AND_API.md section 3.1
"""

from pathlib import Path
from typing import Optional
import pandas as pd

from ml.common.config import RAW_DATA_DIR

DATE_TIME_FORMAT_P1_GEN = "%d-%m-%Y %H:%M"
DATE_TIME_FORMAT_STANDARD = "%Y-%m-%d %H:%M:%S"

def load_generation_data(plant_id: int, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Loads and formats raw inverter generation CSV for a given plant.
    
    Plant 1 uses day-first formatting (%d-%m-%Y %H:%M).
    Plant 2 uses standard ISO-like formatting (%Y-%m-%d %H:%M:%S).
    """
    raw_dir = data_dir or RAW_DATA_DIR
    csv_path = raw_dir / f"Plant_{plant_id}_Generation_Data.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Generation CSV file not found: {csv_path}")

    fmt = DATE_TIME_FORMAT_P1_GEN if plant_id == 1 else DATE_TIME_FORMAT_STANDARD
    df = pd.read_csv(csv_path)

    # Explicit format parsing with strict zero-discrepancy assertion
    parsed = pd.to_datetime(df["DATE_TIME"], format=fmt, errors="coerce")
    if parsed.isna().any():
        n_bad = int(parsed.isna().sum())
        raise ValueError(f"Failed to parse {n_bad} timestamps in {csv_path.name} with format '{fmt}'")

    df["timestamp"] = parsed.dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Set plant_id to integer 1 or 2 per Architecture section 3 contract
    df["plant_id"] = plant_id

    # Rename to contract columns
    rename_map = {
        "SOURCE_KEY": "inverter_id",
        "DC_POWER": "dc_kw",
        "AC_POWER": "ac_kw",
        "DAILY_YIELD": "daily_yield_kwh",
        "TOTAL_YIELD": "total_yield_kwh",
    }
    df = df.rename(columns=rename_map)

    # Contract columns in canonical order
    target_cols = [
        "plant_id",
        "timestamp",
        "inverter_id",
        "dc_kw",
        "ac_kw",
        "daily_yield_kwh",
        "total_yield_kwh",
    ]
    df = df[target_cols]

    # Drop duplicate records
    df = df.drop_duplicates(subset=["plant_id", "timestamp", "inverter_id"]).copy()
    return df

def load_weather_data(plant_id: int, data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Loads and formats plant-level weather sensor data.
    
    Both plants use standard ISO-like formatting (%Y-%m-%d %H:%M:%S).
    Weather sensor SOURCE_KEY is dropped per Spec section 3.
    """
    raw_dir = data_dir or RAW_DATA_DIR
    csv_path = raw_dir / f"Plant_{plant_id}_Weather_Sensor_Data.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Weather sensor CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)

    parsed = pd.to_datetime(df["DATE_TIME"], format=DATE_TIME_FORMAT_STANDARD, errors="coerce")
    if parsed.isna().any():
        n_bad = int(parsed.isna().sum())
        raise ValueError(f"Failed to parse {n_bad} timestamps in {csv_path.name}")

    df["timestamp"] = parsed.dt.strftime("%Y-%m-%dT%H:%M:%S")

    df["plant_id"] = plant_id

    rename_map = {
        "AMBIENT_TEMPERATURE": "ambient_temp_c",
        "MODULE_TEMPERATURE": "module_temp_c",
        "IRRADIATION": "irradiation_kw_m2",
    }
    df = df.rename(columns=rename_map)

    target_cols = [
        "plant_id",
        "timestamp",
        "irradiation_kw_m2",
        "module_temp_c",
        "ambient_temp_c",
    ]
    df = df[target_cols]

    # Drop duplicate sensor readings at the same timestamp
    df = df.drop_duplicates(subset=["plant_id", "timestamp"]).copy()
    return df
