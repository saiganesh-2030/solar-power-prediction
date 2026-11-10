# Project Handbook — Solar Power Generation Prediction & Performance Deviation Analysis

> This is the single source of truth for **what** we are building and **why**.
> If a teammate, the mentor, or Antigravity has a doubt, look here first, then in the file listed in section 12.

---

## 1. The project on one page

**Category:** Web Development (JavaScript + ML)
**Team:** 4 members (roles in `docs/roles/`)
**Data:** Kaggle "Solar Power Generation Data" — two grid-connected solar plants in India, 22 inverters per plant, readings every 15 minutes for roughly 34 days, plus one plant-level weather sensor per plant.

**Problem (our words):** Operators of solar plants see unexpected drops in generation. The causes are mixed: clouds and temperature, dirt on panels, equipment interruptions, and sensor or data glitches. Without a trustworthy estimate of *what the plant should have produced*, it is hard to tell a bad day from a bad inverter, or a real loss from a bad reading.

**What we build:** A web application that
1. estimates expected AC power from weather and time using a regression model,
2. compares it to actual generation and finds significant deviations,
3. explains each deviation with evidence (weather, time, peers, data quality) **without claiming equipment faults**, and
4. converts the shortfall into energy (kWh) and money (INR) with honest uncertainty.

**One-sentence pitch:** *"We don't just flag low generation; we show what the plant should have produced, how sure we are, what else was happening at that moment, and what evidence we would need before calling it a problem."*

## 2. Problem statement traceability (how every sentence is satisfied)

| Problem statement requirement | Where we satisfy it | Owner |
|---|---|---|
| Regression model estimating solar output from environmental and generation measurements | Feature 2 + `docs/DATA_AND_ML_SPEC.md` sections 5–7 (weather + time features; generation-side columns used for QA and a separate DC-to-AC check, not as inputs to the expected-power model) | Role 1 |
| Identify periods when actual differs significantly from estimated | Feature 3, calibrated prediction bands + persistence rule (spec section 8) | Role 2 |
| Investigate associations with weather, time, unusual readings | Feature 4 (weather), Feature 5 (time), evidence ladder + data-quality flags (spec sections 4, 9) | Role 2, 3 |
| Evaluate on unseen time periods | Chronological train/val/test + walk-forward CV; global "Unseen test period" view in the UI (spec section 6) | Role 1, 4 |
| Do not label deviations as equipment faults without supporting evidence | Vocabulary policy (section 8), evidence ladder with confidence, "what would confirm this" panel | Role 2 (all UI) |
| Potential energy shortfall and monetary value | Feature 7, tiered estimate with tariff sensitivity | Role 3 |

## 3. Dataset facts (verify in EDA — do not trust blindly)

Four CSV files: `Plant_1_Generation_Data.csv`, `Plant_1_Weather_Sensor_Data.csv`, `Plant_2_Generation_Data.csv`, `Plant_2_Weather_Sensor_Data.csv`.

| File | Columns |
|---|---|
| Generation | `DATE_TIME, PLANT_ID, SOURCE_KEY (inverter id), DC_POWER, AC_POWER, DAILY_YIELD, TOTAL_YIELD` |
| Weather | `DATE_TIME, PLANT_ID, SOURCE_KEY (sensor id), AMBIENT_TEMPERATURE, MODULE_TEMPERATURE, IRRADIATION` |

Things the team must check and document in `notebooks/01_eda.ipynb` (Role 1) and `docs/DATA_AND_ML_SPEC.md` section 3:
- The weather sensor is **plant-level**: all 22 inverters in a plant share the same weather row at a given time.
- The generation file for Plant 1 is known to use a different `DATE_TIME` text format (day-first) than the other files. Parse with explicit formats and assert the date range.
- Some timestamps are missing (generation and weather), more in some days than others.
- `DC_POWER` and `AC_POWER` are in kW. In Plant 1, DC is commonly reported as roughly 10 times AC; confirm this and handle it in the DC-to-AC check, never by "fixing" the numbers silently.
- `DAILY_YIELD` and `TOTAL_YIELD` are cumulative counters (kWh) per inverter.
- Units for `IRRADIATION` are not documented in the dataset; treat as kW/m2 after confirming that the daily maximum is about 1.0 to 1.2.
- There is **no** rainfall, cloud cover, alarm, maintenance, curtailment or grid-outage data. This limits what we can claim (section 9).

## 4. Solution overview

```
 Kaggle CSVs (4 files, gitignored)
        |
        v
 [Role 1] ml.pipeline.build_dataset  -> artifacts/processed/merged_plant{1,2}.csv   (clean, joined, quality-flagged)
        |
        v
 [Role 1] ml.pipeline.train          -> artifacts/models/*  artifacts/predictions/predictions_plant{1,2}.csv
                                        artifacts/metrics/model_metrics.json
        |
        +--> [Role 2] ml.anomaly.run     -> artifacts/anomalies/{point_flags,events}_plant{1,2}.csv
        |                                   artifacts/anomalies/injection_benchmark.json
        |    [Role 2] ml.weather         -> computed on request from predictions
        +--> [Role 3] ml.history, ml.finance -> computed on request from predictions + events
        |
        v
 FastAPI (backend/app)  --- REST JSON --->  Vite + vanilla JS frontend (Fetch API)
 [Role 4 core, each role owns its routers]   [Role 4 shell, each role owns its pages]
```

Design principle: **roles meet only at files and JSON shapes** (the contracts). Nobody needs another person's code to run, because Role 4 provides stub artifacts that already follow the contracts.

## 5. The seven features (specification)

For each feature: purpose, what the user sees, API endpoints, acceptance criteria. Endpoint details are in `docs/ARCHITECTURE_AND_API.md`.

### Feature 1 — Dashboard Overview (Role 4)
- **Shows:** total actual generation (kWh), total predicted generation (kWh), deviation %, anomaly event count (split by direction and severity), estimated shortfall in INR (range), selected-model test metrics, data-quality score, and "top 5 candidates for inspection" (inverters).
- **Main chart:** actual vs predicted plant power over time with the prediction band and anomaly shading.
- **Global controls:** plant (1/2), date range, and a switch **"Unseen test period only"**.
- **Endpoints:** `GET /api/v1/dashboard/overview`, `GET /api/v1/meta`.
- **Accepts when:** numbers match the sum of the underlying CSV rows (a test verifies this); changing plant/date range updates every card; works in mock mode.

### Feature 2 — Solar Power Prediction (Role 1)
- **Shows:** a prediction form/what-if panel (irradiation, module temperature, ambient temperature, time of day, plant) returning expected AC power per inverter with a prediction interval; plus an "actual vs predicted" time view for any inverter or the plant.
- **Endpoints:** `POST /api/v1/predict`, `GET /api/v1/predictions/timeseries`.
- **Accepts when:** the selected model is loaded from `artifacts/models/`, the same input always gives the same output, inputs are validated (ranges, types), night inputs return about 0 kW.

### Feature 3 — Anomaly Detection (Role 2)
- **Shows:** a list of deviation **events** (not single points) with start, end, duration, direction, energy difference, severity, category, confidence; clicking opens an **event explainer** with small charts: actual vs predicted + band, irradiation, module temperature, fleet median residual, and DC/AC ratio.
- **Endpoints:** `GET /api/v1/anomalies`, `GET /api/v1/anomalies/{event_id}`, `GET /api/v1/anomalies/summary`, `GET /api/v1/anomalies/validation`.
- **Accepts when:** thresholds come only from validation data; the injection benchmark (spec section 10) is displayed; no banned vocabulary appears; every event shows category + confidence + "what would confirm this".

### Feature 4 — Weather Analysis (Role 2)
- **Shows:** irradiation vs AC power (binned scatter), module temperature vs performance ratio (temperature effect), ambient vs module temperature, correlation table (Pearson and Spearman), cloud variability by day, and model feature importance.
- **Endpoints:** `GET /api/v1/weather/relationships`, `GET /api/v1/weather/temperature-effect`, `GET /api/v1/weather/variability`.
- **Accepts when:** every number is computed from data; each chart has a one-line plain-language insight generated from the numbers (not hard-coded text).

### Feature 5 — Historical Analysis (Role 3)
- **Shows:** daily energy totals, hour-by-day heatmap, average daily curve with percentile band, daily Performance Index (actual / expected), inverter ranking with fleet-relative performance, plant comparison.
- **Endpoints:** `GET /api/v1/history/daily`, `/history/heatmap`, `/history/diurnal`, `/history/inverters`.
- **Accepts when:** daily kWh equals the integrated AC power (kW x 0.25 h); reconciliation against `DAILY_YIELD` is shown with its ratio; missing intervals are visible (not silently interpolated).

### Feature 6 — Model Performance (Role 1)
- **Shows:** MAE, RMSE, R2, WAPE, normalized MAE for each model on validation and test (all hours and daylight-only), walk-forward CV results, residual plots, breakdown by irradiation level and by clear versus cloudy day, selected-model badge with reason.
- **Endpoints:** `GET /api/v1/models`, `/models/performance`, `/models/residuals`, `/models/feature-importance`.
- **Accepts when:** metrics come from `artifacts/metrics/model_metrics.json` produced by `ml.pipeline.train`; a leakage test passes; the baseline models are present for comparison.

### Feature 7 — Financial Impact Analysis (Role 3)
- **Shows:** estimated shortfall (kWh) and value (INR) as a **range** with three tiers (conservative, central, upper), split by event category, tariff input with sensitivity, and surplus shown separately (never netted against shortfall).
- **Endpoints:** `GET /api/v1/finance/impact`, `GET /api/v1/finance/sensitivity`.
- **Accepts when:** formulas match `docs/DATA_AND_ML_SPEC.md` section 11; changing the tariff changes only the INR values; the page states clearly that the estimate covers the dataset period and is not an annual forecast.

## 6. How we stand out (innovation, ranked by value for effort)

**Must-have differentiators (build these):**
1. **Fleet-normal expected-power model.** The model has *no inverter id*. It learns what a typical inverter should produce for the weather. Because all inverters in a plant share one weather sensor, comparing each inverter to its peers cancels the weather and isolates inverter-specific behaviour.
2. **Evidence ladder with the "no fault without evidence" rule built into the product.** Each event gets one primary category (data quality, weather transient, fleet-wide, inverter-specific, unexplained), a confidence level based on independent signals, and a "what would confirm this" list (maintenance log, alarm codes, inspection, cleaning record, rainfall). This answers the problem statement directly.
3. **Calibrated prediction bands (split-conformal) on unseen data.** Deviations are measured against a band whose width depends on power level, learned from the validation period, so we do not flag normal noise.
4. **Synthetic-deviation injection benchmark.** There are no labels, so we prove the detector works by injecting known drops, spikes and flatlines into the **test** period and measuring recall, precision and detection delay. This is rare in student projects and very persuasive to a mentor.
5. **Unseen-period rigor.** Chronological split, walk-forward cross-validation, daylight-only metrics, results split by clear/cloudy days, and a UI switch that shows only the unseen test period.
6. **Evidence-tiered financial range.** We show conservative, central and upper shortfall instead of one fake-precise number, exclude data-quality events from the monetary claim, and separate surplus.

**Should-have (do after must-haves are done):**
7. **Physics-informed baseline** `P = a * G * (1 + gamma * (T_module - 25))` as a comparison model and as a way to estimate the temperature coefficient from data. It makes the ML story explainable.
8. **Data-quality layer:** timestamp gaps, flat-lined readings, night-time power, negative values, AC-versus-DC inconsistency, and energy reconciliation with `DAILY_YIELD`, summarized as a data-quality score on the dashboard.
9. **Event explainer drawer** (small-multiples view per event).

**Stretch (only if everything above is finished and tested):**
10. What-if simulator with sliders; PDF/CSV export of the event report; a second plant comparison view; simple alert-rule configuration.

## 7. Scope boundaries (what we will not do)

- No deep learning or huge hyper-parameter searches (about 34 days of data would overfit).
- No claims about soiling, shading, degradation or equipment health beyond "hypothesis, needs external evidence".
- No database server. Artifacts are small files loaded by FastAPI at start-up (decision D-005).
- No authentication or multi-tenant features.
- No live data. The system is designed so a live feed could be added later (see MENTOR_QA).

## 8. Vocabulary policy (strict)

| Do not write | Write instead |
|---|---|
| fault, failure, defective, broken, malfunction | deviation, shortfall, candidate for inspection |
| the inverter is faulty | this inverter performed below its peers for N intervals (confidence: medium) |
| soiling detected | performance-ratio drift observed; possible soiling, needs cleaning/rain records |
| error in sensor | possible measurement irregularity |
| cause | possible explanation / supporting evidence |

Approved category labels (exact strings used in the API): `data_quality`, `weather_transient`, `fleet_wide`, `inverter_specific`, `unexplained`.
Approved confidence labels: `low`, `medium`, `high`.
Approved direction labels: `shortfall`, `surplus`.
Approved severity labels: `low`, `medium`, `high`.

Human-facing display names (UI): "Possible measurement irregularity", "Weather-driven variation", "Plant-wide deviation", "Inverter below peers (candidate for inspection)", "Unexplained deviation".

## 9. Limitations we state openly (this builds credibility)

- Only about 34 days and two plants: seasonal effects are not captured; results are for this period.
- One plant-level sensor: a passing cloud may hit part of the plant before the sensor sees it, causing short weather-transient mismatches.
- No rainfall or cleaning records: soiling cannot be confirmed.
- No alarm/maintenance/curtailment data: equipment issues and grid curtailment cannot be separated from performance loss.
- Tariff is an assumption (configurable); the INR value is indicative.
- Inverter capacity is not given; we use a data-derived capacity proxy (99th percentile of inverter AC power in the training period) for normalization.

## 10. Project-level Definition of Done

- [ ] All 7 features work end to end (data -> API -> UI) for both plants.
- [ ] Reproducible: from a clean clone, the commands in `AGENTS.md` section 7 produce all artifacts and run the app.
- [ ] `pytest` and `npm test` pass; Postman collection runs green.
- [ ] Leakage guard test and time-split test pass.
- [ ] No banned vocabulary anywhere (a test greps for it).
- [ ] Every chart number traces to an endpoint, and every endpoint to an artifact.
- [ ] README has screenshots, setup, and a 2-minute demo script.
- [ ] `docs/DECISION_LOG.md` is up to date; `docs/MENTOR_QA.md` is reviewed by everyone.

## 11. Demo script (5 minutes)

1. Dashboard: choose Plant 1, switch on "Unseen test period only". Point out totals, deviation %, anomaly count, shortfall range.
2. Model Performance: show baseline vs ML on the test period, daylight-only; explain why random splitting was not used.
3. Prediction: change irradiation and module temperature in the what-if panel.
4. Anomalies: open one event; walk through the explainer: band, irradiation, peers, DC/AC ratio, category, confidence, "what would confirm".
5. Injection benchmark: show recall and precision for injected drops.
6. Finance: show tiered range, change tariff, show surplus is separate.
7. Close with limitations and next steps (weather API, maintenance-log integration).

## 12. Document map (where to look)

| Doubt about... | Open |
|---|---|
| Scope, vocabulary, acceptance, demo | this file |
| Folder layout, API endpoints, JSON shapes, file schemas | `docs/ARCHITECTURE_AND_API.md` |
| Cleaning, features, split, models, thresholds, formulas | `docs/DATA_AND_ML_SPEC.md` |
| Who does what, Git rules, schedule, prompts for Antigravity | `docs/TEAM_WORKFLOW.md` and `docs/roles/` |
| Why we chose X | `docs/DECISION_LOG.md`, `docs/MENTOR_QA.md` |
| AI agent behaviour | `AGENTS.md`, `.agents/` |

## 13. Glossary

- **Expected power / predicted power:** what a typical inverter should produce under the measured weather and time.
- **Residual:** actual minus predicted AC power (kW).
- **Deviation event:** a run of consecutive intervals where the residual is outside the band.
- **Prediction band:** range around the prediction in which normal values fall (calibrated on validation data).
- **Performance Index (PI):** actual energy divided by expected energy over a period.
- **Fleet median residual:** median residual across all inverters of a plant at the same timestamp.
- **Peer ratio:** inverter AC power divided by the fleet median AC power at the same timestamp.
- **WAPE:** sum of absolute errors divided by sum of actual values.
- **Daylight-only:** rows with irradiation at or above 0.05 kW/m2.
- **Walk-forward CV:** repeated train-on-past, test-on-next-days validation.
- **Split-conformal:** method to turn validation residuals into calibrated prediction intervals.
