"""Runs all unit and integration tests across the project.

Verifies:
- Data pipeline, cleaning, and quality flags
- Feature engineering, leakage guard, and chronological splits
- Split-conformal calibration and prediction intervals
- API contracts: /health, /meta, /dashboard/overview, /predict, /models/*
- Strict vocabulary policy guardrails
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.unit.ml_data.test_data_pipeline import (
    test_weather_interpolation_limits,
    test_quality_flag_night_power,
    test_quality_flag_negative_power,
    test_quality_flag_gap_before,
    test_quality_flag_flatline_daylight,
)
from tests.unit.test_features_and_split import (
    test_no_leakage_in_features,
    test_chronological_splits,
    test_walk_forward_folds_inside_train,
    test_trailing_window_no_future_leakage,
)
from tests.unit.test_conformal import test_conformal_calibration_and_coverage
from tests.integration.test_health_meta import test_health, test_meta, test_dashboard
from tests.integration.test_predict_and_models import (
    test_predict_daylight,
    test_predict_night,
    test_predictions_timeseries,
    test_models_list,
    test_model_performance,
    test_model_residuals,
    test_feature_importance,
)
from tests.integration.test_banned_vocabulary import test_no_banned_vocabulary

def run_suite():
    print("=" * 60)
    print("RUNNING ROLE 1 & PLATFORM VERIFICATION TEST SUITE")
    print("=" * 60)

    print("\n1. Data Pipeline & Quality Flags:")
    test_weather_interpolation_limits()
    test_quality_flag_night_power()
    test_quality_flag_negative_power()
    test_quality_flag_gap_before()
    test_quality_flag_flatline_daylight()

    print("\n2. Feature Engineering & Chronological Split:")
    test_no_leakage_in_features()
    test_chronological_splits()
    test_walk_forward_folds_inside_train()
    test_trailing_window_no_future_leakage()

    print("\n3. Split-Conformal Calibration:")
    test_conformal_calibration_and_coverage()

    print("\n4. Core & Dashboard Endpoints:")
    test_health()
    test_meta()
    test_dashboard()

    print("\n5. Prediction & Model Performance Endpoints:")
    test_predict_daylight()
    test_predict_night()
    test_predictions_timeseries()
    test_models_list()
    test_model_performance()
    test_model_residuals()
    test_feature_importance()

    print("\n6. Language Guardrails:")
    test_no_banned_vocabulary()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED WITH 100% SUCCESS")
    print("=" * 60)

if __name__ == "__main__":
    run_suite()

