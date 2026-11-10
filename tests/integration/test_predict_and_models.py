"""Integration tests for Feature 2 (/predict, /predictions/timeseries) and Feature 6 (/models/*).

References:
- docs/roles/ROLE_1_ML_ENGINEER.md
- docs/PROJECT_HANDBOOK.md section 5 (Features 2 and 6)
- AGENTS.md section 4
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.routers.models import (
    get_feature_importance,
    get_model_performance,
    get_model_residuals,
    get_models,
)
from backend.app.routers.predict import get_timeseries, post_predict
from backend.app.schemas.predict import PredictRequest

BANNED_PATTERN = re.compile(r"\b(fault|failure|defective|malfunction)\b", re.IGNORECASE)

def test_predict_daylight():
    req = PredictRequest(
        plant=1,
        timestamp="2020-06-10T12:00:00",
        irradiation_kw_m2=0.85,
        module_temp_c=52.0,
        ambient_temp_c=33.0,
        model="selected",
    )
    res = post_predict(req)
    data = res.data

    assert data.ac_kw_per_inverter > 0.0
    assert data.interval_lo_kw <= data.ac_kw_per_inverter <= data.interval_hi_kw
    assert data.interval_lo_kw >= 0.0
    assert data.plant_ac_kw_estimate == round(data.ac_kw_per_inverter * 22, 2)
    assert data.interval_coverage == 0.90
    assert len(data.model_name) > 0

    # Language check
    assert BANNED_PATTERN.search(res.model_dump_json()) is None
    print(f"✓ test_predict_daylight passed (Predicted: {data.ac_kw_per_inverter} kW, Band: [{data.interval_lo_kw}, {data.interval_hi_kw}])")

def test_predict_night():
    req = PredictRequest(
        plant=1,
        timestamp="2020-06-10T01:00:00",
        irradiation_kw_m2=0.0,
        module_temp_c=22.0,
        ambient_temp_c=20.0,
        model="selected",
    )
    res = post_predict(req)
    assert res.data.ac_kw_per_inverter == 0.0
    assert res.data.interval_lo_kw == 0.0
    assert any("Night conditions" in w for w in res.data.warnings)
    print("✓ test_predict_night passed (Night generation is 0.0 kW)")

def test_predictions_timeseries():
    res = get_timeseries(plant=1, split="test")
    data = res.data
    assert len(data.t) > 0
    assert len(data.t) == len(data.actual_kw) == len(data.pred_kw)
    assert BANNED_PATTERN.search(res.model_dump_json()) is None
    print(f"✓ test_predictions_timeseries passed ({len(data.t)} series points)")

def test_models_list():
    res = get_models(plant=1)
    models = res.data
    assert len(models) == 4
    selected = [m for m in models if m.is_selected]
    assert len(selected) == 1
    assert BANNED_PATTERN.search(res.model_dump_json()) is None
    print(f"✓ test_models_list passed (Selected model: {selected[0].name})")

def test_model_performance():
    res = get_model_performance(plant=1)
    data = res.data
    assert data.capacity_proxy_kw > 0
    assert len(data.models) == 4
    assert len(data.by_irradiation_bin) == 5
    assert len(data.by_day_type) >= 2
    # Verify plant_level key is present per DATA_AND_ML_SPEC.md section 7 & Architecture 3.5
    for m in data.models:
        assert "plant_level" in m
        assert "val" in m["plant_level"] and "test" in m["plant_level"]
    assert BANNED_PATTERN.search(res.model_dump_json()) is None
    print("✓ test_model_performance passed (includes plant_level metrics across all models)")

def test_model_residuals():
    res = get_model_residuals(plant=1, split="test")
    data = res.data
    assert len(data.histogram) > 0
    assert len(data.sample_points) > 0
    assert BANNED_PATTERN.search(res.model_dump_json()) is None
    print(f"✓ test_model_residuals passed (Mean residual: {data.mean_residual_kw} kW, Std: {data.std_residual_kw} kW)")

def test_feature_importance():
    res = get_feature_importance(plant=1)
    items = res.data
    assert len(items) > 0
    # Top feature is solar irradiation
    assert items[0].feature == "irradiation_kw_m2"
    assert items[0].importance > 0.4
    # Plain-language explanation check
    assert items[0].explanation is not None and len(items[0].explanation) > 10
    assert BANNED_PATTERN.search(res.model_dump_json()) is None
    print(f"✓ test_feature_importance passed (Top feature: {items[0].feature} with {items[0].importance:.1%}, explanation present)")

if __name__ == "__main__":
    test_predict_daylight()
    test_predict_night()
    test_predictions_timeseries()
    test_models_list()
    test_model_performance()
    test_model_residuals()
    test_feature_importance()
    print("All predict & models integration tests passed successfully!")

