# Data and ML Specification

> The method document. It tells you exactly **how** data is cleaned, how the model is built and evaluated,
> how deviations are detected and explained, and how money is computed.
> Starting values (thresholds etc.) are marked **[initial]**: Roles may tune them, but only by logging a `DECISION_LOG.md` entry with the evidence.

---

## 1. Principles

1. **Estimate expected output from conditions, not from the output itself.** The model sees weather and time only.
2. **Evaluate on the future.** All evaluation is chronological. The test block is touched once per pipeline run, never used for tuning.
3. **Everything learned comes from the past.** Scalers, bands, thresholds and percentiles are fitted on train or validation rows only.
4. **Deviation is a measurement, not a diagnosis.** We report evidence and confidence; we never assert an equipment fault.
5. **Daylight is what matters.** Night rows (all zeros) inflate R2, so daylight-only metrics are primary.

## 2. Constants (`ml/common/config.py`)

| Name | Value | Meaning |
|---|---|---|
| `SEED` | 42 | every random operation |
| `INTERVAL_H` | 0.25 | hours per row, kWh = kW x 0.25 |
| `DAYLIGHT_G` | 0.05 | kW/m2; "daylight" rows for metrics and anomaly eligibility |
| `NIGHT_G` | 0.01 | below this, predicted power is set to 0 |
| `TRAIN_FRAC`, `VAL_FRAC` | 0.70, 0.15 | share of calendar days; test = remainder |
| `PRED_INTERVAL_COVERAGE` | 0.90 | interval shown in `/predict` |
| `ANOMALY_BAND_COVERAGE` | 0.99 | band used to flag points |
| `MIN_EVENT_INTERVALS` | 3 | persistence rule (45 min) |
| `MAX_GAP_INTERVALS` | 1 | gap allowed when merging flagged runs |
| `FLEET_FRACTION` | 0.60 | share of inverters out of band for a plant-wide event |
| `PEER_LOW`, `PEER_HIGH` | 0.85, 1.15 | peer ratio limits |
| `FLATLINE_INTERVALS` | 8 | identical readings in daylight |
| `DEFAULT_TARIFF_INR_PER_KWH` | placeholder, set and sourced by the team | see D-009 |

## 3. Raw data and parsing rules (Role 1)

1. Read the four CSVs from `data/raw/`. Never edit them.
2. Parse `DATE_TIME` with explicit formats. Plant 1 generation uses day-first text (for example `15-05-2020 00:00`); the other files use ISO-like text (`2020-05-15 00:00:00`). Try the known format first and **assert zero parse failures**; do not use `dayfirst` guessing on mixed data.
3. Check and record in the EDA notebook and in `artifacts/processed/data_report.json`: date range, number of days, rows per file, inverters per plant (expected 22), duplicates, missing 15-minute slots per day, ranges of each column, maximum irradiation per day (to confirm units).
4. Drop exact duplicate rows. If the same `(plant, timestamp, inverter)` has conflicting values, keep the first and count them in `data_report.json`.
5. Rename to the contract columns (`ARCHITECTURE_AND_API.md` 3.1). Units stay as reported (kW, kWh, deg C, kW/m2) unless EDA proves otherwise; any rescaling is logged in `DECISION_LOG.md`.
6. Left-join weather onto generation on `(plant_id, timestamp)`. The weather `SOURCE_KEY` is a sensor id and is not used.

## 4. Cleaning and quality flags (Role 1)

- **Weather gaps:** linear interpolation in time for gaps of at most 2 intervals (30 min). Longer gaps stay empty and set `flag_missing_weather = True`. Rows with empty weather get **no prediction** (`ac_kw_pred` empty) and are not used for training or scoring.
- **Power values:** never forward-fill or interpolate power. Never drop night rows.
- **Flags** (contract 3.1): `flag_night_power`, `flag_flatline`, `flag_negative`, `flag_gap_before`, `flag_ac_dc_inconsistent`, `flag_missing_weather`, and `flag_any` = OR of all.
- **Capacity proxy** per plant = 99th percentile of `ac_kw` over train rows with irradiation >= `DAYLIGHT_G`. It is used only to normalize (nMAE, minimum absolute band width, flag thresholds). It is not the plant's rated capacity.
- **DC-to-AC check:** compute `dc_ac_ratio = dc_kw / ac_kw` for rows with `ac_kw` >= 5% of capacity proxy. Compare each inverter with **its own train-period median ratio** (so any unit scaling, such as DC reported about 10x AC in Plant 1, cancels out). `flag_ac_dc_inconsistent` marks rows where AC exceeds DC after that normalization by more than 5%.
- **Data-quality score** = 100 x (rows with `flag_any == False`) / (all rows), per plant and per period.
- **Energy reconciliation** (Role 3 reports): per inverter and day, `max(daily_yield_kwh)` versus `sum(ac_kw) x 0.25`. Report the median ratio and its spread. We do not assume which one is "right".

## 5. Features for the expected-power model (Role 1)

Computed on the **plant-level weather series reindexed to a full 15-minute grid**, then joined to inverter rows. Trailing windows only.

| Feature | Definition |
|---|---|
| `irradiation_kw_m2` | G at time t |
| `module_temp_c`, `ambient_temp_c` | measured |
| `temp_delta_c` | module minus ambient |
| `hour_sin`, `hour_cos` | `sin/cos(2*pi*minute_of_day/1440)` |
| `irr_lag1` | G at t-1 interval |
| `irr_diff1` | G(t) - G(t-1) |
| `irr_roll_mean_4`, `irr_roll_std_4` | trailing mean and std over the last 4 intervals including t |
| `irr_x_modtemp` | G x module temperature |

Missing lag/rolling values (first rows, gaps): tree models receive NaN; linear models get `irr_lag1 = G`, `irr_diff1 = 0`, rolling values filled from the available window.

**Forbidden as model inputs (tested):** `dc_kw`, `daily_yield_kwh`, `total_yield_kwh`, any lag or rolling statistic of `ac_kw`, `inverter_id` (and any one-hot of it), date, day index, row index, `plant_id` (one model per plant instead).

Why: using DC or lagged AC would make the model re-state the output it should estimate and hide deviations; using inverter id would let the model learn each inverter's own low output as "normal".

## 6. Split and validation protocol (Role 1)

1. Take the sorted list of calendar days present in the data. `n_train = floor(0.70 n)`, `n_val = floor(0.15 n)`, `test` = remaining days. With 34 days this is about 23 or 24 train, 5 val, 5 to 6 test. Both plants use the same day boundaries. Write them into `model_metrics.json`.
2. `split` column in predictions = block of the row's day.
3. **Tuning** (hyper-parameters, feature on/off): walk-forward folds **inside the train block only**: train on the first 12 days, test on the next 3; then 15 -> 3; 18 -> 3; 21 -> 3 (expanding window). Pick the setting with the lowest mean daylight RMSE.
4. **Model selection:** compare models on the **validation** block by daylight RMSE. If a simpler model is within 3% of the best, choose the simpler one (simplicity order: physics, ridge_poly, hist_gradient_boosting, random_forest). Record `selection_reason`.
5. **Test:** report once after selection. Never change anything after seeing test numbers; if something is changed anyway, log it as a decision and say so in the report.
6. **Rolling-origin report** (reporting only, no tuning): train on all days before day k, predict days k to k+2, for k = 15, 18, 21, ... Report per-fold daylight RMSE to show stability across time. Stored as `walk_forward` in the metrics file.
7. **Deployment fit:** all predictions in `predictions_plant{N}.csv` come from the **train-only** fit so that val and test remain strictly unseen (D-006). `train` rows are in-sample and the UI labels them.
8. **Leakage tests** (pytest): feature list has no forbidden names; `max(train day) < min(val day) <= max(val day) < min(test day)`; changing test rows does not change any fitted parameter, band or threshold.

## 7. Models and metrics (Role 1)

Trained **per plant**, on inverter-level rows with `irradiation >= NIGHT_G`, `flag_any == False`, weather present. Predictions are clipped at 0 and set to 0 when `irradiation < NIGHT_G`.

**Robust training [initial]:** drop training rows whose peer ratio (inverter AC / fleet median AC at the same timestamp, when the median is at least 5% of capacity proxy) is below 0.7 or above 1.3, so persistently low inverters do not drag "normal" down. Report metrics with and without this rule in the EDA notebook and log the chosen option.

| Name | Description |
|---|---|
| `persistence_prev_day` | same inverter, same time of day, previous day (uses actual history; reference only, not a weather model) |
| `physics_baseline` | `P = a * G * (1 + gamma * (T_module - 25))`, fit `a >= 0`, `gamma in [-0.01, 0]` by least squares on train daylight rows |
| `ridge_poly` | scaler + degree-2 polynomial on `G, T_module, T_ambient, temp_delta, hour_sin, hour_cos` + Ridge (alpha tuned) |
| `random_forest` | 200 trees, `min_samples_leaf` 5, `max_depth` about 12 |
| `hist_gradient_boosting` | scikit-learn `HistGradientBoostingRegressor`, monotonic increasing constraint on irradiation, small grid on learning rate, depth, iterations |

**Metrics** (inverter level and plant level; plant level = sum over inverters at timestamps where at least 90% of inverters have a valid row; `plant_level` is an additive key in the metrics file):
- MAE (kW), RMSE (kW), R2, WAPE = sum|error| / sum(actual), nMAE = MAE / capacity proxy.
- Two views: `all` (all rows with prediction) and `daylight` (irradiation >= 0.05, `flag_any == False`). **Daylight is primary.**
- Breakdowns on the test block: by irradiation bin (0.05-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8+), by hour of day, by day type (clear/mixed/cloudy, section 12).
- Permutation importance on validation rows (5 repeats, seed 42).
- Baseline sanity: `physics_baseline` and ridge must beat `persistence_prev_day` on cloudy days or we explain why not.

## 8. Prediction bands and point flags (Role 2)

Input: `predictions_plant{N}.csv`. Shared helper `ml/common/conformal.py` (Role 1 provides; Role 2 may keep a local copy until it exists).

1. `residual = ac_kw_actual - ac_kw_pred`, `rel_dev = residual / max(ac_kw_pred, 0.05 * capacity)`.
2. **Eligible rows:** `irradiation >= 0.05`, weather present, `ac_kw_pred >= 0.05 * capacity`.
3. **Calibration rows:** `split == val`, eligible, `flag_any == False`, peer ratio in [0.7, 1.3].
4. Make 8 quantile bins of `ac_kw_pred` on calibration rows. In each bin, `q_b` = split-conformal quantile of `|residual|` at `ANOMALY_BAND_COVERAGE` (the `ceil((n+1)*coverage)/n` empirical quantile). Use `max(q_b, 0.02 * capacity)`.
5. Band for any row: `band_lo = max(0, pred - q_b)`, `band_hi = pred + q_b` using the bin of its prediction. Save edges and `q_b` to `artifacts/anomalies/band_params_plant{N}.json`.
6. `z_robust = residual / (1.4826 * MAD_b)` where `MAD_b` is the median absolute deviation of calibration residuals in that bin.
7. `is_outlier = actual < band_lo or actual > band_hi` on eligible rows.
8. **Stability check:** the outlier rate in `val` should be about `1 - coverage` (that is expected by construction); the outlier rate in `test` is the real check. Report both in `/anomalies/validation`. A much higher test rate means the model or bands do not generalize and must be discussed honestly.

**Events (persistence rule):** per inverter, join consecutive outlier points of the same sign allowing a gap of `MAX_GAP_INTERVALS`; keep runs with at least `MIN_EVENT_INTERVALS` points.

**Plant-wide events:** at each timestamp compute the share of eligible inverters outside the band with the same sign. Runs of at least 3 intervals where the share is at least `FLEET_FRACTION` become events with `inverter_id = FLEET`. Per-inverter events that are at least 80% covered by a FLEET event are dropped (represented by the FLEET event).

**Event measures:** `energy_delta_kwh = sum(residual) x 0.25`; `energy_vs_band_kwh` = `sum(actual - band_lo)` for shortfall or `sum(actual - band_hi)` for surplus (over the event rows, x 0.25); `mean_rel_dev`, `peak_rel_dev`.

**Severity [initial]:** `score = mean(|rel_dev|) x min(duration_min / 60, 4)`; `low` < 0.15, `medium` 0.15 to < 0.5, `high` >= 0.5.

## 9. Evidence ladder: category and confidence (Role 2)

Signals computed for each event (values saved in `evidence_json`):

| Signal | Definition [initial] |
|---|---|
| `S_dq` data-quality | `flag_any` true on at least 30% of event rows, or power above 0 while irradiation is below 0.01, or a flat-lined run |
| `S_peer` | median peer ratio over the event <= 0.85 (shortfall) or >= 1.15 (surplus), **and** fleet median residual inside the band for at least 70% of event rows |
| `S_recur` | the same inverter has `S_peer` events on at least 2 different days |
| `S_dcac` | the inverter's DC/AC ratio during the event differs from its own train median by more than 3 robust SD |
| `S_vol` | trailing irradiation volatility (`irr_roll_std_4`) during the event is above the 75th percentile of train daylight values |
| `S_fleet` | share of inverters outside the band with the same sign >= `FLEET_FRACTION` during at least half of the event |

**Category (first match wins):**
1. `data_quality` if `S_dq`
2. `inverter_specific` if `S_peer` and not `S_fleet`
3. `weather_transient` if `S_vol`
4. `fleet_wide` if `S_fleet`
5. `unexplained` otherwise

**Confidence:**
- `inverter_specific`: count corroborating signals among {`S_recur`, `S_dcac`, duration >= 120 min}: 0 -> `low`, 1 -> `medium`, 2 or more -> `high`.
- `weather_transient`: `high` if also `S_fleet`, else `medium`.
- `fleet_wide`: `medium` if duration >= 120 min, else `low`.
- `data_quality`: `high` if flags cover at least 70% of event rows, else `medium`.
- `unexplained`: always `low`.

**`confirm_with` per category** (shown in the UI as "What would confirm this"):
- `inverter_specific`: `maintenance_log`, `alarm_codes`, `string_level_current_data`, `site_inspection`
- `fleet_wide`: `grid_outage_or_curtailment_records`, `sensor_calibration_record`
- `weather_transient`: `co_located_second_irradiance_sensor`, `satellite_cloud_data`
- `data_quality`: `scada_communication_log`, `sensor_calibration_record`
- `unexplained`: `maintenance_log`, `site_inspection`, `additional_sensor_data`

**Soiling and degradation** are not categories. The History page can show a Performance Index trend; the UI text may only say "possible soiling, needs cleaning and rainfall records".

## 10. Injection benchmark (Role 2)

Goal: prove the detector works without labels, on unseen data.

1. Use `split == test` rows of a plant. Fix the seed.
2. For each scenario, choose 30 random `(inverter, start)` windows where irradiation >= 0.3 for the whole window and no existing event overlaps. Scenarios: multiplicative drop of 10%, 20%, 40% for 2 hours; spike of +30% for 1 hour; flat-line (hold the first value) for 2 hours.
3. Apply the change to a copy of `ac_kw_actual`, recompute residuals with the **same bands** (fitted on validation), rebuild events with the same rules, and match events to injected windows (overlap of at least 50% of the injected window).
4. Report per scenario: `n_injected`, `recall`, `precision` (events overlapping injected windows divided by those plus new events that overlap no injected window and did not exist before injection), and the median detection delay in minutes (first event interval minus injection start; the persistence rule makes the minimum 30 minutes).
5. Output: the drop sweep gives a "minimum detectable deviation" curve. Show it in the UI. Save to `artifacts/anomalies/injection_benchmark.json`.

## 11. Finance formulas (Role 3)

All energy in kWh, money in INR, `tariff` from the request (default from `/meta`).

- `central_kwh` = sum over **shortfall** events with category != `data_quality` of `-energy_delta_kwh`.
- `conservative_kwh` = same set, using `-energy_vs_band_kwh` (only the part beyond the normal band).
- `data_quality_kwh` = sum over shortfall events with category == `data_quality` of `-energy_delta_kwh` (excluded: the reading itself may be wrong).
- `upper_kwh` = `central_kwh + data_quality_kwh`.
- `inr = kwh x tariff` for each tier. `by_category` uses the central measure.
- `surplus` = sum of `energy_delta_kwh` over surplus events x tariff, reported separately and **never netted**.
- Period filters use the event start date. `period_days` = number of distinct days in the selected range.
- Sensitivity: INR for tariffs from 50% to 150% of the default in 9 steps.
- Always show the note: indicative, selected period only, not an annual forecast, tariff is an assumption.
- Reconcile in a test: `central <= upper` and `conservative <= central`.

## 12. Weather analysis (Role 2)

Daylight rows (`irradiation >= 0.05`, `flag_any == False`).
- **Binned relationship:** 20 irradiation bins; per bin the median and 10th/90th percentile of AC per inverter, and count.
- **Correlations:** Pearson and Spearman of `ac_kw` with irradiation, module temperature, ambient temperature; give n and say that correlations are associations.
- **Temperature effect:** performance ratio `PR = ac_kw / (capacity_proxy x G)` for `G >= 0.4`. Fit `PR ~ a + b x (T_module - 25)`; report `b / a` in %/deg C with a bootstrap 95% interval (resample days). Add the caution that temperature and time of day are correlated, so this is an estimate, not a controlled measurement.
- **Variability:** per day `VI = std(diff(G)) / mean(G)` over daylight rows and the daily irradiation total. **Day type:** `clear` if the daily total is at least 80% of the largest day and `VI` is at most the median `VI`; `cloudy` if the total is below 60% of the largest day or `VI` is at or above the 75th percentile; otherwise `mixed`.
- Every chart gets an auto-generated insight sentence built from the computed values.

## 13. History analysis (Role 3)

- Daily energy actual (`sum ac_kw x 0.25`) and expected (`sum ac_kw_pred x 0.25` on the same rows), **Performance Index** `PI = actual / expected` on rows with `flag_any == False`. Missing intervals are counted and shown.
- Heatmap: date x hour energy (kWh) per plant.
- Diurnal curve: mean and 10th/90th percentile of plant power per time-of-day.
- Inverter ranking: energy, mean peer ratio, share of time below `PEER_LOW`, number of events, reconciliation ratio.
- All endpoints take `split` and date filters.

## 14. Reproducibility and quality

- Pin versions in `requirements.txt`. `SEED = 42` everywhere (numpy, scikit-learn, bootstrap, injection).
- Each stage is one command (`AGENTS.md` section 7), reads inputs from the previous stage's artifacts, and writes a small `*_run.json` with timestamp, git commit if available, and parameters.
- Tests: schema tests for every artifact (columns, types, allowed enums), leakage tests, formula tests on tiny hand-made frames, and a "no banned vocabulary" grep test over `backend/`, `frontend/src/`, `ml/` and `artifacts/**/*.json`.
- Notebooks are for exploration. Anything the app depends on lives in `ml/` as importable code.
