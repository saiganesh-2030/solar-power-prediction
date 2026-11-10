"""Regression model definitions for solar power estimation.

References:
- docs/DATA_AND_ML_SPEC.md section 7
"""

from typing import Any, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from ml.common.config import NIGHT_G, SEED
from ml.features.build_features import FEATURE_COLUMNS

# Poly features subset: G, T_module, T_ambient, temp_delta, hour_sin, hour_cos
RIDGE_POLY_COLS = [
    "irradiation_kw_m2",
    "module_temp_c",
    "ambient_temp_c",
    "temp_delta_c",
    "hour_sin",
    "hour_cos",
]

class RidgePolyModel:
    """Degree-2 Polynomial Ridge Regressor with Standard Scaling."""
    def __init__(self, alpha: float = 10.0):
        self.alpha = alpha
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("ridge", Ridge(alpha=self.alpha, random_state=SEED)),
        ])

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "RidgePolyModel":
        sub_X = X[RIDGE_POLY_COLS].fillna(0.0)
        self.pipeline.fit(sub_X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        sub_X = X[RIDGE_POLY_COLS].fillna(0.0)
        preds = self.pipeline.predict(sub_X)
        preds = np.maximum(0.0, preds)
        g = X["irradiation_kw_m2"].values
        preds[g < NIGHT_G] = 0.0
        return preds

class HistGradientBoostingModel:
    """HistGradientBoostingRegressor with monotonic constraint on irradiation."""
    def __init__(self, learning_rate: float = 0.08, max_iter: int = 150, max_depth: int = 8):
        # Monotonic constraint: 1 for irradiation (index 0), 0 for all other features
        monotonic_cst = [1] + [0] * (len(FEATURE_COLUMNS) - 1)
        self.model = HistGradientBoostingRegressor(
            monotonic_cst=monotonic_cst,
            learning_rate=learning_rate,
            max_iter=max_iter,
            max_depth=max_depth,
            random_state=SEED,
        )

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "HistGradientBoostingModel":
        features = X[FEATURE_COLUMNS]
        self.model.fit(features, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        features = X[FEATURE_COLUMNS]
        preds = self.model.predict(features)
        preds = np.maximum(0.0, preds)
        g = X["irradiation_kw_m2"].values
        preds[g < NIGHT_G] = 0.0
        return preds

class RandomForestModel:
    """Random Forest Regressor."""
    def __init__(self, n_estimators: int = 100, max_depth: int = 12, min_samples_leaf: int = 5):
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=SEED,
            n_jobs=1,
        )

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "RandomForestModel":
        features = X[FEATURE_COLUMNS].fillna(0.0)
        self.model.fit(features, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        features = X[FEATURE_COLUMNS].fillna(0.0)
        preds = self.model.predict(features)
        preds = np.maximum(0.0, preds)
        g = X["irradiation_kw_m2"].values
        preds[g < NIGHT_G] = 0.0
        return preds

