# Architecture, Data Contracts and API Contract

> This file is the **contract** between the four roles. It has the highest precedence in the project.
> Changing anything here requires: a PR that edits this file + a `DECISION_LOG.md` entry + a heads-up to the team.

---

## 1. Stack

| Layer | Choice | Notes |
|---|---|---|
| ML / data | Python 3.11, pandas, numpy, scikit-learn, joblib, scipy | Seed `42`. Optional: lightgbm (only if installed cleanly) |
| API | FastAPI, Pydantic v2, uvicorn | Versioned prefix `/api/v1`, auto docs at `/docs` |
| Frontend | Vite, vanilla JavaScript (ES modules), Chart.js + chartjs-adapter-date-fns | Hash router, `fetch` via one client module |
| API testing | Postman collection in `postman/`, pytest + FastAPI `TestClient` | |
| Storage | Files in `artifacts/` loaded at start-up | No DB (decision D-005) |
| Code editor | Antigravity, rules in `AGENTS.md` and `.agents/` | |

## 2. Repository layout (target)

```
solar-power-prediction/
├── AGENTS.md                      # Antigravity entry point
├── README.md
├── requirements.txt               # pinned
├── .gitignore                     # data/raw/, .venv/, node_modules/, *.joblib is NOT ignored (small), __pycache__/
├── .agents/
│   ├── rules/solar-guardrails.md
│   └── workflows/resolve-doubt.md
├── docs/
│   ├── PROJECT_HANDBOOK.md
│   ├── ARCHITECTURE_AND_API.md    # this file
│   ├── DATA_AND_ML_SPEC.md
│   ├── TEAM_WORKFLOW.md
│   ├── DECISION_LOG.md
│   ├── MENTOR_QA.md
│   └── roles/ROLE_1_ML_ENGINEER.md ... ROLE_4_PLATFORM_INTEGRATION.md
├── data/
│   └── raw/                       # the 4 Kaggle CSVs (gitignored). README.md inside says where to download
├── notebooks/                     # 01_eda.ipynb (Role 1), exploratory only, never imported by code
├── ml/                            # pure Python, no FastAPI imports
│   ├── common/config.py           # paths, constants (INTERVAL_H=0.25, DAYLIGHT_G=0.05, SEED=42, split dates)
│   ├── common/conformal.py        # [R1] split-conformal helper shared with R2
│   ├── data/                      # [R1] loading, cleaning, quality flags
│   ├── features/                  # [R1] feature builders
│   ├── models/                    # [R1] baselines, ML models, metrics, selection
│   ├── pipeline/                  # [R1] build_dataset.py, train.py
│   ├── anomaly/                   # [R2] bands, events, attribution, injection benchmark, run.py
│   ├── weather/                   # [R2] correlations, temperature effect, variability
│   ├── history/                   # [R3] aggregations, heatmap, performance index
│   └── finance/                   # [R3] shortfall and value formulas
├── artifacts/                     # generated; small files are committed
│   ├── processed/                 # merged_plant{1,2}.csv                       [R1]
│   ├── models/                    # plant{1,2}/<model>.joblib, selected.json      [R1]
│   ├── predictions/               # predictions_plant{1,2}.csv                    [R1]
│   ├── metrics/                   # model_metrics.json                            [R1]
│   ├── anomalies/                 # point_flags_*, events_*, injection_benchmark.json [R2]
│   └── _stub/                     # synthetic files with the SAME schemas         [R4]
├── backend/app/
│   ├── main.py                    # [R4] app factory, CORS, router registration
│   ├── core/                      # [R4] config.py, data_store.py, errors.py, schemas_common.py
│   ├── routers/
│   │   ├── meta.py, dashboard.py  # [R4]
│   │   ├── predict.py, models.py  # [R1]
│   │   ├── anomalies.py, weather.py   # [R2]
│   │   └── history.py, finance.py     # [R3]
│   ├── schemas/                   # one Pydantic module per router; common.py (re-exports core/schemas_common.py)
│   └── services/                  # business logic called by routers (thin routers)
├── frontend/
│   ├── index.html, vite.config.js, package.json
│   ├── public/mock/               # one JSON per endpoint (mock mode)
│   └── src/
│       ├── main.js, router.js, styles/
│       ├── api/client.js          # [R4] the ONLY place that calls fetch
│       ├── state/filters.js       # [R4] plant, date range, test-only switch (URL query synced)
│       ├── components/            # [R4] kpiCard, lineChart, barChart, heatmap, dataTable, filterBar, badge, banner
│       └── pages/
│           ├── dashboard/         # [R4]
│           ├── prediction/, models/    # [R1]
│           ├── anomalies/, weather/    # [R2]
│           └── history/, finance/      # [R3]
├── scripts/make_stub_artifacts.py # [R4] generates artifacts/_stub/
├── postman/solar.postman_collection.json + environment file   # [R4], each role adds own requests
└── tests/                         # unit/ per role folder, integration/ [R4]
```

Rule: **ml/ never imports backend/**. **backend/ may import ml/** for shared pure functions (formulas, loaders). Frontend only talks to the API.

## 3. Data artifacts contract (file schemas)

All CSVs: UTF-8, header row, comma separated, `timestamp` as `YYYY-MM-DDTHH:MM:SS`, booleans as `True/False`, empty string for null. Plants are `1` or `2`.

### 3.1 `artifacts/processed/merged_plant{N}.csv` (producer: Role 1)

One row per `(timestamp, inverter_id)` with plant-level weather joined on `timestamp`.

| Column | Type | Meaning |
|---|---|---|
| `plant_id` | int | 1 or 2 |
| `timestamp` | str | 15-min grid |
| `inverter_id` | str | SOURCE_KEY of the inverter |
| `dc_kw` | float | DC power (kW), as reported |
| `ac_kw` | float | AC power (kW) |
| `daily_yield_kwh` | float | cumulative daily counter |
| `total_yield_kwh` | float | cumulative lifetime counter |
| `irradiation_kw_m2` | float | plant sensor |
| `module_temp_c` | float | plant sensor |
| `ambient_temp_c` | float | plant sensor |
| `flag_missing_weather` | bool | weather absent or filled across more than 2 intervals |
| `flag_night_power` | bool | irradiation < 0.01 and ac_kw > 0.5% of capacity proxy |
| `flag_flatline` | bool | identical ac_kw for 8 or more consecutive daylight intervals |
| `flag_negative` | bool | ac_kw < 0 or dc_kw < 0 |
| `flag_gap_before` | bool | previous interval for this inverter is missing |
| `flag_ac_dc_inconsistent` | bool | AC > DC (after plant-specific scaling check) |
| `flag_any` | bool | OR of all flags above |

### 3.2 `artifacts/predictions/predictions_plant{N}.csv` (producer: Role 1; consumers: Roles 2, 3, 4)

| Column | Type | Meaning |
|---|---|---|
| `plant_id`, `timestamp`, `inverter_id` | | keys |
| `ac_kw_actual` | float | |
| `ac_kw_pred` | float | output of the **selected** model (never negative); empty when weather is missing |
| `dc_kw_actual` | float | kept for the DC-to-AC check only |
| `irradiation_kw_m2`, `module_temp_c`, `ambient_temp_c` | float | copied from merged |
| `split` | str | `train`, `val` or `test` (by date block) |
| `model_name` | str | selected model name |
| `flag_any` | bool | copied from merged |

Rows exist for every merged row (all splits). In `train`, predictions are in-sample; the UI must label them so.

### 3.3 `artifacts/anomalies/point_flags_plant{N}.csv` (producer: Role 2)

`plant_id, timestamp, inverter_id, residual_kw, rel_dev, band_lo_kw, band_hi_kw, z_robust, is_outlier, event_id` (`event_id` empty when the point is not part of an event).

### 3.4 `artifacts/anomalies/events_plant{N}.csv` (producer: Role 2)

| Column | Type | Meaning |
|---|---|---|
| `event_id` | str | `P{plant}-E{0001}` |
| `plant_id` | int | |
| `inverter_id` | str | inverter id, or `FLEET` for plant-wide events |
| `start`, `end` | str | first and last interval of the event |
| `duration_min` | int | |
| `direction` | str | `shortfall` or `surplus` |
| `energy_delta_kwh` | float | sum of (actual - predicted) x 0.25; negative for shortfall |
| `energy_vs_band_kwh` | float | same, measured against the nearest band edge (conservative); negative for shortfall |
| `mean_rel_dev`, `peak_rel_dev` | float | relative deviation |
| `severity` | str | `low`, `medium`, `high` |
| `category` | str | `data_quality`, `weather_transient`, `fleet_wide`, `inverter_specific`, `unexplained` |
| `confidence` | str | `low`, `medium`, `high` |
| `evidence_json` | str | JSON text: signals and values supporting the category |
| `confirm_with` | str | `;`-separated list of external evidence that would confirm (e.g. `maintenance_log;alarm_codes;cleaning_record`) |
| `split` | str | split of the event start |

### 3.5 `artifacts/metrics/model_metrics.json` (producer: Role 1)

```json
{
  "generated_at": "2026-11-12T10:00:00",
  "seed": 42,
  "split": {"train": ["2020-05-15", "2020-06-07"], "val": ["2020-06-08", "2020-06-12"], "test": ["2020-06-13", "2020-06-17"]},
  "plants": {
    "1": {
      "capacity_proxy_kw": 0.0,
      "selected_model": "hist_gradient_boosting",
      "selection_reason": "lowest validation daylight RMSE; no simpler model within 3%",
      "models": [
        {
          "name": "physics_baseline",
          "val":  {"all": {"mae": 0, "rmse": 0, "r2": 0}, "daylight": {"mae": 0, "rmse": 0, "r2": 0, "wape": 0, "nmae": 0}},
          "test": {"all": {"mae": 0, "rmse": 0, "r2": 0}, "daylight": {"mae": 0, "rmse": 0, "r2": 0, "wape": 0, "nmae": 0}}
        }
      ],
      "walk_forward": [{"fold": 1, "train_end": "2020-05-29", "test_range": ["2020-05-30", "2020-06-01"], "model": "...", "daylight_rmse": 0}],
      "by_irradiation_bin": [{"bin": "0.05-0.2", "model": "...", "mae": 0, "n": 0}],
      "by_day_type": [{"day_type": "clear", "model": "...", "mae": 0, "n": 0}],
      "feature_importance": [{"feature": "irradiation_kw_m2", "importance": 0.0}]
    }
  }
}
```
Zeros above are placeholders for the shape only. The real file contains real computed values. Split dates must be recomputed from the data (section 6 of `DATA_AND_ML_SPEC.md`), the dates above are illustrative.

### 3.6 `artifacts/anomalies/injection_benchmark.json` (producer: Role 2)

```json
{
  "plants": {"1": {"scenarios": [
    {"type": "drop_20pct_2h", "n_injected": 0, "recall": 0, "precision": 0, "median_detection_delay_min": 0},
    {"type": "spike_plus_30pct_1h", "n_injected": 0, "recall": 0, "precision": 0, "median_detection_delay_min": 0},
    {"type": "flatline_2h", "n_injected": 0, "recall": 0, "precision": 0, "median_detection_delay_min": 0}
  ]}}
}
```

## 4. API conventions

- Base URL: `http://localhost:8000/api/v1`. Interactive docs: `http://localhost:8000/docs`.
- CORS: allow `http://localhost:5173` and `http://127.0.0.1:5173`.
- Methods: `GET` for reads, `POST` only for `/predict`.
- Common query parameters (where relevant): `plant` (1 or 2), `start` and `end` (`YYYY-MM-DD`, inclusive), `inverter` (id, optional), `split` (`all` default, or `train`, `val`, `test`), `limit` and `offset` for lists.
- **Success envelope:**
```json
{ "data": { }, "meta": { "plant": 1, "start": "2020-06-13", "end": "2020-06-17", "split": "test", "model_name": "hist_gradient_boosting", "generated_at": "2026-11-12T10:00:00", "source": "artifacts" } }
```
- **Error envelope** (HTTP 400, 404, 422, 500):
```json
{ "error": { "code": "invalid_parameter", "message": "start must be on or before end", "details": { "field": "start" } } }
```
- Error codes: `invalid_parameter`, `not_found`, `artifact_missing`, `internal_error`.
- Numbers: floats rounded to 4 decimals in JSON; money rounded to 2; no `NaN` (use `null`).
- Time series arrays are column-oriented to keep payloads small: `{"t": [...], "actual": [...], "pred": [...]}`.
- Every router uses Pydantic response models; the shapes below are the contract.

## 5. Endpoint catalogue

| # | Method and path | Purpose | Owner |
|---|---|---|---|
| 1 | `GET /health` | liveness (`{"status":"ok"}`) | R4 |
| 2 | `GET /meta` | plants, inverter ids, date range, split dates, selected models, tariff default, data version | R4 |
| 3 | `GET /dashboard/overview` | KPIs + plant time series + top candidates | R4 |
| 4 | `POST /predict` | expected power for given conditions | R1 |
| 5 | `GET /predictions/timeseries` | actual vs predicted (plant or inverter) | R1 |
| 6 | `GET /models` | list of models with short descriptions | R1 |
| 7 | `GET /models/performance` | metrics table, walk-forward, breakdowns | R1 |
| 8 | `GET /models/residuals` | residual histogram + residual vs irradiation | R1 |
| 9 | `GET /models/feature-importance` | permutation importance | R1 |
| 10 | `GET /anomalies` | list of events (filters: severity, category, direction, inverter) | R2 |
| 11 | `GET /anomalies/{event_id}` | one event with explainer series | R2 |
| 12 | `GET /anomalies/summary` | counts by category/severity/direction/day | R2 |
| 13 | `GET /anomalies/validation` | injection benchmark + flag-rate stability (val vs test) | R2 |
| 14 | `GET /weather/relationships` | irradiation/temperature vs power (binned), correlations | R2 |
| 15 | `GET /weather/temperature-effect` | performance ratio vs module temperature, estimated coefficient | R2 |
| 16 | `GET /weather/variability` | per-day irradiation variability and day type | R2 |
| 17 | `GET /history/daily` | daily actual vs expected energy, Performance Index | R3 |
| 18 | `GET /history/heatmap` | date x hour matrix of energy | R3 |
| 19 | `GET /history/diurnal` | average curve with percentile band | R3 |
| 20 | `GET /history/inverters` | inverter ranking, peer ratio, reconciliation | R3 |
| 21 | `GET /finance/impact` | shortfall kWh and INR by tier and category | R3 |
| 22 | `GET /finance/sensitivity` | INR across tariff values | R3 |

## 6. Payload examples (the contract; fields may be added, never renamed or removed without a PR)

### `GET /dashboard/overview?plant=1&start=2020-06-13&end=2020-06-17&split=test`
```json
{ "data": {
  "kpis": {
    "actual_kwh": 0.0, "predicted_kwh": 0.0, "deviation_pct": 0.0,
    "anomaly_events": {"total": 0, "shortfall": 0, "surplus": 0, "high_severity": 0},
    "shortfall_kwh": {"conservative": 0.0, "central": 0.0, "upper": 0.0},
    "shortfall_inr": {"conservative": 0.0, "central": 0.0, "upper": 0.0},
    "tariff_inr_per_kwh": 0.0,
    "model": {"name": "hist_gradient_boosting", "test_daylight_rmse_kw": 0.0, "test_daylight_r2": 0.0, "test_daylight_mae_kw": 0.0},
    "data_quality_score": 0.0
  },
  "timeseries": {"t": [], "actual_kw": [], "pred_kw": [], "band_lo_kw": [], "band_hi_kw": []},
  "event_spans": [{"event_id": "P1-E0001", "start": "", "end": "", "direction": "shortfall", "category": "unexplained"}],
  "top_candidates": [{"inverter_id": "", "events": 0, "shortfall_kwh": 0.0, "mean_peer_ratio": 0.0, "confidence": "low"}]
}, "meta": {} }
```
Plant-level `timeseries` = sum over inverters at each timestamp (kW). `data_quality_score` = 100 x share of rows with `flag_any == False`.

### `POST /predict`
Request:
```json
{ "plant": 1, "timestamp": "2020-06-10T12:00:00", "irradiation_kw_m2": 0.85, "module_temp_c": 52.0, "ambient_temp_c": 33.0, "model": "selected" }
```
Response `data`:
```json
{ "ac_kw_per_inverter": 0.0, "interval_lo_kw": 0.0, "interval_hi_kw": 0.0, "interval_coverage": 0.9, "plant_ac_kw_estimate": 0.0, "n_inverters": 22, "model_name": "hist_gradient_boosting", "warnings": [] }
```
Validation: irradiation 0 to 1.5, module temp -10 to 90, ambient -10 to 60; out-of-range -> 422 `invalid_parameter`. `warnings` carries e.g. `"extrapolation: input outside training range"`. `plant_ac_kw_estimate` = per-inverter x n_inverters (label it as an estimate for a fleet-normal plant).

### `GET /anomalies?plant=1&split=test&category=inverter_specific&limit=50`
```json
{ "data": { "total": 0, "items": [
  { "event_id": "P1-E0007", "inverter_id": "", "start": "", "end": "", "duration_min": 0, "direction": "shortfall",
    "energy_delta_kwh": 0.0, "mean_rel_dev": 0.0, "severity": "medium", "category": "inverter_specific", "confidence": "medium",
    "display_category": "Inverter below peers (candidate for inspection)", "confirm_with": ["maintenance_log", "alarm_codes"] }
] }, "meta": {} }
```

### `GET /anomalies/{event_id}`
`data` = the item above plus `evidence` (object from `evidence_json`) and `series`:
```json
{ "series": { "t": [], "actual_kw": [], "pred_kw": [], "band_lo_kw": [], "band_hi_kw": [],
  "irradiation_kw_m2": [], "module_temp_c": [], "fleet_median_residual_kw": [], "peer_ratio": [], "dc_ac_ratio": [] },
  "context_window_min": 120 }
```
The series covers the event plus 2 hours before and after.

### `GET /finance/impact?plant=1&start=...&end=...&tariff=4.0`
```json
{ "data": { "tariff_inr_per_kwh": 4.0, "period_days": 0,
  "tiers": { "conservative": {"kwh": 0.0, "inr": 0.0}, "central": {"kwh": 0.0, "inr": 0.0}, "upper": {"kwh": 0.0, "inr": 0.0} },
  "by_category": [{"category": "inverter_specific", "central_kwh": 0.0, "central_inr": 0.0}],
  "excluded": {"data_quality_kwh": 0.0},
  "surplus": {"kwh": 0.0, "inr": 0.0},
  "note": "Indicative estimate for the selected period only; not an annual forecast." }, "meta": {} }
```

### Other endpoints
Roles define the exact JSON for endpoints they own by adding a subsection **here** (copy the style above) in their first PR, before building the UI. Use column-oriented arrays for series.

## 7. Frontend conventions

- Router: hash based (`#/`, `#/prediction`, `#/anomalies`, `#/weather`, `#/history`, `#/models`, `#/finance`). Each page module exports `render(container, ctx)` and `destroy()`.
- API client (`src/api/client.js`): `get(path, params)` and `post(path, body)`; builds query strings, parses the envelope, throws a typed `ApiError`, and in mock mode (`VITE_USE_MOCK=true`) returns `public/mock/<path-with-dashes>.json`.
- Env: `VITE_API_BASE=http://localhost:8000/api/v1`, `VITE_USE_MOCK=false`.
- Global filters in `state/filters.js`: `plant`, `start`, `end`, `testOnly`; synced to the URL query so a view can be shared.
- Every page: skeleton loader, empty state, error banner with retry, and a one-line "How to read this chart" caption.
- Chart rules: axes with units, legend, tooltip with time and values, colour-blind-safe palette, light and dark friendly.
- No frameworks, no inline `fetch` outside `client.js`, no `innerHTML` with unsanitized API strings (use `textContent`).

## 8. Run, test, Postman

See `AGENTS.md` section 7 for commands. Postman: one folder per router, environment variable `{{baseUrl}}`, a test script on each request that checks status 200 and the envelope keys (`data`, `meta`). Role 4 runs the whole collection with Newman or the Postman runner before every release.

## 9. Versioning of contracts

`API_VERSION = v1`. Additive changes (new optional field) are allowed with a PR. Breaking changes (rename, remove, change type) require: new decision log entry, update of this file, update of `frontend/public/mock/`, update of the Postman collection, and agreement of the affected roles.
