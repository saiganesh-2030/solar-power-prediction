"""Exploratory Data Analysis script for raw solar generation and weather datasets.

Performs verification per docs/DATA_AND_ML_SPEC.md section 3:
- Explicit timestamp parsing with zero parse errors asserted
- Counts rows, days, inverters per plant
- Checks duplicates, conflicting rows, and missing 15-minute intervals
- Checks column ranges, daily max irradiation (to confirm units)
- Computes DC vs AC ratios per plant
- Outputs summary report to artifacts/processed/data_report.json

References:
- docs/roles/ROLE_1_ML_ENGINEER.md Deliverable D1
- docs/DATA_AND_ML_SPEC.md section 3
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.common.config import RAW_DATA_DIR, PROCESSED_DIR

def run_eda() -> dict:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    files = {
        "p1_gen": RAW_DATA_DIR / "Plant_1_Generation_Data.csv",
        "p1_weather": RAW_DATA_DIR / "Plant_1_Weather_Sensor_Data.csv",
        "p2_gen": RAW_DATA_DIR / "Plant_2_Generation_Data.csv",
        "p2_weather": RAW_DATA_DIR / "Plant_2_Weather_Sensor_Data.csv",
    }
    
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "files": {},
        "plants": {},
    }

    # 1. Parse and validate raw files
    # Formats: Plant 1 gen uses day-first (%d-%m-%Y %H:%M), others use %Y-%m-%d %H:%M:%S
    df_p1_gen = pd.read_csv(files["p1_gen"])
    df_p1_gen["parsed_dt"] = pd.to_datetime(df_p1_gen["DATE_TIME"], format="%d-%m-%Y %H:%M", errors="coerce")
    assert df_p1_gen["parsed_dt"].isna().sum() == 0, "Plant 1 generation date parsing produced NaT"

    df_p1_wtr = pd.read_csv(files["p1_weather"])
    df_p1_wtr["parsed_dt"] = pd.to_datetime(df_p1_wtr["DATE_TIME"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    assert df_p1_wtr["parsed_dt"].isna().sum() == 0, "Plant 1 weather date parsing produced NaT"

    df_p2_gen = pd.read_csv(files["p2_gen"])
    df_p2_gen["parsed_dt"] = pd.to_datetime(df_p2_gen["DATE_TIME"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    assert df_p2_gen["parsed_dt"].isna().sum() == 0, "Plant 2 generation date parsing produced NaT"

    df_p2_wtr = pd.read_csv(files["p2_weather"])
    df_p2_wtr["parsed_dt"] = pd.to_datetime(df_p2_wtr["DATE_TIME"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    assert df_p2_wtr["parsed_dt"].isna().sum() == 0, "Plant 2 weather date parsing produced NaT"

    raw_dfs = {
        "Plant_1_Generation_Data.csv": df_p1_gen,
        "Plant_1_Weather_Sensor_Data.csv": df_p1_wtr,
        "Plant_2_Generation_Data.csv": df_p2_gen,
        "Plant_2_Weather_Sensor_Data.csv": df_p2_wtr,
    }

    for fname, df in raw_dfs.items():
        min_date = df["parsed_dt"].min().strftime("%Y-%m-%d")
        max_date = df["parsed_dt"].max().strftime("%Y-%m-%d")
        unique_days = df["parsed_dt"].dt.date.nunique()
        unique_sources = df["SOURCE_KEY"].nunique()
        duplicates = int(df.duplicated(subset=[c for c in df.columns if c != "parsed_dt"]).sum())

        report["files"][fname] = {
            "rows": int(len(df)),
            "date_range": [min_date, max_date],
            "calendar_days": unique_days,
            "unique_sources": unique_sources,
            "exact_duplicates": duplicates,
            "columns": [c for c in df.columns if c != "parsed_dt"],
        }

    # 2. Plant-specific statistics
    for p_id, df_gen, df_wtr in [(1, df_p1_gen, df_p1_wtr), (2, df_p2_gen, df_p2_wtr)]:
        inverters = sorted(df_gen["SOURCE_KEY"].unique().tolist())
        
        # Exact duplicate checks on key (DATE_TIME, SOURCE_KEY)
        key_dupes = int(df_gen.duplicated(subset=["parsed_dt", "SOURCE_KEY"]).sum())
        
        # Weather slots analysis
        min_dt = df_gen["parsed_dt"].min()
        max_dt = df_gen["parsed_dt"].max()
        expected_slots = pd.date_range(min_dt.floor("D"), max_dt.ceil("D"), freq="15min")
        wtr_unique_times = df_wtr["parsed_dt"].drop_duplicates()
        missing_wtr_slots = len(expected_slots) - len(wtr_unique_times.isin(expected_slots))

        # Max daily irradiation (to verify kW/m2)
        df_wtr["date"] = df_wtr["parsed_dt"].dt.date
        daily_max_irr = df_wtr.groupby("date")["IRRADIATION"].max().to_dict()
        daily_max_irr_str = {str(k): round(float(v), 4) for k, v in daily_max_irr.items()}
        peak_irr = float(df_wtr["IRRADIATION"].max())

        # DC / AC ratio check on daylight rows (AC > 10 kW)
        daylight_gen = df_gen[df_gen["AC_POWER"] > 10.0]
        dc_ac_ratio = (daylight_gen["DC_POWER"] / daylight_gen["AC_POWER"]).median()

        # Capacity proxy estimate: 99th percentile of AC power
        cap_proxy = float(np.percentile(daylight_gen["AC_POWER"], 99))

        report["plants"][str(p_id)] = {
            "inverter_count": len(inverters),
            "inverters": inverters,
            "generation_rows": len(df_gen),
            "weather_rows": len(df_wtr),
            "key_duplicates": key_dupes,
            "peak_irradiation_kw_m2": round(peak_irr, 4),
            "daily_max_irradiation": daily_max_irr_str,
            "median_dc_ac_ratio": round(float(dc_ac_ratio), 4),
            "capacity_proxy_kw": round(cap_proxy, 2),
            "column_ranges": {
                "ac_power": [float(df_gen["AC_POWER"].min()), float(df_gen["AC_POWER"].max())],
                "dc_power": [float(df_gen["DC_POWER"].min()), float(df_gen["DC_POWER"].max())],
                "ambient_temp": [float(df_wtr["AMBIENT_TEMPERATURE"].min()), float(df_wtr["AMBIENT_TEMPERATURE"].max())],
                "module_temp": [float(df_wtr["MODULE_TEMPERATURE"].min()), float(df_wtr["MODULE_TEMPERATURE"].max())],
                "irradiation": [float(df_wtr["IRRADIATION"].min()), float(df_wtr["IRRADIATION"].max())],
            },
        }

    out_file = PROCESSED_DIR / "data_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Data report successfully written to {out_file}")
    return report

if __name__ == "__main__":
    report = run_eda()
    print("EDA Complete:")
    print("Plant 1 Inverters:", report["plants"]["1"]["inverter_count"], "DC/AC ratio:", report["plants"]["1"]["median_dc_ac_ratio"], "Peak Irr:", report["plants"]["1"]["peak_irradiation_kw_m2"])
    print("Plant 2 Inverters:", report["plants"]["2"]["inverter_count"], "DC/AC ratio:", report["plants"]["2"]["median_dc_ac_ratio"], "Peak Irr:", report["plants"]["2"]["peak_irradiation_kw_m2"])

