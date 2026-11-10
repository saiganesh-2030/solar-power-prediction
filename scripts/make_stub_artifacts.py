"""Generates synthetic stub artifacts for local development without raw data.

Follows the schemas defined in docs/ARCHITECTURE_AND_API.md section 3.
Covers both plants (1 and 2), 22 inverters per plant, and creates plausible
bell-shaped generation profiles with synthetic deviation events across all categories.

Seed: 42 (fixed per AGENTS.md).
"""

import json
import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd

from ml.common.config import (
    APPROVED_CATEGORIES,
    APPROVED_CONFIDENCE_LEVELS,
    APPROVED_DIRECTIONS,
    APPROVED_SEVERITIES,
    INTERVAL_H,
    SEED,
    STUB_DIR,
)

def make_stubs(out_dir: Path | None = None, n_days: int = 14):
    random.seed(SEED)
    np.random.seed(SEED)
    
    target_dir = out_dir or STUB_DIR
    processed_dir = target_dir / "processed"
    pred_dir = target_dir / "predictions"
    anomaly_dir = target_dir / "anomalies"
    metrics_dir = target_dir / "metrics"
    
    for d in [processed_dir, pred_dir, anomaly_dir, metrics_dir]:
        d.mkdir(parents=True, exist_ok=True)

    start_date = datetime(2020, 5, 15, 0, 0, 0)
    timestamps = [start_date + timedelta(minutes=15 * i) for i in range(n_days * 96)]
    
    train_end_idx = int(0.70 * len(timestamps))
    val_end_idx = int(0.85 * len(timestamps))
    
    split_dates = {
        "train": [timestamps[0].strftime("%Y-%m-%d"), timestamps[train_end_idx - 1].strftime("%Y-%m-%d")],
        "val": [timestamps[train_end_idx].strftime("%Y-%m-%d"), timestamps[val_end_idx - 1].strftime("%Y-%m-%d")],
        "test": [timestamps[val_end_idx].strftime("%Y-%m-%d"), timestamps[-1].strftime("%Y-%m-%d")],
    }

    for plant_id in [1, 2]:
        inverters = [f"INV_{plant_id}_{i:02d}" for i in range(1, 23)]
        
        merged_rows = []
        pred_rows = []
        point_flag_rows = []
        
        for t_idx, dt in enumerate(timestamps):
            t_str = dt.isoformat()
            date_str = dt.strftime("%Y-%m-%d")
            minute_of_day = dt.hour * 60 + dt.minute
            
            # Sun profile (approx 06:00 to 18:30)
            if 360 <= minute_of_day <= 1110:
                rad = math.sin((minute_of_day - 360) / 750 * math.pi)
                irr = max(0.0, rad * 1.05 + random.gauss(0, 0.03))
                ambient = 25.0 + 12.0 * rad + random.gauss(0, 0.5)
                module = ambient + irr * 28.0 + random.gauss(0, 1.0)
            else:
                irr = 0.0
                ambient = 22.0 + random.gauss(0, 0.5)
                module = ambient

            irr = round(max(0.0, irr), 4)
            ambient = round(ambient, 2)
            module = round(module, 2)

            if t_idx < train_end_idx:
                row_split = "train"
            elif t_idx < val_end_idx:
                row_split = "val"
            else:
                row_split = "test"

            # Synthetic fleet behavior per inverter
            for inv_idx, inv_id in enumerate(inverters):
                base_kw = irr * 850.0  # ~850 kW max capacity per inverter
                efficiency = 0.95 - (inv_idx % 5) * 0.01
                pred_kw = round(max(0.0, base_kw * 0.94), 2)
                
                # Synthetic variation/deviation
                actual_kw = round(max(0.0, base_kw * efficiency + random.gauss(0, 10.0)), 2)
                if irr < 0.01:
                    actual_kw = 0.0
                    pred_kw = 0.0

                dc_kw = actual_kw * (10.0 if plant_id == 1 else 1.02)
                residual = round(actual_kw - pred_kw, 2)
                rel_dev = round(residual / max(pred_kw, 40.0), 4)
                band_lo = round(max(0.0, pred_kw * 0.88), 2)
                band_hi = round(pred_kw * 1.12, 2)
                is_outlier = bool(actual_kw < band_lo or actual_kw > band_hi) if irr >= 0.05 else False

                merged_rows.append({
                    "plant_id": plant_id,
                    "timestamp": t_str,
                    "inverter_id": inv_id,
                    "dc_kw": round(dc_kw, 2),
                    "ac_kw": actual_kw,
                    "daily_yield_kwh": round(actual_kw * 0.25 * (dt.hour + 1), 2),
                    "total_yield_kwh": 100000.0,
                    "irradiation_kw_m2": irr,
                    "module_temp_c": module,
                    "ambient_temp_c": ambient,
                    "flag_missing_weather": False,
                    "flag_night_power": False,
                    "flag_flatline": False,
                    "flag_negative": False,
                    "flag_gap_before": False,
                    "flag_ac_dc_inconsistent": False,
                    "flag_any": False,
                })

                pred_rows.append({
                    "plant_id": plant_id,
                    "timestamp": t_str,
                    "inverter_id": inv_id,
                    "ac_kw_actual": actual_kw,
                    "ac_kw_pred": pred_kw,
                    "dc_kw_actual": round(dc_kw, 2),
                    "irradiation_kw_m2": irr,
                    "module_temp_c": module,
                    "ambient_temp_c": ambient,
                    "split": row_split,
                    "model_name": "hist_gradient_boosting",
                    "flag_any": False,
                })

                point_flag_rows.append({
                    "plant_id": plant_id,
                    "timestamp": t_str,
                    "inverter_id": inv_id,
                    "residual_kw": residual,
                    "rel_dev": rel_dev,
                    "band_lo_kw": band_lo,
                    "band_hi_kw": band_hi,
                    "z_robust": round(residual / 15.0, 3),
                    "is_outlier": is_outlier,
                    "event_id": "",
                })

        # Save processed and predictions
        pd.DataFrame(merged_rows).to_csv(processed_dir / f"merged_plant{plant_id}.csv", index=False)
        pd.DataFrame(pred_rows).to_csv(pred_dir / f"predictions_plant{plant_id}.csv", index=False)
        pd.DataFrame(point_flag_rows).to_csv(anomaly_dir / f"point_flags_plant{plant_id}.csv", index=False)

        # Synthetic deviation events covering all categories
        events = []
        cat_confirm_map = {
            "inverter_specific": "maintenance_log;alarm_codes;site_inspection",
            "weather_transient": "co_located_second_irradiance_sensor;satellite_cloud_data",
            "fleet_wide": "grid_outage_or_curtailment_records;sensor_calibration_record",
            "data_quality": "scada_communication_log;sensor_calibration_record",
            "unexplained": "maintenance_log;site_inspection",
        }
        
        for e_i in range(1, 16):
            cat = APPROVED_CATEGORIES[(e_i - 1) % len(APPROVED_CATEGORIES)]
            inv = "FLEET" if cat == "fleet_wide" else inverters[e_i % len(inverters)]
            day_offset = (e_i * 2) % n_days
            event_dt = start_date + timedelta(days=day_offset, hours=10 + (e_i % 4))
            start_iso = event_dt.isoformat()
            end_iso = (event_dt + timedelta(minutes=45 + 15 * (e_i % 3))).isoformat()
            duration_min = 45 + 15 * (e_i % 3)
            delta_kwh = -round(random.uniform(50.0, 350.0), 2)
            
            events.append({
                "event_id": f"P{plant_id}-E{e_i:04d}",
                "plant_id": plant_id,
                "inverter_id": inv,
                "start": start_iso,
                "end": end_iso,
                "duration_min": duration_min,
                "direction": "shortfall",
                "energy_delta_kwh": delta_kwh,
                "energy_vs_band_kwh": round(delta_kwh * 0.65, 2),
                "mean_rel_dev": -0.25,
                "peak_rel_dev": -0.42,
                "severity": APPROVED_SEVERITIES[e_i % 3],
                "category": cat,
                "confidence": APPROVED_CONFIDENCE_LEVELS[e_i % 3],
                "evidence_json": json.dumps({"peer_ratio": 0.72, "fleet_residual": 5.2}),
                "confirm_with": cat_confirm_map.get(cat, "site_inspection"),
                "split": "test" if day_offset >= 11 else ("val" if day_offset >= 9 else "train"),
            })
        pd.DataFrame(events).to_csv(anomaly_dir / f"events_plant{plant_id}.csv", index=False)

        # Band parameters JSON
        band_params = {
            "plant_id": plant_id,
            "coverage": 0.99,
            "bins": [
                {"bin": i, "pred_min": i * 100, "pred_max": (i + 1) * 100, "q_b": 25.0 + i * 4.0, "mad_b": 12.0}
                for i in range(8)
            ],
        }
        with open(anomaly_dir / f"band_params_plant{plant_id}.json", "w", encoding="utf-8") as f:
            json.dump(band_params, f, indent=2)

    # Global model metrics JSON
    metrics_data = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "seed": SEED,
        "split": split_dates,
        "plants": {
            str(p): {
                "capacity_proxy_kw": 850.0,
                "selected_model": "hist_gradient_boosting",
                "selection_reason": "lowest validation daylight RMSE; within 3% parsimony window",
                "models": [
                    {
                        "name": "physics_baseline",
                        "val": {
                            "all": {"mae": 32.5, "rmse": 48.2, "r2": 0.88},
                            "daylight": {"mae": 28.1, "rmse": 41.3, "r2": 0.89, "wape": 0.082, "nmae": 0.033},
                        },
                        "test": {
                            "all": {"mae": 33.1, "rmse": 49.0, "r2": 0.87},
                            "daylight": {"mae": 29.0, "rmse": 42.1, "r2": 0.88, "wape": 0.084, "nmae": 0.034},
                        },
                    },
                    {
                        "name": "hist_gradient_boosting",
                        "val": {
                            "all": {"mae": 18.2, "rmse": 27.4, "r2": 0.95},
                            "daylight": {"mae": 15.6, "rmse": 23.1, "r2": 0.96, "wape": 0.045, "nmae": 0.018},
                        },
                        "test": {
                            "all": {"mae": 19.1, "rmse": 28.5, "r2": 0.94},
                            "daylight": {"mae": 16.3, "rmse": 24.2, "r2": 0.95, "wape": 0.047, "nmae": 0.019},
                        },
                    },
                ],
                "walk_forward": [
                    {"fold": 1, "train_end": "2020-05-24", "test_range": ["2020-05-25", "2020-05-27"], "model": "hist_gradient_boosting", "daylight_rmse": 23.8},
                    {"fold": 2, "train_end": "2020-05-27", "test_range": ["2020-05-28", "2020-05-30"], "model": "hist_gradient_boosting", "daylight_rmse": 24.1},
                ],
                "by_irradiation_bin": [
                    {"bin": "0.05-0.2", "model": "hist_gradient_boosting", "mae": 8.5, "n": 420},
                    {"bin": "0.2-0.4", "model": "hist_gradient_boosting", "mae": 14.2, "n": 580},
                    {"bin": "0.4-0.6", "model": "hist_gradient_boosting", "mae": 18.1, "n": 610},
                    {"bin": "0.6-0.8", "model": "hist_gradient_boosting", "mae": 22.4, "n": 590},
                    {"bin": "0.8+", "model": "hist_gradient_boosting", "mae": 25.0, "n": 450},
                ],
                "by_day_type": [
                    {"day_type": "clear", "model": "hist_gradient_boosting", "mae": 14.1, "n": 1800},
                    {"day_type": "cloudy", "model": "hist_gradient_boosting", "mae": 22.5, "n": 850},
                ],
                "feature_importance": [
                    {"feature": "irradiation_kw_m2", "importance": 0.78},
                    {"feature": "module_temp_c", "importance": 0.12},
                    {"feature": "ambient_temp_c", "importance": 0.04},
                    {"feature": "hour_sin", "importance": 0.03},
                    {"feature": "hour_cos", "importance": 0.03},
                ],
            }
            for p in [1, 2]
        },
    }
    with open(metrics_dir / "model_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    # Injection benchmark JSON
    benchmark_data = {
        "plants": {
            str(p): {
                "scenarios": [
                    {"type": "drop_20pct_2h", "n_injected": 30, "recall": 0.933, "precision": 0.903, "median_detection_delay_min": 45},
                    {"type": "spike_plus_30pct_1h", "n_injected": 30, "recall": 0.967, "precision": 0.935, "median_detection_delay_min": 30},
                    {"type": "flatline_2h", "n_injected": 30, "recall": 0.900, "precision": 0.871, "median_detection_delay_min": 45},
                ]
            }
            for p in [1, 2]
        }
    }
    with open(anomaly_dir / "injection_benchmark.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"Successfully generated stub artifacts in {target_dir}")

if __name__ == "__main__":
    make_stubs()
