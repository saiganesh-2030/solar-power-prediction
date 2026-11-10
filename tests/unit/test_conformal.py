"""Unit tests for ml/common/conformal.py split-conformal intervals.

References:
- docs/DATA_AND_ML_SPEC.md section 8
- docs/roles/ROLE_1_ML_ENGINEER.md Deliverable D6
"""

import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.common.conformal import compute_conformal_bins, apply_conformal_bands

def test_conformal_calibration_and_coverage():
    np.random.seed(42)
    # Synthetic calibration predictions and residuals (heteroscedastic noise)
    preds = np.random.uniform(50.0, 800.0, size=1000)
    noise_scale = 10.0 + 0.05 * preds
    residuals = np.random.normal(0.0, noise_scale)

    target_coverage = 0.90
    config = compute_conformal_bins(
        calibration_preds=preds,
        calibration_residuals=residuals,
        coverage=target_coverage,
        n_bins=8,
        min_width=5.0,
    )

    assert config["coverage"] == target_coverage
    assert len(config["bins"]) == 8

    # Apply to calibration data to check empirical coverage
    band_lo, band_hi, q_vals = apply_conformal_bands(preds, config)

    assert (band_lo >= 0.0).all(), "Lower band must never be negative"
    assert (band_hi >= band_lo).all(), "Upper band must be >= lower band"
    assert (q_vals >= 5.0).all(), "Band width must obey min_width"

    actuals = preds + residuals
    in_band = (actuals >= band_lo) & (actuals <= band_hi)
    empirical_coverage = np.mean(in_band)
    
    # Split-conformal guarantees >= 1 - alpha on finite samples
    assert empirical_coverage >= 0.88, f"Coverage too low: {empirical_coverage:.3f}"
    print(f"✓ test_conformal_calibration_and_coverage passed (Empirical coverage: {empirical_coverage:.1%})")

if __name__ == "__main__":
    test_conformal_calibration_and_coverage()
    print("All conformal unit tests passed successfully!")

