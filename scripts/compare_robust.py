import sys
from pathlib import Path
REPO_ROOT = Path("c:/Users/pandu/Desktop/project2/solar-power-prediction")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import numpy as np
from ml.common.config import PROCESSED_DIR, NIGHT_G
from ml.features.build_features import compute_weather_features, FEATURE_COLUMNS
from ml.features.split import assign_split_column, compute_split_date_blocks
from ml.models.baselines import PhysicsBaselineRegressor
from ml.models.regressors import RidgePolyModel, HistGradientBoostingModel, RandomForestModel
from ml.models.evaluate import evaluate_predictions
from ml.pipeline.train import apply_robust_training_filter

def run_comparison():
    print("Loading data...", flush=True)
    p1_csv = PROCESSED_DIR / "merged_plant1.csv"
    df_p1 = pd.read_csv(p1_csv, usecols=["timestamp"])
    dates = df_p1["timestamp"].str[:10].unique().tolist()
    split_blocks = compute_split_date_blocks(dates)

    results = []

    for plant_id in [1, 2]:
        print(f"\nProcessing Plant {plant_id}...", flush=True)
        csv_path = PROCESSED_DIR / f"merged_plant{plant_id}.csv"
        df_merged = pd.read_csv(csv_path)
        df_merged = assign_split_column(df_merged, split_blocks)

        weather_unique = df_merged[["timestamp", "irradiation_kw_m2", "module_temp_c", "ambient_temp_c"]].drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        weather_feats = compute_weather_features(weather_unique)
        feat_cols = [c for c in weather_feats.columns if c not in ["irradiation_kw_m2", "module_temp_c", "ambient_temp_c"]]
        df_features = pd.merge(df_merged, weather_feats[feat_cols], on="timestamp", how="left")

        train_mask = df_features["split"] == "train"
        daylight_train = df_features[train_mask & (df_features["irradiation_kw_m2"] >= 0.05) & (~df_features["flag_any"])]
        capacity_proxy = float(np.percentile(daylight_train["ac_kw"], 99))

        train_eligible = df_features[
            train_mask &
            (df_features["irradiation_kw_m2"] >= NIGHT_G) &
            (~df_features["flag_any"]) &
            df_features["ac_kw"].notna()
        ].copy()

        train_robust = apply_robust_training_filter(train_eligible, capacity_proxy)

        val_df = df_features[df_features["split"] == "val"].copy()
        test_df = df_features[df_features["split"] == "test"].copy()

        for robust_flag, train_set in [("OFF", train_eligible), ("ON", train_robust)]:
            print(f"  Evaluating with Robust = {robust_flag} ({len(train_set)} rows)...", flush=True)
            models = {
                "physics_baseline": PhysicsBaselineRegressor(),
                "ridge_poly": RidgePolyModel(alpha=10.0),
                "hist_gradient_boosting": HistGradientBoostingModel(learning_rate=0.08, max_iter=150, max_depth=8),
                "random_forest": RandomForestModel(n_estimators=60, max_depth=12, min_samples_leaf=5),
            }
            y_train = train_set["ac_kw"].values
            for name, model in models.items():
                print(f"    Fitting {name}...", flush=True)
                model.fit(train_set, y_train)
                val_df[f"pred_{name}"] = model.predict(val_df)
                test_df[f"pred_{name}"] = model.predict(test_df)

                val_m = evaluate_predictions(val_df, f"pred_{name}", "ac_kw", capacity_proxy)
                test_m = evaluate_predictions(test_df, f"pred_{name}", "ac_kw", capacity_proxy)

                results.append({
                    "plant_id": plant_id,
                    "robust": robust_flag,
                    "model": name,
                    "train_rows": len(train_set),
                    "val_daylight_rmse": val_m["daylight"]["rmse"],
                    "val_daylight_mae": val_m["daylight"]["mae"],
                    "val_daylight_r2": val_m["daylight"]["r2"],
                    "val_daylight_wape": val_m["daylight"]["wape"],
                    "test_daylight_rmse": test_m["daylight"]["rmse"],
                    "test_daylight_mae": test_m["daylight"]["mae"],
                    "test_daylight_r2": test_m["daylight"]["r2"],
                    "test_daylight_wape": test_m["daylight"]["wape"],
                })

    res_df = pd.DataFrame(results)
    print("\n=== SUMMARY COMPARISON ===", flush=True)
    print(res_df.to_string(), flush=True)
    out_csv = REPO_ROOT / "artifacts/metrics/robust_training_comparison.csv"
    res_df.to_csv(out_csv, index=False)
    print(f"Saved to {out_csv}", flush=True)

if __name__ == "__main__":
    run_comparison()
