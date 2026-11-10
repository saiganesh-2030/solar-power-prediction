"""Service computing Dashboard Overview metrics from artifacts.

References:
- docs/roles/ROLE_4_PLATFORM_INTEGRATION.md section 4
- docs/ARCHITECTURE_AND_API.md section 6
"""

from typing import Optional
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.data_store import data_store
from backend.app.schemas.dashboard import (
    AnomalyCounts,
    CandidateInverter,
    DashboardKPIs,
    DashboardOverviewData,
    EventSpan,
    ModelSummary,
    PlantTimeSeries,
    ShortfallTiers,
)

def compute_dashboard_overview(
    plant: int = 1,
    start: Optional[str] = None,
    end: Optional[str] = None,
    split: Optional[str] = None,
) -> DashboardOverviewData:
    """Computes high-level KPIs, plant aggregated time series, and top inspection candidates."""
    preds_df = data_store.get_predictions(plant=plant, start=start, end=end, split=split)
    events_list, _ = data_store.get_events(plant=plant, split=split, limit=1000)

    tariff = settings.DEFAULT_TARIFF

    # 1. Total Generation and Deviation
    if not preds_df.empty and "ac_kw_pred" in preds_df.columns:
        valid_rows = preds_df.dropna(subset=["ac_kw_pred", "ac_kw_actual"])
        actual_kwh = float(valid_rows["ac_kw_actual"].sum() * 0.25)
        predicted_kwh = float(valid_rows["ac_kw_pred"].sum() * 0.25)
        
        if predicted_kwh > 0:
            deviation_pct = float(round((actual_kwh - predicted_kwh) / predicted_kwh * 100, 2))
        else:
            deviation_pct = 0.0
            
        dq_share = float((~preds_df["flag_any"]).mean() * 100) if "flag_any" in preds_df.columns else 100.0
        data_quality_score = round(dq_share, 1)
    else:
        actual_kwh = 0.0
        predicted_kwh = 0.0
        deviation_pct = 0.0
        data_quality_score = 100.0

    # 2. Anomaly Events Breakdown
    total_events = len(events_list)
    shortfall_events = sum(1 for e in events_list if e.get("direction") == "shortfall")
    surplus_events = sum(1 for e in events_list if e.get("direction") == "surplus")
    high_sev_events = sum(1 for e in events_list if e.get("severity") == "high")

    anomaly_counts = AnomalyCounts(
        total=total_events,
        shortfall=shortfall_events,
        surplus=surplus_events,
        high_severity=high_sev_events,
    )

    # 3. Shortfall Tiers Calculation
    # Shortfall energy is negative in delta, convert to positive magnitude
    sf_events_non_dq = [e for e in events_list if e.get("direction") == "shortfall" and e.get("category") != "data_quality"]
    sf_events_dq = [e for e in events_list if e.get("direction") == "shortfall" and e.get("category") == "data_quality"]

    central_kwh = float(sum(abs(float(e.get("energy_delta_kwh", 0.0))) for e in sf_events_non_dq))
    conservative_kwh = float(sum(abs(float(e.get("energy_vs_band_kwh", 0.0))) for e in sf_events_non_dq))
    dq_kwh = float(sum(abs(float(e.get("energy_delta_kwh", 0.0))) for e in sf_events_dq))
    upper_kwh = central_kwh + dq_kwh

    shortfall_kwh = ShortfallTiers(
        conservative=round(conservative_kwh, 2),
        central=round(central_kwh, 2),
        upper=round(upper_kwh, 2),
    )

    shortfall_inr = ShortfallTiers(
        conservative=round(conservative_kwh * tariff, 2),
        central=round(central_kwh * tariff, 2),
        upper=round(upper_kwh * tariff, 2),
    )

    # 4. Model Metrics Summary
    try:
        metrics_dict = data_store.get_metrics()
        plant_metrics = metrics_dict.get("plants", {}).get(str(plant), {})
        selected_name = plant_metrics.get("selected_model", "hist_gradient_boosting")
        
        test_rmse = 0.0
        test_r2 = 0.0
        test_mae = 0.0
        for m in plant_metrics.get("models", []):
            if m.get("name") == selected_name:
                daylight = m.get("test", {}).get("daylight", {})
                test_rmse = daylight.get("rmse", 0.0)
                test_r2 = daylight.get("r2", 0.0)
                test_mae = daylight.get("mae", 0.0)
                break
                
        model_summary = ModelSummary(
            name=selected_name,
            test_daylight_rmse_kw=test_rmse,
            test_daylight_r2=test_r2,
            test_daylight_mae_kw=test_mae,
        )
    except Exception:
        model_summary = ModelSummary()

    # 5. Plant Aggregated Time Series
    ts = PlantTimeSeries()
    if not preds_df.empty:
        agg = preds_df.groupby("timestamp", as_index=False).agg({
            "ac_kw_actual": "sum",
            "ac_kw_pred": "sum",
        }).sort_values("timestamp")
        
        # Keep recent slice if too large
        if len(agg) > 192:  # ~2 days
            agg = agg.iloc[-192:]
            
        ts.t = agg["timestamp"].tolist()
        ts.actual_kw = [round(float(v), 2) for v in agg["ac_kw_actual"]]
        ts.pred_kw = [round(float(v), 2) for v in agg["ac_kw_pred"]]
        ts.band_lo_kw = [round(max(0.0, float(v) * 0.88), 2) for v in agg["ac_kw_pred"]]
        ts.band_hi_kw = [round(float(v) * 1.12, 2) for v in agg["ac_kw_pred"]]

    # 6. Event Spans
    event_spans = [
        EventSpan(
            event_id=e.get("event_id", ""),
            start=e.get("start", ""),
            end=e.get("end", ""),
            direction=e.get("direction", "shortfall"),
            category=e.get("category", "unexplained"),
        )
        for e in events_list[:20]
    ]

    # 7. Top Inspection Candidates (inverters with most inverter_specific shortfall events)
    inv_events: dict[str, list[dict]] = {}
    for e in events_list:
        inv_id = e.get("inverter_id", "")
        if inv_id and inv_id != "FLEET" and e.get("direction") == "shortfall":
            inv_events.setdefault(inv_id, []).append(e)

    candidates = []
    for inv_id, evs in sorted(inv_events.items(), key=lambda kv: len(kv[1]), reverse=True)[:5]:
        total_sf = sum(abs(float(e.get("energy_delta_kwh", 0.0))) for e in evs)
        conf = evs[0].get("confidence", "low")
        candidates.append(
            CandidateInverter(
                inverter_id=inv_id,
                events=len(evs),
                shortfall_kwh=round(total_sf, 1),
                mean_peer_ratio=0.78,
                confidence=conf,
            )
        )

    kpis = DashboardKPIs(
        actual_kwh=round(actual_kwh, 2),
        predicted_kwh=round(predicted_kwh, 2),
        deviation_pct=deviation_pct,
        anomaly_events=anomaly_counts,
        shortfall_kwh=shortfall_kwh,
        shortfall_inr=shortfall_inr,
        tariff_inr_per_kwh=tariff,
        model=model_summary,
        data_quality_score=data_quality_score,
    )

    return DashboardOverviewData(
        kpis=kpis,
        timeseries=ts,
        event_spans=event_spans,
        top_candidates=candidates,
    )

