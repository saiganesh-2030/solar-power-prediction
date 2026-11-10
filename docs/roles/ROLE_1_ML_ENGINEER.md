# ROLE 1 — ML Engineer (Data, Features, Models, Prediction, Model Performance)

**Owner:** ____________
**Features:** 2 Solar Power Prediction, 6 Model Performance
**Read first:** `AGENTS.md`, `docs/PROJECT_HANDBOOK.md` sections 3, 5 (features 2 and 6), 8; `docs/DATA_AND_ML_SPEC.md` sections 1 to 7 and 14; `docs/ARCHITECTURE_AND_API.md` sections 3.1, 3.2, 3.5, 4 to 7.

## 1. Mission

Turn the four raw CSV files into clean, quality-flagged, joined data; build and honestly evaluate regression models that estimate expected AC power from weather and time; publish predictions that everyone else builds on; serve them through the API and two pages.

You are upstream of Roles 2 and 3. Your first real `predictions_plant{N}.csv` (even from the simple baseline) unlocks them: **ship a baseline early (Checkpoint A, Day 3), then improve.**

## 2. You own (read and write)

```
ml/common/config.py          ml/common/conformal.py
ml/data/   ml/features/   ml/models/   ml/pipeline/
notebooks/01_eda.ipynb
artifacts/processed/   artifacts/models/   artifacts/predictions/   artifacts/metrics/
backend/app/routers/predict.py   backend/app/routers/models.py
backend/app/schemas/predict.py   backend/app/schemas/models.py   backend/app/services/prediction_service.py
frontend/src/pages/prediction/   frontend/src/pages/models/
frontend/public/mock/predict*.json   models*.json   predictions-timeseries.json
tests/unit/ml_data/   tests/unit/ml_models/
```
Do not edit other roles' folders. Ask via PR if you need a change in `core/` (Role 4).

## 3. Deliverables (exact)

| # | Deliverable | Path | Contract |
|---|---|---|---|
| D1 | Data report | `artifacts/processed/data_report.json` | date range, rows, inverters, duplicates, missing slots, units check |
| D2 | Merged data with flags | `artifacts/processed/merged_plant{1,2}.csv` | Architecture 3.1 |
| D3 | Trained models | `artifacts/models/plant{N}/<model>.joblib`, `selected.json` | |
| D4 | Predictions | `artifacts/predictions/predictions_plant{1,2}.csv` | Architecture 3.2 |
| D5 | Metrics | `artifacts/metrics/model_metrics.json` | Architecture 3.5 |
| D6 | `ml/common/conformal.py` | function `conformal_quantiles(abs_residuals, bins_by, coverage)` + tests | Spec section 8 |
| D7 | Endpoints 4 to 9 | `routers/predict.py`, `routers/models.py` | Architecture section 5 |
| D8 | Pages | Prediction (what-if form + actual vs predicted), Model Performance | Handbook features 2 and 6 |
| D9 | EDA notebook | `notebooks/01_eda.ipynb` | findings feed `DECISION_LOG.md` |

## 4. Task list

**Phase 0 (Day 0 to 1)**
- [ ] Download the Kaggle data into `data/raw/` (add `data/raw/README.md` with the link and file names). Never commit the CSVs.
- [ ] `ml/common/config.py` with all constants from Spec section 2.
- [ ] EDA: parse dates with explicit formats, count days, inverters, missing slots, duplicates; plot irradiation vs AC; check DC vs AC scale per plant; check irradiation units; write `data_report.json`. Log surprises in `DECISION_LOG.md`.

**Phase 1 (Day 2 to 5)**
- [ ] `ml/data/load.py`, `clean.py`, `quality_flags.py` (Spec 3 and 4) with unit tests on tiny hand-made frames (parse formats, join, interpolation limit, each flag).
- [ ] `ml/pipeline/build_dataset.py` -> `merged_plant*.csv`.
- [ ] `ml/features/build_features.py` (Spec 5) with a **leakage test**: features contain no forbidden names.
- [ ] Split function (Spec 6) + test: ordering and no overlap.
- [ ] Baselines first: `physics_baseline`, `persistence_prev_day`. Write predictions with the baseline so Checkpoint A can happen.
- [ ] `ridge_poly`, `random_forest`, `hist_gradient_boosting`; walk-forward tuning inside train only; validation selection with the 3% simplicity rule.
- [ ] `ml/pipeline/train.py` -> models, `predictions_plant*.csv`, `model_metrics.json` (all keys from contract; real numbers).
- [ ] `ml/common/conformal.py` and the prediction interval used by `/predict` (90% coverage, bins of predicted power, calibrated on validation).
- [ ] Endpoints `/predict`, `/predictions/timeseries`, `/models`, `/models/performance`, `/models/residuals`, `/models/feature-importance`; add their exact JSON shapes to `ARCHITECTURE_AND_API.md` section 6 in your first PR.
- [ ] Mock JSON for every endpoint you own.
- [ ] Pages: Prediction (form with validation, result card with interval, warnings, actual vs predicted chart with inverter selector), Models (metrics table with val/test toggle and daylight/all toggle, bar chart of RMSE by model, residual plots, rolling-fold chart, breakdown by irradiation and day type, selected-model badge with reason).

**Phase 2 (Day 6 to 8)**
- [ ] Re-run the full pipeline on `main`; confirm Role 2 and 3 pipelines still run on your files.
- [ ] Compare robust training on/off and log the decision.
- [ ] Explain top features in plain language (permutation importance).

**Phase 3**
- [ ] Prepare to answer Mentor Q&A 1 to 8. Add a short "Model card" section to the README: data, features, split, metrics, limits.

## 5. Acceptance criteria

- Running `python -m ml.pipeline.build_dataset` then `python -m ml.pipeline.train` from a clean clone regenerates D1 to D5 with the same numbers (seed 42).
- Leakage and time-split tests pass; metrics include `all` and `daylight` for val and test, inverter level and `plant_level`.
- Test numbers are computed once per run and are not used for any selection logic (assert in code by structure, not by comment).
- `/predict` rejects out-of-range input with 422, returns the same output for the same input, returns 0 at night, includes `warnings` for extrapolation.
- No banned vocabulary; no hard-coded metrics in the UI.

## 6. Interfaces

- **You give Role 2 and 3:** `predictions_plant*.csv` (schema fixed), `ml/common/conformal.py`.
- **You give Role 4:** `selected.json` content and model metrics for `/meta` and the dashboard KPI card; keep `selected_model` and `test.daylight` keys stable.
- **You need nothing from others** except Role 4's shell and stubs for the pages; if the shell is late, build the page against the mock JSON in your own folder.

## 7. Pitfalls to avoid

- Shuffling or random `train_test_split`.
- Scaling or imputing with statistics computed on all data.
- Using `DC_POWER`, `DAILY_YIELD`, `TOTAL_YIELD`, lagged AC, or inverter id.
- Forward-filling power values; dropping night rows.
- Reporting only all-hours R2.
- Forgetting that the Plant 1 generation file uses a different date format.
- Predicting negative power.

## 8. Antigravity starter prompts

```
I am Role 1. Read AGENTS.md, docs/PROJECT_HANDBOOK.md, docs/roles/ROLE_1_ML_ENGINEER.md,
docs/DATA_AND_ML_SPEC.md sections 3-4. Implement ml/data/quality_flags.py exactly per section 4
with pytest tests on small hand-made DataFrames. Do not touch other folders. Run /resolve-doubt if unsure.
```
```
I am Role 1. Implement ml/pipeline/train.py per docs/DATA_AND_ML_SPEC.md sections 5-7:
chronological split, walk-forward tuning inside train only, validation selection with the 3% simplicity rule,
daylight and all-hours metrics, writes the files in docs/ARCHITECTURE_AND_API.md 3.2 and 3.5.
Add the leakage tests from section 6.8.
```
