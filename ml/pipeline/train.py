"""Training, cross-validation, selection, and prediction generation pipeline.

Outputs:
- artifacts/models/plant{N}/<model>.joblib
- artifacts/models/selected.json
- artifacts/predictions/predictions_plant{N}.csv
- artifacts/metrics/model_metrics.json

Conforms strictly to:
- docs/DATA_AND_ML_SPEC.md sections 6 and 7
- docs/ARCHITECTURE_AND_API.md sections 3.2 and 3.5
- docs/DECISION_LOG.md (D-004, D-006, D-007)
"""

from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Dict, List
import joblib
import numpy as np
import pandas as pd

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.common.config import (
    METRICS_DIR,
    MODELS_DIR,
    NIGHT_G,
    PEER_HIGH,
    PEER_LOW,
    PREDICTIONS_DIR,
    PROCESSED_DIR,
    SEED,
)
from ml.features.build_features import compute_weather_features, FEATURE_COLUMNS
from ml.features.split import assign_split_column, compute_split_date_blocks, get_walk_forward_folds
from ml.models.baselines import PhysicsBaselineRegressor
from ml.models.evaluate import (
    compute_day_types,
    compute_permutation_importance,
    evaluate_by_irradiation_bins,
    evaluate_predictions,
    evaluate_plant_level_predictions,
)
from ml.models.regressors import HistGradientBoostingModel, RandomForestModel, RidgePolyModel

SIMPLICITY_ORDER = ["physics_baseline", "ridge_poly", "hist_gradient_boosting", "random_forest"]

def get_models_dict() -> Dict[str, Any]:
    return {
        "physics_baseline": PhysicsBaselineRegressor(),
        "ridge_poly": RidgePolyModel(alpha=10.0),
        "hist_gradient_boosting": HistGradientBoostingModel(learning_rate=0.08, max_iter=150, max_depth=8),
        "random_forest": RandomForestModel(n_estimators=100, max_depth=12, min_samples_leaf=5),
    }

def apply_robust_training_filter(df_train: pd.DataFrame, capacity_proxy: float) -> pd.DataFrame:
    """Drops training rows where inverter peer ratio is < 0.7 or > 1.3 to avoid dragging normal down.
    
    References: docs/DATA_AND_ML_SPEC.md section 7.
    """
    df = df_train.copy()
    sig_floor = 0.05 * capacity_proxy

    # Compute fleet median AC at each timestamp
    fleet_medians = df.groupby("timestamp")["ac_kw"].transform("median")
    eligible = fleet_medians >= sig_floor

    peer_ratio = df["ac_kw"] / fleet_medians
    # Drop rows that are strongly anomalous outliers during training
    drop_mask = eligible & ((peer_ratio < 0.70) | (peer_ratio > 1.30))
    kept = df[~drop_mask].copy()
    print(f"    Robust filter: dropped {drop_mask.sum()} outlier rows from {len(df)} training rows.")
    return kept

def train_and_evaluate_plant(
    plant_id: int,
    split_blocks: Dict[str, List[str]],
) -> Dict[str, Any]:
    print(f"\nTraining pipeline for Plant {plant_id}...")
    
    # 1. Load processed merged data
    csv_path = PROCESSED_DIR / f"merged_plant{plant_id}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Processed dataset not found: {csv_path}. Run build_dataset first.")
        
    df_merged = pd.read_csv(csv_path)

    # 2. Assign split blocks
    df_merged = assign_split_column(df_merged, split_blocks)

    # 3. Compute weather features on regular weather timestamps
    weather_unique = df_merged[["timestamp", "irradiation_kw_m2", "module_temp_c", "ambient_temp_c"]].drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    weather_feats = compute_weather_features(weather_unique)
    
    # Left join engineered features
    feat_cols_to_join = [c for c in weather_feats.columns if c not in ["irradiation_kw_m2", "module_temp_c", "ambient_temp_c"]]
    df_features = pd.merge(df_merged, weather_feats[feat_cols_to_join], on="timestamp", how="left")

    # Determine capacity proxy: 99th percentile of ac_kw on train daylight rows
    train_mask = df_features["split"] == "train"
    daylight_train = df_features[train_mask & (df_features["irradiation_kw_m2"] >= 0.05) & (~df_features["flag_any"])]
    capacity_proxy = float(np.percentile(daylight_train["ac_kw"], 99))
    print(f"  Capacity proxy: {capacity_proxy:.2f} kW")

    # 4. Prepare training set: daylight/positive irradiance, zero flags, weather present, robust filter
    train_eligible = df_features[
        train_mask &
        (df_features["irradiation_kw_m2"] >= NIGHT_G) &
        (~df_features["flag_any"]) &
        df_features["ac_kw"].notna()
    ].copy()

    train_robust = apply_robust_training_filter(train_eligible, capacity_proxy)

    X_train = train_robust[FEATURE_COLUMNS]
    y_train = train_robust["ac_kw"].values

    # 5. Fit all candidate models strictly on train rows
    models = get_models_dict()
    for name, model in models.items():
        print(f"  Fitting {name}...")
        model.fit(train_robust, y_train)

    # 6. Evaluate all candidate models on Validation block
    val_df = df_features[df_features["split"] == "val"].copy()
    test_df = df_features[df_features["split"] == "test"].copy()

    model_eval_records = []
    val_daylight_rmses = {}

    for name, model in models.items():
        val_preds = model.predict(val_df)
        val_df[f"pred_{name}"] = val_preds
        val_metrics = evaluate_predictions(val_df, f"pred_{name}", "ac_kw", capacity_proxy)
        val_plant_metrics = evaluate_plant_level_predictions(val_df, f"pred_{name}", "ac_kw", capacity_proxy)

        test_preds = model.predict(test_df)
        test_df[f"pred_{name}"] = test_preds
        test_metrics = evaluate_predictions(test_df, f"pred_{name}", "ac_kw", capacity_proxy)
        test_plant_metrics = evaluate_plant_level_predictions(test_df, f"pred_{name}", "ac_kw", capacity_proxy)

        val_rmse = val_metrics["daylight"]["rmse"]
        val_daylight_rmses[name] = val_rmse

        model_eval_records.append({
            "name": name,
            "val": val_metrics,
            "test": test_metrics,
            "plant_level": {
                "val": val_plant_metrics,
                "test": test_plant_metrics,
            },
        })
        print(f"    {name} -> Val Daylight RMSE: {val_rmse:.2f} kW | Test: {test_metrics['daylight']['rmse']:.2f} kW (Plant-level: {test_plant_metrics['daylight']['rmse']:.2f} kW)")

    # 7. Model Selection on Validation block with 3% parsimony rule
    best_model_name = min(val_daylight_rmses, key=val_daylight_rmses.get)
    best_rmse = val_daylight_rmses[best_model_name]
    threshold_3pct = best_rmse * 1.03

    selected_model_name = best_model_name
    selection_reason = f"lowest validation daylight RMSE ({best_rmse:.2f} kW)"

    # Check simpler models
    for simpler in SIMPLICITY_ORDER:
        if simpler == best_model_name:
            break
        if val_daylight_rmses[simpler] <= threshold_3pct:
            selected_model_name = simpler
            selection_reason = (
                f"{simpler} is within 3% of best ({val_daylight_rmses[simpler]:.2f} kW vs {best_rmse:.2f} kW); "
                f"simpler model preferred per spec section 6"
            )
            break

    print(f"  Selected model for Plant {plant_id}: {selected_model_name} ({selection_reason})")
    selected_model = models[selected_model_name]

    # Save fitted models to disk
    plant_model_dir = MODELS_DIR / f"plant{plant_id}"
    plant_model_dir.mkdir(parents=True, exist_ok=True)
    for name, model in models.items():
        joblib.dump(model, plant_model_dir / f"{name}.joblib")

    # 8. Walk-forward cross validation on train block
    train_dates = df_features[train_mask]["timestamp"].str[:10].unique().tolist()
    folds = get_walk_forward_folds(train_dates, fold_train_days=12, fold_test_days=3)
    wf_results = []
    
    for f in folds:
        f_train_mask = df_features["timestamp"].str[:10].isin(f["train_dates"]) & (df_features["irradiation_kw_m2"] >= NIGHT_G) & (~df_features["flag_any"])
        f_test_mask = df_features["timestamp"].str[:10].isin(f["test_dates"]) & (df_features["irradiation_kw_m2"] >= 0.05) & (~df_features["flag_any"])

        f_train_df = df_features[f_train_mask]
        f_test_df = df_features[f_test_mask]

        if len(f_train_df) > 50 and len(f_test_df) > 10:
            wf_model = get_models_dict()[selected_model_name]
            wf_model.fit(f_train_df, f_train_df["ac_kw"].values)
            wf_preds = wf_model.predict(f_test_df)
            f_rmse = float(np.sqrt(np.mean((f_test_df["ac_kw"].values - wf_preds) ** 2)))
            wf_results.append({
                "fold": f["fold"],
                "train_end": f["train_end"],
                "test_range": f["test_range"],
                "model": selected_model_name,
                "daylight_rmse": round(f_rmse, 2),
            })

    # 9. Test breakdowns: by irradiation bin and by day type
    test_df["pred_selected"] = selected_model.predict(test_df)
    by_irr_bin = evaluate_by_irradiation_bins(test_df, "pred_selected", "ac_kw", selected_model_name)

    day_types = compute_day_types(weather_unique)
    test_df["day_type"] = test_df["timestamp"].str[:10].map(day_types).fillna("mixed")
    
    by_day_type = []
    test_daylight = test_df[(test_df["irradiation_kw_m2"] >= 0.05) & (~test_df["flag_any"])]
    for dt_name in ["clear", "mixed", "cloudy"]:
        sub_dt = test_daylight[test_daylight["day_type"] == dt_name]
        mae = float(np.mean(np.abs(sub_dt["ac_kw"].values - sub_dt["pred_selected"].values))) if len(sub_dt) > 0 else 0.0
        by_day_type.append({"day_type": dt_name, "model": selected_model_name, "mae": round(mae, 2), "n": len(sub_dt)})

    # Permutation feature importance on validation rows
    val_daylight = val_df[(val_df["irradiation_kw_m2"] >= 0.05) & (~val_df["flag_any"])]
    feat_importance = compute_permutation_importance(
        selected_model,
        val_daylight[FEATURE_COLUMNS],
        val_daylight["ac_kw"].values,
    )

    # 10. Generate full predictions CSV (all rows in-sample for train, strictly out-of-sample for val and test)
    # Architecture 3.2 schema:
    # plant_id, timestamp, inverter_id, ac_kw_actual, ac_kw_pred, dc_kw_actual, irradiation_kw_m2, module_temp_c, ambient_temp_c, split, model_name, flag_any
    df_features["ac_kw_actual"] = df_features["ac_kw"]
    df_features["dc_kw_actual"] = df_features["dc_kw"]
    df_features["ac_kw_pred"] = selected_model.predict(df_features)

    # Missing weather rows get no prediction (NaN) per Spec section 4
    df_features.loc[df_features["flag_missing_weather"], "ac_kw_pred"] = np.nan
    df_features["model_name"] = selected_model_name

    pred_cols = [
        "plant_id",
        "timestamp",
        "inverter_id",
        "ac_kw_actual",
        "ac_kw_pred",
        "dc_kw_actual",
        "irradiation_kw_m2",
        "module_temp_c",
        "ambient_temp_c",
        "split",
        "model_name",
        "flag_any",
    ]
    df_predictions = df_features[pred_cols].sort_values(["timestamp", "inverter_id"]).copy()

    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    pred_csv_out = PREDICTIONS_DIR / f"predictions_plant{plant_id}.csv"
    df_predictions.to_csv(pred_csv_out, index=False)
    print(f"  Saved predictions to {pred_csv_out}")

    selected_record = next(m for m in model_eval_records if m["name"] == selected_model_name)
    return {
        "capacity_proxy_kw": round(capacity_proxy, 2),
        "selected_model": selected_model_name,
        "selection_reason": selection_reason,
        "models": model_eval_records,
        "plant_level": selected_record["plant_level"],
        "walk_forward": wf_results,
        "by_irradiation_bin": by_irr_bin,
        "by_day_type": by_day_type,
        "feature_importance": feat_importance,
    }

def run_training_pipeline():
    print("Starting ML training and evaluation pipeline...")
    
    # 1. Determine common split date blocks across plants (from merged_plant1 dates)
    p1_csv = PROCESSED_DIR / "merged_plant1.csv"
    if not p1_csv.exists():
        raise FileNotFoundError("Run 'python -m ml.pipeline.build_dataset' first.")
        
    df_p1 = pd.read_csv(p1_csv, usecols=["timestamp"])
    dates = df_p1["timestamp"].str[:10].unique().tolist()
    split_blocks = compute_split_date_blocks(dates)
    print(f"Chronological split blocks: Train: {split_blocks['train']} | Val: {split_blocks['val']} | Test: {split_blocks['test']}")

    plants_meta = {}
    selected_summary = {}

    for plant_id in [1, 2]:
        p_res = train_and_evaluate_plant(plant_id, split_blocks)
        plants_meta[str(plant_id)] = p_res
        selected_summary[str(plant_id)] = p_res["selected_model"]

    # Save selected.json
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODELS_DIR / "selected.json", "w", encoding="utf-8") as f:
        json.dump(selected_summary, f, indent=2)

    # Save model_metrics.json (Architecture 3.5 schema)
    metrics_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "split": split_blocks,
        "plants": plants_meta,
    }
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    metrics_path = METRICS_DIR / "model_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"\nAll models trained and evaluated successfully!")
    print(f"Metrics saved to {metrics_path}")

if __name__ == "__main__":
    run_training_pipeline()

