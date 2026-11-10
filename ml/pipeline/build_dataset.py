"""Dataset building pipeline: loads, cleans, flags, and saves processed plant data.

Outputs:
- artifacts/processed/merged_plant1.csv
- artifacts/processed/merged_plant2.csv

Conforms strictly to docs/ARCHITECTURE_AND_API.md section 3.1.
References:
- docs/roles/ROLE_1_ML_ENGINEER.md Deliverable D2
- docs/DATA_AND_ML_SPEC.md sections 3 and 4
"""

import sys
from pathlib import Path
import pandas as pd

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.common.config import PROCESSED_DIR
from ml.data.clean import clean_weather_series, join_generation_weather
from ml.data.load import load_generation_data, load_weather_data
from ml.data.quality_flags import add_quality_flags

TARGET_COLUMNS = [
    "plant_id",
    "timestamp",
    "inverter_id",
    "dc_kw",
    "ac_kw",
    "daily_yield_kwh",
    "total_yield_kwh",
    "irradiation_kw_m2",
    "module_temp_c",
    "ambient_temp_c",
    "flag_missing_weather",
    "flag_night_power",
    "flag_flatline",
    "flag_negative",
    "flag_gap_before",
    "flag_ac_dc_inconsistent",
    "flag_any",
]

def build_dataset_for_plant(plant_id: int) -> pd.DataFrame:
    """Builds processed, quality-flagged dataset for one plant."""
    print(f"Building processed dataset for Plant {plant_id}...")
    
    # 1. Load raw data with explicit timestamp formats
    df_gen = load_generation_data(plant_id)
    df_wtr = load_weather_data(plant_id)
    print(f"  Loaded {len(df_gen)} generation rows and {len(df_wtr)} weather rows.")

    # 2. Clean weather series on 15-minute grid and join
    df_wtr_clean = clean_weather_series(df_wtr, plant_id)
    df_merged = join_generation_weather(df_gen, df_wtr_clean)
    print(f"  Joined dataset contains {len(df_merged)} rows.")

    # 3. Add quality flags
    df_flagged = add_quality_flags(df_merged)

    # 4. Enforce canonical contract columns and ordering
    df_final = df_flagged[TARGET_COLUMNS].copy()

    # Sort deterministically
    df_final = df_final.sort_values(["timestamp", "inverter_id"]).reset_index(drop=True)

    # Summary of flags
    clean_pct = round(float((~df_final["flag_any"]).mean() * 100), 2)
    print(f"  Quality check: {clean_pct}% rows have zero flags.")

    out_csv = PROCESSED_DIR / f"merged_plant{plant_id}.csv"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(out_csv, index=False)
    print(f"  Saved to {out_csv}")
    return df_final

def run_pipeline():
    """Main pipeline entry point."""
    print("Starting dataset build pipeline...")
    p1 = build_dataset_for_plant(1)
    p2 = build_dataset_for_plant(2)
    print(f"Pipeline complete: Plant 1 has {len(p1)} rows, Plant 2 has {len(p2)} rows.")

if __name__ == "__main__":
    run_pipeline()

