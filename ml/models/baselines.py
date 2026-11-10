"""Baseline models for solar power prediction.

References:
- docs/DATA_AND_ML_SPEC.md section 7
- docs/PROJECT_HANDBOOK.md section 6
"""

from typing import Optional
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.base import BaseEstimator, RegressorMixin

from ml.common.config import NIGHT_G

class PhysicsBaselineRegressor(BaseEstimator, RegressorMixin):
    """Physics-informed baseline model:
    P = a * G * (1 + gamma * (T_module - 25))
    
    Parameters:
    - a >= 0: power coefficient (kW per kW/m2)
    - gamma in [-0.01, 0]: temperature coefficient of power (1/deg C)
    """
    _estimator_type = "regressor"

    def __init__(self, a: float = 800.0, gamma: float = -0.004):
        self.a: float = a
        self.gamma: float = gamma

    @staticmethod
    def _physics_formula(data, a, gamma):
        g, t_mod = data
        return a * g * (1.0 + gamma * (t_mod - 25.0))

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "PhysicsBaselineRegressor":
        g = X["irradiation_kw_m2"].values
        t_mod = X["module_temp_c"].values

        # Filter strictly daylight rows for fitting
        valid = (g >= NIGHT_G) & np.isfinite(g) & np.isfinite(t_mod) & np.isfinite(y)
        if valid.sum() < 20:
            return self

        g_val = g[valid]
        t_val = t_mod[valid]
        y_val = y[valid]

        # Initial guess and bounds: a in [0, 2000], gamma in [-0.01, 0.0]
        p0 = [max(10.0, float(np.mean(y_val) / max(0.1, np.mean(g_val)))), -0.004]
        bounds = ([0.0, -0.01], [2500.0, 0.0])

        try:
            popt, _ = curve_fit(
                self._physics_formula,
                (g_val, t_val),
                y_val,
                p0=p0,
                bounds=bounds,
                maxfev=2000,
            )
            self.a = float(popt[0])
            self.gamma = float(popt[1])
        except Exception:
            # Fallback least squares on a alone if non-linear fit fails
            self.a = max(0.0, float(np.sum(g_val * y_val) / max(1e-6, np.sum(g_val ** 2))))
            self.gamma = -0.004

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        g = X["irradiation_kw_m2"].values
        t_mod = X["module_temp_c"].values
        preds = self._physics_formula((g, t_mod), self.a, self.gamma)
        # Never predict negative power; zero out at night
        preds = np.maximum(0.0, preds)
        preds[g < NIGHT_G] = 0.0
        return preds

class PersistencePrevDayBaseline:
    """Persistence reference baseline: predicts AC power at the same time yesterday."""
    def __init__(self):
        self.history_lookup: dict = {}

    def fit(self, df_train: pd.DataFrame) -> "PersistencePrevDayBaseline":
        # Key: (inverter_id, minute_of_day) -> median AC power
        df = df_train.copy()
        dt = pd.to_datetime(df["timestamp"])
        df["minute_of_day"] = dt.dt.hour * 60 + dt.dt.minute
        grouped = df.groupby(["inverter_id", "minute_of_day"])["ac_kw"].median()
        self.history_lookup = grouped.to_dict()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        dt = pd.to_datetime(df["timestamp"])
        minutes = dt.dt.hour * 60 + dt.dt.minute
        inverters = df["inverter_id"].values
        preds = np.zeros(len(df), dtype=float)
        for i, (inv, m) in enumerate(zip(inverters, minutes)):
            preds[i] = self.history_lookup.get((inv, m), 0.0)
        return np.maximum(0.0, preds)
