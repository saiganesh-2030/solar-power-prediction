"""Chronological train, validation, and test splitting protocol.

Strict non-negotiable: All evaluation is strictly time-ordered.
Never shuffle or randomly split tabular solar time-series data.

References:
- docs/DATA_AND_ML_SPEC.md section 6
- AGENTS.md section 4 (Non-negotiable 2)
"""

from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from ml.common.config import TRAIN_FRAC, VAL_FRAC

def compute_split_date_blocks(dates: List[str]) -> Dict[str, List[str]]:
    """Computes exact start and end dates for train, val, and test blocks."""
    sorted_dates = sorted(list(set(dates)))
    n_days = len(sorted_dates)
    
    n_train = int(np.floor(TRAIN_FRAC * n_days))
    n_val = int(np.floor(VAL_FRAC * n_days))
    
    train_dates = sorted_dates[:n_train]
    val_dates = sorted_dates[n_train : n_train + n_val]
    test_dates = sorted_dates[n_train + n_val :]
    
    # Assert strictly chronological ordering and non-empty blocks
    assert len(train_dates) > 0, "Train date block must not be empty"
    assert len(val_dates) > 0, "Val date block must not be empty"
    assert len(test_dates) > 0, "Test date block must not be empty"
    assert max(train_dates) < min(val_dates), "Train block must strictly precede Val block"
    assert max(val_dates) < min(test_dates), "Val block must strictly precede Test block"
    
    return {
        "train": [train_dates[0], train_dates[-1]],
        "val": [val_dates[0], val_dates[-1]],
        "test": [test_dates[0], test_dates[-1]],
    }

def assign_split_column(df: pd.DataFrame, split_blocks: Dict[str, List[str]]) -> pd.DataFrame:
    """Adds 'split' column ('train', 'val', or 'test') to DataFrame based on timestamp date."""
    out = df.copy()
    dates = out["timestamp"].str[:10]
    
    train_s, train_e = split_blocks["train"]
    val_s, val_e = split_blocks["val"]
    test_s, test_e = split_blocks["test"]
    
    conditions = [
        (dates >= train_s) & (dates <= train_e),
        (dates >= val_s) & (dates <= val_e),
        (dates >= test_s) & (dates <= test_e),
    ]
    choices = ["train", "val", "test"]
    
    out["split"] = np.select(conditions, choices, default="train")
    return out

def get_walk_forward_folds(train_dates: List[str], fold_train_days: int = 12, fold_test_days: int = 3) -> List[Dict]:
    """Generates expanding-window walk-forward folds strictly inside the train block.
    
    E.g. for 23 train days:
    - Fold 1: train 0..12, test 12..15
    - Fold 2: train 0..15, test 15..18
    - Fold 3: train 0..18, test 18..21
    - Fold 4: train 0..21, test 21..23
    """
    sorted_dates = sorted(list(set(train_dates)))
    n_days = len(sorted_dates)
    folds = []
    
    start_train_len = fold_train_days
    fold_idx = 1
    
    while start_train_len + fold_test_days <= n_days:
        f_train = sorted_dates[:start_train_len]
        f_test = sorted_dates[start_train_len : start_train_len + fold_test_days]
        folds.append({
            "fold": fold_idx,
            "train_dates": f_train,
            "test_dates": f_test,
            "train_end": f_train[-1],
            "test_range": [f_test[0], f_test[-1]],
        })
        start_train_len += fold_test_days
        fold_idx += 1
        
    return folds

