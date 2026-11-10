# Solar Power Generation Prediction and Performance Deviation Analysis

A web application that estimates expected solar AC power from weather and time, finds significant deviations from actual generation, explains them with evidence (without calling them equipment faults), and estimates the energy and money at stake.

**Data:** Kaggle "Solar Power Generation Data" (2 plants, 22 inverters each, 15-minute data, about 34 days).  
**Stack:** Python (FastAPI, pandas, scikit-learn) + JavaScript (Vite, Chart.js, Fetch API). Postman for API testing.  
**Team:** 4 members, 4 roles.

## The 7 features

| # | Feature | Owner |
|---|---|---|
| 1 | Dashboard Overview | Role 4 |
| 2 | Solar Power Prediction | Role 1 |
| 3 | Anomaly Detection | Role 2 |
| 4 | Weather Analysis | Role 2 |
| 5 | Historical Analysis | Role 3 |
| 6 | Model Performance | Role 1 |
| 7 | Financial Impact Analysis | Role 3 |

## Where to read what

| You want to know... | Open |
|---|---|
| What and why (scope, vocabulary, acceptance, demo) | `docs/PROJECT_HANDBOOK.md` |
| Folder layout, file schemas, REST API | `docs/ARCHITECTURE_AND_API.md` |
| Cleaning, features, split, models, anomaly rules, finance formulas | `docs/DATA_AND_ML_SPEC.md` |
| Who does what, Git rules, schedule, Antigravity usage | `docs/TEAM_WORKFLOW.md`, `docs/roles/` |
| Why we decided X | `docs/DECISION_LOG.md` |
| Questions the mentor may ask | `docs/MENTOR_QA.md` |
| AI agent instructions | `AGENTS.md`, `.agents/` |

## Quick start

```bash
# 1. get the data (not committed): download the 4 CSVs from Kaggle into data/raw/
#    https://www.kaggle.com/datasets/anikannal/solar-power-generation-data

# 2. Python
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. build data, train, detect deviations
python -m ml.pipeline.build_dataset
python -m ml.pipeline.train

# 4. run tests (unit and integration)
pytest -q
python tests/run_all_tests.py

# 5. run the API (add ARTIFACT_DIR=artifacts/_stub to use stub data)
uvicorn backend.app.main:app --reload --port 8000     # docs: http://localhost:8000/docs

# 6. run the frontend
cd frontend && npm install && npm run dev             # http://localhost:5173
# no backend yet? VITE_USE_MOCK=true npm run dev
```

## Principles (short)

- Expected power is estimated from weather and time only (no leakage).
- Evaluation is chronological, on unseen days; daylight-only metrics are primary.
- Deviations are described with evidence and confidence, never labelled as equipment faults.
- Every number shown comes from data through the API.

## Model card

### 1. Data
- **Source:** Kaggle `anikannal/solar-power-generation-data` (2 solar PV plants, 22 inverters each, 15-minute intervals, ~34 calendar days: May 15, 2020 to June 17, 2020).
- **Target:** Inverter-level AC power generation (`ac_kw`).
- **Quality Cleaning:** 6 quality flags (`flag_missing_weather`, `flag_interpolated_weather`, `flag_zero_ac_positive_dc`, `flag_positive_ac_zero_dc`, `flag_extreme_dc_ac_ratio`, `flag_flatlined_ac`) + `flag_any`. Over 98.6% of rows in Plant 1 and 94.8% in Plant 2 are clean.

### 2. Features (Strict Leakage Guard)
- Strictly weather and temporal features only; zero leakage of future data or concurrent plant yield/inverter ID.
- Covariates: `irradiation_kw_m2`, `module_temp_c`, `ambient_temp_c`, `temp_delta_c`, cyclical diurnal encodings (`hour_sin`, `hour_cos`), and trailing weather statistics (`irr_lag1`, `irr_diff1`, `irr_roll_mean_4`, `irr_roll_std_4`, `irr_x_modtemp`).
- Forbidden features: `DC_POWER`, `DAILY_YIELD`, `TOTAL_YIELD`, lagged `AC_POWER`, inverter ID.

### 3. Chronological Split
- Time-ordered evaluation only (never random train/test split):
  - **Train (70%):** 2020-05-15 to 2020-06-06 (23 days)
  - **Validation (15%):** 2020-06-07 to 2020-06-11 (5 days)
  - **Unseen Test (15%):** 2020-06-12 to 2020-06-17 (6 days)
- Tuning and walk-forward stability checks evaluated strictly within the training block; model selection performed on validation; test reported once without feedback tuning.

### 4. Selected Model Per Plant & Out-of-Sample Daylight Test Metrics
Model selection follows the 3% Parsimony Principle (Spec section 6 & Decision D-006):

- **Plant 1:**
  - **Selected Model:** `physics_baseline` ($P = a \cdot G \cdot (1 + \gamma (T_{\text{mod}} - 25))$)
  - **Selection Rationale:** Parsimony rule — validation daylight RMSE (111.97 kW) was within 1.6% of the best complex tree model (`hist_gradient_boosting` at 110.19 kW). Simpler, interpretable physics formulation preferred.
  - **Unseen Test Daylight Metrics (Inverter Level):**
    - RMSE: **53.96 kW**
    - MAE: **34.16 kW**
    - $R^2$: **0.9717**
    - WAPE: **5.74%**
    - Normalized MAE (nMAE): **0.0266** (2.7% of capacity proxy)
  - **Unseen Test Daylight Metrics (Plant Level):**
    - RMSE: **687.39 kW** | MAE: **500.51 kW** | $R^2$: **0.9901** | WAPE: **3.91%**

- **Plant 2:**
  - **Selected Model:** `physics_baseline`
  - **Selection Rationale:** Direct lowest validation daylight RMSE (**207.15 kW**).
  - **Unseen Test Daylight Metrics (Inverter Level):**
    - RMSE: **185.60 kW**
    - MAE: **84.66 kW**
    - $R^2$: **0.5425**
    - WAPE: **18.77%**
    - Normalized MAE (nMAE): **0.0663** (6.6% of capacity proxy)
  - **Unseen Test Daylight Metrics (Plant Level):**
    - RMSE: **3040.61 kW** | MAE: **1990.22 kW** | $R^2$: **0.8654** | WAPE: **15.22%**

### 5. Robust Training Result (Decision D-015)
- Peer-ratio training filter (`inverter_ac / fleet_median_ac` within [0.70, 1.30]) drops outlier rows during training to prevent chronic underperformance from depressing expected fleet-normal generation.
- **Plant 1:** 124 outlier rows (0.5%) dropped; fleet is highly uniform.
- **Plant 2:** 972 outlier rows (4.7%) dropped. Protects baseline from persistently degraded inverters, reducing unseen test daylight MAE across models by:
  - Physics Baseline: **92.48 kW -> 84.66 kW** (8.5% improvement)
  - Polynomial Ridge: **100.67 kW -> 81.30 kW** (19.2% improvement)
  - Hist Gradient Boosting: **93.69 kW -> 81.92 kW** (12.6% improvement)

### 6. Limitations & Honest Assessment
- **Duration:** Only ~34 calendar days of observation during May–June 2020 (dry/early monsoon season in India). Cannot model full annual seasonality, winter solar declination, or seasonal monsoonal degradation.
- **Plant 2 Fleet Disparity:** Several inverters in Plant 2 show persistent underperformance relative to peers throughout the dataset; models estimate the fleet-normal potential rather than inverter-specific degradation curves.
- **Missing Sensor Channels:** No co-located rainfall sensor, wind speed anemometer, or multi-point irradiance sensors across the array. Cloud transients cannot be separated from localized physical shading with single-sensor weather data.
- **Vocabulary Policy:** Predictions represent statistical expectations under clean ambient conditions; performance shortfalls are candidates for inspection and are never diagnosed as equipment failures or defects without attached external logs.
