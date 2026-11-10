"""Global constants and configuration for the solar power prediction system.

References:
- docs/DATA_AND_ML_SPEC.md section 2
- docs/ARCHITECTURE_AND_API.md section 1 & 3
- docs/DECISION_LOG.md (D-009, D-010)
"""

import os
from pathlib import Path

# Silence joblib/loky CPU core detection warning on Windows
if "LOKY_MAX_CPU_COUNT" not in os.environ:
    os.environ["LOKY_MAX_CPU_COUNT"] = "4"

# Paths
REPO_ROOT: Path = Path(__file__).resolve().parent.parent.parent
DATA_DIR: Path = REPO_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"

ARTIFACTS_DIR: Path = REPO_ROOT / "artifacts"
PROCESSED_DIR: Path = ARTIFACTS_DIR / "processed"
MODELS_DIR: Path = ARTIFACTS_DIR / "models"
PREDICTIONS_DIR: Path = ARTIFACTS_DIR / "predictions"
METRICS_DIR: Path = ARTIFACTS_DIR / "metrics"
ANOMALIES_DIR: Path = ARTIFACTS_DIR / "anomalies"
STUB_DIR: Path = ARTIFACTS_DIR / "_stub"

# Reproducibility
SEED: int = 42

# Time & Energy Constants
INTERVAL_H: float = 0.25  # 15 minutes per interval in hours (kWh = kW * 0.25)

# Solar & Weather Thresholds
DAYLIGHT_G: float = 0.05  # kW/m2: daylight rows for metrics & anomaly eligibility
NIGHT_G: float = 0.01     # kW/m2: below this, predicted power is set to 0.0 kW

# Chronological Data Split (share of calendar days)
TRAIN_FRAC: float = 0.70
VAL_FRAC: float = 0.15
# test fraction is the remaining ~0.15

# Prediction & Conformal Bands Coverage
PRED_INTERVAL_COVERAGE: float = 0.90  # 90% interval shown in /predict
ANOMALY_BAND_COVERAGE: float = 0.99   # 99% band used to flag deviation points

# Deviation Event Rules (Persistence & Fleet)
MIN_EVENT_INTERVALS: int = 3   # 3 consecutive intervals (45 min) to form an event
MAX_GAP_INTERVALS: int = 1     # Allowed 1 interval gap when merging runs
FLEET_FRACTION: float = 0.60   # Share of inverters out of band for fleet-wide event
PEER_LOW: float = 0.85         # Peer ratio lower threshold
PEER_HIGH: float = 1.15        # Peer ratio upper threshold
FLATLINE_INTERVALS: int = 8    # Identical daylight readings flag

# Financial Parameters (INR per kWh)
DEFAULT_TARIFF_INR_PER_KWH: float = 4.0  # Configurable baseline tariff (D-009)

# Standard Approved Labels (Vocabulary Policy)
APPROVED_CATEGORIES = (
    "data_quality",
    "weather_transient",
    "fleet_wide",
    "inverter_specific",
    "unexplained",
)

APPROVED_CONFIDENCE_LEVELS = ("low", "medium", "high")
APPROVED_DIRECTIONS = ("shortfall", "surplus")
APPROVED_SEVERITIES = ("low", "medium", "high")
APPROVED_SPLITS = ("train", "val", "test")

