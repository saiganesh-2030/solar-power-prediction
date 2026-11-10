"""Split-conformal prediction intervals and calibrated anomaly band calibration.

Shared module owned by Role 1, consumed by Role 2 and /predict endpoint.

References:
- docs/DATA_AND_ML_SPEC.md section 8
- docs/roles/ROLE_1_ML_ENGINEER.md Deliverable D6
- docs/DECISION_LOG.md (D-011)
"""

from typing import Any, Dict, List, Tuple
import numpy as np

def compute_conformal_bins(
    calibration_preds: np.ndarray,
    calibration_residuals: np.ndarray,
    coverage: float = 0.90,
    n_bins: int = 8,
    min_width: float = 0.0,
) -> Dict[str, Any]:
    """Calibrates split-conformal quantile thresholds partitioned by predicted power bins.
    
    Formula per Spec section 8:
    q_b = split-conformal quantile of |residual| at coverage:
          quantile level = ceil((n_b + 1) * coverage) / n_b
          clipped at 1.0.
    Threshold: max(q_b, min_width).
    """
    abs_res = np.abs(calibration_residuals)
    
    # Quantile bins of predicted power
    # Fallback to linear linspace if quantile binning has identical edges
    try:
        quantiles = np.linspace(0.0, 1.0, n_bins + 1)
        bin_edges = np.unique(np.quantile(calibration_preds, quantiles))
        if len(bin_edges) < 3:
            bin_edges = np.linspace(np.min(calibration_preds), np.max(calibration_preds) + 1e-4, n_bins + 1)
    except Exception:
        bin_edges = np.linspace(0.0, max(100.0, np.max(calibration_preds) + 1e-4), n_bins + 1)

    bins_data: List[Dict[str, float]] = []

    for i in range(len(bin_edges) - 1):
        low = bin_edges[i]
        high = bin_edges[i + 1]
        
        if i == len(bin_edges) - 2:
            mask = (calibration_preds >= low) & (calibration_preds <= high)
        else:
            mask = (calibration_preds >= low) & (calibration_preds < high)

        bin_res = abs_res[mask]
        n_b = len(bin_res)

        if n_b >= 5:
            # Finite-sample split-conformal empirical quantile
            alpha_level = min(1.0, np.ceil((n_b + 1) * coverage) / n_b)
            # numpy quantile in [0, 1]
            q_b = float(np.quantile(bin_res, min(1.0, alpha_level)))
            # Median absolute deviation (MAD)
            mad_b = float(np.median(bin_res))
        else:
            # Fallback to global quantile if bin is sparse
            q_b = float(np.quantile(abs_res, coverage)) if len(abs_res) > 0 else 25.0
            mad_b = float(np.median(abs_res)) if len(abs_res) > 0 else 12.0

        q_b = max(q_b, min_width)
        
        bins_data.append({
            "bin": i,
            "pred_min": float(round(low, 2)),
            "pred_max": float(round(high, 2)),
            "q_b": float(round(q_b, 2)),
            "mad_b": float(round(mad_b, 2)),
            "n": int(n_b),
        })

    return {
        "coverage": coverage,
        "n_bins": len(bins_data),
        "bin_edges": [float(round(e, 2)) for e in bin_edges],
        "bins": bins_data,
    }

def apply_conformal_bands(
    preds: np.ndarray,
    calibrated_config: Dict[str, Any],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Applies calibrated conformal bands to an array of predictions.
    
    Returns:
    - band_lo: max(0, pred - q_b)
    - band_hi: pred + q_b
    - q_b: half-width applied to each point
    """
    bins = calibrated_config["bins"]
    n_pts = len(preds)
    q_applied = np.zeros(n_pts, dtype=float)

    for b in bins:
        low = b["pred_min"]
        high = b["pred_max"]
        q_val = b["q_b"]
        mask = (preds >= low) & (preds <= high if b["bin"] == len(bins) - 1 else preds < high)
        q_applied[mask] = q_val

    # For any out-of-range points (e.g. higher than calibration max)
    unassigned = q_applied == 0.0
    if np.any(unassigned):
        last_q = bins[-1]["q_b"] if bins else 25.0
        q_applied[unassigned] = last_q

    band_lo = np.maximum(0.0, preds - q_applied)
    band_hi = preds + q_applied
    return band_lo, band_hi, q_applied

