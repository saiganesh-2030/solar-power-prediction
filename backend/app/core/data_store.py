"""Centralized artifact loader and data access store.

This is the ONLY module in the backend that reads artifacts from disk.
It loads from ARTIFACT_DIR (default: artifacts/), falls back to artifacts/_stub/,
and marks meta.source appropriately.

References:
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
- docs/ARCHITECTURE_AND_API.md section 3
"""

import json
from pathlib import Path
from typing import Any, Optional
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.errors import ArtifactMissingError

class DataStore:
    def __init__(self, artifact_dir: Optional[Path] = None, stub_dir: Optional[Path] = None):
        self.artifact_dir = artifact_dir or settings.ARTIFACT_DIR
        self.stub_dir = stub_dir or settings.STUB_DIR
        self._cache: dict[str, Any] = {}
        self._sources: dict[str, str] = {}  # artifact_name -> "artifacts" | "stub"
        self._global_source: str = "artifacts"

    def _resolve_path(self, relative_path: str) -> tuple[Path, str]:
        """Resolves file path in primary artifact dir or falls back to stub dir."""
        primary = self.artifact_dir / relative_path
        if primary.exists():
            return primary, "artifacts"
        
        fallback = self.stub_dir / relative_path
        if fallback.exists():
            return fallback, "stub"
            
        raise ArtifactMissingError(
            f"Artifact '{relative_path}' was not found in primary ({self.artifact_dir}) "
            f"or stub ({self.stub_dir}) directory."
        )

    def load_csv(self, relative_path: str) -> pd.DataFrame:
        if relative_path in self._cache:
            return self._cache[relative_path].copy()
            
        file_path, source = self._resolve_path(relative_path)
        df = pd.read_csv(file_path)
        self._cache[relative_path] = df
        self._sources[relative_path] = source
        if source == "stub":
            self._global_source = "stub"
        return df.copy()

    def load_json(self, relative_path: str) -> dict[str, Any]:
        if relative_path in self._cache:
            return json.loads(json.dumps(self._cache[relative_path]))
            
        file_path, source = self._resolve_path(relative_path)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._cache[relative_path] = data
        self._sources[relative_path] = source
        if source == "stub":
            self._global_source = "stub"
        return json.loads(json.dumps(data))

    @property
    def source(self) -> str:
        """Returns 'stub' if any loaded artifact was from stub, else 'artifacts'."""
        return self._global_source

    def get_predictions(
        self,
        plant: int,
        start: Optional[str] = None,
        end: Optional[str] = None,
        inverter: Optional[str] = None,
        split: Optional[str] = None,
    ) -> pd.DataFrame:
        rel_path = f"predictions/predictions_plant{plant}.csv"
        df = self.load_csv(rel_path)
        
        if inverter:
            df = df[df["inverter_id"] == inverter]
        if split and split != "all":
            df = df[df["split"] == split]
        if start:
            # timestamp format YYYY-MM-DDTHH:MM:SS
            df = df[df["timestamp"].str[:10] >= start]
        if end:
            df = df[df["timestamp"].str[:10] <= end]
            
        return df.copy()

    def get_events(
        self,
        plant: int,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        direction: Optional[str] = None,
        inverter: Optional[str] = None,
        split: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        rel_path = f"anomalies/events_plant{plant}.csv"
        df = self.load_csv(rel_path)
        
        if inverter:
            df = df[df["inverter_id"] == inverter]
        if category:
            df = df[df["category"] == category]
        if severity:
            df = df[df["severity"] == severity]
        if direction:
            df = df[df["direction"] == direction]
        if split and split != "all":
            df = df[df["split"] == split]
            
        total = len(df)
        paginated = df.iloc[offset : offset + limit]
        return paginated.to_dict(orient="records"), total

    def get_point_flags(
        self,
        plant: int,
        timestamp: Optional[str] = None,
        inverter: Optional[str] = None,
    ) -> pd.DataFrame:
        rel_path = f"anomalies/point_flags_plant{plant}.csv"
        df = self.load_csv(rel_path)
        if inverter:
            df = df[df["inverter_id"] == inverter]
        if timestamp:
            df = df[df["timestamp"] == timestamp]
        return df.copy()

    def get_metrics(self) -> dict[str, Any]:
        return self.load_json("metrics/model_metrics.json")

    def get_band_params(self, plant: int) -> dict[str, Any]:
        return self.load_json(f"anomalies/band_params_plant{plant}.json")

    def get_meta_info(self) -> dict[str, Any]:
        """Provides metadata for the /meta endpoint."""
        # Try loading metrics to get split dates and selected models
        try:
            metrics = self.get_metrics()
            split_dates = metrics.get("split", {
                "train": ["2020-05-15", "2020-06-07"],
                "val": ["2020-06-08", "2020-06-12"],
                "test": ["2020-06-13", "2020-06-17"],
            })
            selected_models = {
                str(p): metrics.get("plants", {}).get(str(p), {}).get("selected_model", "hist_gradient_boosting")
                for p in [1, 2]
            }
        except Exception:
            split_dates = {
                "train": ["2020-05-15", "2020-06-07"],
                "val": ["2020-06-08", "2020-06-12"],
                "test": ["2020-06-13", "2020-06-17"],
            }
            selected_models = {"1": "hist_gradient_boosting", "2": "hist_gradient_boosting"}

        # Get inverters per plant from predictions or defaults
        inverters: dict[str, list[str]] = {"1": [], "2": []}
        date_range = {"start": "2020-05-15", "end": "2020-06-17"}
        
        for p in [1, 2]:
            try:
                preds = self.get_predictions(plant=p)
                inv_list = sorted(preds["inverter_id"].dropna().unique().tolist())
                inverters[str(p)] = inv_list
                if not preds.empty:
                    min_t = preds["timestamp"].min()[:10]
                    max_t = preds["timestamp"].max()[:10]
                    date_range = {"start": min_t, "end": max_t}
            except Exception:
                # Fallback list of 22 mock inverters if artifact not yet loaded
                inverters[str(p)] = [f"INV_{p}_{i:02d}" for i in range(1, 23)]

        return {
            "plants": [1, 2],
            "inverters": inverters,
            "date_range": date_range,
            "split_dates": split_dates,
            "selected_models": selected_models,
            "tariff_default": settings.DEFAULT_TARIFF,
            "data_version": "v1.0",
            "source": self.source,
        }

data_store = DataStore()
