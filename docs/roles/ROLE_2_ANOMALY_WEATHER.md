# ROLE 2 — Anomaly and Weather Engineer (Deviation Detection, Evidence, Weather Analysis)

**Owner:** ____________
**Features:** 3 Anomaly Detection, 4 Weather Analysis
**Read first:** `AGENTS.md`, `docs/PROJECT_HANDBOOK.md` sections 5 (features 3 and 4), 6, 8, 9; `docs/DATA_AND_ML_SPEC.md` sections 1, 2, 8, 9, 10, 12; `docs/ARCHITECTURE_AND_API.md` sections 3.3, 3.4, 3.6, 4 to 7.

## 1. Mission

Find significant deviations between actual and expected generation, group them into events, and **explain each one with evidence and honest confidence** without ever calling it an equipment fault. Prove the detector works on unseen days with an injection benchmark. Also analyse how irradiation and temperature relate to generation.

This role is the heart of the problem statement. The product's credibility rests on the evidence ladder and the vocabulary policy.

## 2. You own (read and write)

```
ml/anomaly/   ml/weather/
artifacts/anomalies/
backend/app/routers/anomalies.py   backend/app/routers/weather.py
backend/app/schemas/anomalies.py   backend/app/schemas/weather.py
backend/app/services/anomaly_service.py   backend/app/services/weather_service.py
frontend/src/pages/anomalies/   frontend/src/pages/weather/
frontend/public/mock/anomalies*.json   weather*.json
tests/unit/ml_anomaly/   tests/unit/ml_weather/
```

## 3. Deliverables (exact)

| # | Deliverable | Path | Contract |
|---|---|---|---|
| D1 | Band parameters | `artifacts/anomalies/band_params_plant{N}.json` | Spec 8 |
| D2 | Point flags | `artifacts/anomalies/point_flags_plant{N}.csv` | Architecture 3.3 |
| D3 | Events with category, confidence, evidence | `artifacts/anomalies/events_plant{N}.csv` | Architecture 3.4 |
| D4 | Injection benchmark | `artifacts/anomalies/injection_benchmark.json` | Architecture 3.6, Spec 10 |
| D5 | Endpoints 10 to 16 | `routers/anomalies.py`, `routers/weather.py` | Architecture section 5 |
| D6 | Pages | Anomalies (list + event explainer + validation panel), Weather (4 to 5 charts with auto insights) | Handbook features 3 and 4 |

Single command: `python -m ml.anomaly.run` produces D1 to D4 for both plants.

## 4. How to start without waiting for Role 1

1. Use `artifacts/_stub/predictions_plant{N}.csv` (made by Role 4 on Day 1). It has the real schema, so your code will not change when real data arrives.
2. Write your own tiny synthetic frames inside tests for rules like persistence and merging.
3. Do not copy Role 1's code. If `ml/common/conformal.py` does not exist yet, keep a local `ml/anomaly/conformal_local.py` and swap later.
4. At Checkpoint A (Day 3) rerun on real predictions and fix only data-dependent issues.

## 5. Task list

**Phase 1 (Day 2 to 5)**
- [ ] `ml/anomaly/residuals.py`: residual, `rel_dev`, eligibility mask, peer ratio, fleet median residual.
- [ ] `ml/anomaly/bands.py`: split-conformal bands by prediction bin from validation rows (Spec 8, steps 3 to 6), saved as JSON; unit tests (coverage close to target on synthetic noise; calibration uses only `val`).
- [ ] `ml/anomaly/events.py`: persistence rule, gap merging, plant-wide events, dropping covered inverter events, event measures, severity.
- [ ] `ml/anomaly/attribution.py`: signals `S_dq`, `S_peer`, `S_recur`, `S_dcac`, `S_vol`, `S_fleet`; category order; confidence; `confirm_with`; `evidence_json`. Unit-test each rule with hand-made events.
- [ ] `ml/anomaly/injection.py`: benchmark per Spec 10 with fixed seed; drop sweep of 10/20/40%.
- [ ] `ml/anomaly/run.py` ties it together and writes `*_run.json`.
- [ ] `ml/weather/analysis.py`: binned relationship, correlations (Pearson, Spearman), temperature effect with bootstrap by day, variability index and day type, auto-generated insight sentences from computed values.
- [ ] Endpoints 10 to 16: add exact JSON shapes to `ARCHITECTURE_AND_API.md` section 6 in your first PR (event list and event detail are already there).
- [ ] Mock JSON for each endpoint.
- [ ] Anomalies page: filters (category, severity, direction, inverter), event table with badges and display names, timeline strip of events per day, **event explainer drawer** (actual vs predicted + band, irradiation, module temperature, fleet median residual, peer ratio, DC/AC ratio, evidence list, "What would confirm this"), validation panel (injection benchmark table, detection curve, val vs test flag rate).
- [ ] Weather page: irradiation vs power (binned with percentile band), module temperature vs performance ratio with the estimated coefficient and its interval plus the confounding caution, ambient vs module temperature, correlation table, daily variability with day-type chips, feature importance (from Role 1's endpoint if available, otherwise omit).

**Phase 2 (Day 6 to 8)**
- [ ] Rerun on final predictions. Check the test flag rate against validation and write an honest paragraph for the README.
- [ ] Review all UI strings with the vocabulary policy (grep test).
- [ ] If there are too many events, tune thresholds only through a `DECISION_LOG.md` entry with evidence.

## 6. Acceptance criteria

- Bands and thresholds use **only validation rows**. A test proves that changing test rows does not change `band_params`.
- Events table has every column in contract 3.4; categories, confidence, direction, severity use only the allowed strings.
- Each event in the UI shows: display category, confidence, duration, energy difference, supporting signals, and "What would confirm this".
- No banned vocabulary in UI text, API output, artifact JSON or code comments (the grep test passes).
- Injection benchmark runs on `split == test` only, is seeded, and is shown in the UI with recall, precision, delay and the detection curve.
- Weather insights are generated from numbers; temperature coefficient is labelled as an association estimate.

## 7. Interfaces

- **You consume:** `predictions_plant*.csv` (Role 1).
- **You provide Role 3:** `events_plant*.csv` and `point_flags_plant*.csv` (finance and history use them).
- **You provide Role 4:** `/anomalies/summary` numbers and event spans for the dashboard (Role 4 reads the CSVs directly, using `core/data_store.py`).
- **You never need** Role 3's code.

## 8. Pitfalls to avoid

- Calibrating bands on train or test rows.
- Flagging single points as events (no persistence).
- Calling anything a fault, failure, or defect. Also avoid "root cause".
- Giving `unexplained` events high confidence.
- Treating night or very low-power rows as eligible.
- Letting underperforming inverters inflate the band (use peer-ratio filter in calibration).
- Hard-coded insight text.
- Presenting the temperature coefficient as a controlled measurement.

## 9. Antigravity starter prompts

```
I am Role 2. Read AGENTS.md, docs/PROJECT_HANDBOOK.md, docs/roles/ROLE_2_ANOMALY_WEATHER.md,
docs/DATA_AND_ML_SPEC.md sections 8-9. Implement ml/anomaly/bands.py and events.py exactly per the spec,
using artifacts/_stub/predictions_plant1.csv as input. Add pytest tests including one proving bands ignore test rows.
Use only approved vocabulary. Run /resolve-doubt if unsure.
```
```
I am Role 2. Build frontend/src/pages/anomalies/ (list + event explainer drawer + validation panel)
against frontend/public/mock/anomalies.json and anomalies-event.json using src/api/client.js and the shared components.
Show category, confidence and "What would confirm this" for every event. Loading, empty and error states required.
```
