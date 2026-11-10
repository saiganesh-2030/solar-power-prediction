# ROLE 3 — Analytics and Finance Engineer (Historical Analysis, Financial Impact)

**Owner:** ____________
**Features:** 5 Historical Analysis, 7 Financial Impact Analysis
**Read first:** `AGENTS.md`, `docs/PROJECT_HANDBOOK.md` sections 5 (features 5 and 7), 8, 9; `docs/DATA_AND_ML_SPEC.md` sections 4 (reconciliation), 11, 13; `docs/ARCHITECTURE_AND_API.md` sections 3.2 to 3.4, 4 to 7.

## 1. Mission

Show how the plant behaved over time (days, hours, inverters) and translate deviations into energy and money with honest ranges. You turn the technical results into something an operator or a manager understands, and you make sure no number is over-claimed.

## 2. You own (read and write)

```
ml/history/   ml/finance/
backend/app/routers/history.py   backend/app/routers/finance.py
backend/app/schemas/history.py   backend/app/schemas/finance.py
backend/app/services/history_service.py   backend/app/services/finance_service.py
frontend/src/pages/history/   frontend/src/pages/finance/
frontend/public/mock/history*.json   finance*.json
tests/unit/ml_history/   tests/unit/ml_finance/
```
Your logic is computed **on request** from `predictions_plant*.csv` and `events_plant*.csv` (no new artifacts needed). Optionally cache in memory.

## 3. Deliverables (exact)

| # | Deliverable | Notes |
|---|---|---|
| D1 | `ml/history/aggregations.py` | daily energy, Performance Index, heatmap matrix, diurnal curve, inverter ranking, reconciliation |
| D2 | `ml/finance/impact.py` | tiers, categories, surplus, sensitivity (Spec 11) |
| D3 | Endpoints 17 to 22 | Architecture section 5 |
| D4 | History page | daily bars, heatmap, diurnal curve with band, inverter ranking table, plant comparison |
| D5 | Finance page | tier cards, category breakdown, tariff input, sensitivity chart, surplus card, note |
| D6 | Tariff proposal | a sourced value recorded in `DECISION_LOG.md` D-009 (Phase 1) |

## 4. How to start without waiting

- Use `artifacts/_stub/predictions_plant*.csv` and `artifacts/_stub/events_plant*.csv` (Role 4, Day 1).
- Write finance functions as pure functions over DataFrames, test them with 5 to 10 hand-made rows where you know the answer by hand.
- Switch to real artifacts at Checkpoint A (predictions) and when Role 2 delivers events (their first run, even with preliminary thresholds).

## 5. Task list

**Phase 1 (Day 2 to 5)**
- [ ] Propose the tariff value and its source; update D-009; put the default in `ml/common/config.py` (coordinate: Role 1 owns the file, so open a one-line PR) or read it from the environment, and expose through `/meta` via Role 4.
- [ ] `aggregations.py` (Spec 13): daily actual and expected kWh, PI on rows with `flag_any == False`, missing interval counts, heatmap (date x hour), diurnal mean and 10th/90th percentiles, inverter ranking (energy, mean peer ratio, share below `PEER_LOW`, events, reconciliation ratio).
- [ ] `impact.py` (Spec 11) with tests: `conservative <= central <= upper`; surplus never netted; tariff scales INR linearly; empty period returns zeros.
- [ ] Add exact JSON shapes for endpoints 17 to 22 to `ARCHITECTURE_AND_API.md` section 6 in your first PR (finance example is already there).
- [ ] Mock JSON for each endpoint.
- [ ] History page and Finance page against mocks, then real endpoints.
- [ ] Plain-language captions ("How to read this chart") and the finance disclaimer: indicative, selected period only, not an annual forecast, tariff is an assumption.

**Phase 2 (Day 6 to 8)**
- [ ] Verify with real data: daily kWh equals integrated AC power; reconciliation ratio displayed and explained; totals agree with the dashboard (coordinate with Role 4's sums).
- [ ] Check that finance numbers match a manual spreadsheet calculation for one day (put this check into a test).
- [ ] Add a "Performance Index trend" insight text (only wording: "possible soiling, needs cleaning and rainfall records" if the trend declines).

## 6. Acceptance criteria

- Formulas exactly as in Spec 11 and 13; unit tests prove them on hand-made data.
- Changing the tariff changes only INR values, never kWh.
- Data-quality events are excluded from central and conservative, included only in upper, and shown separately in `excluded`.
- Surplus is reported separately and not subtracted.
- Missing intervals are visible; no silent interpolation of power.
- All text follows the vocabulary policy; the INR values are formatted with the rupee sign and 2 decimals; kWh with thousands separators.
- Every page works in mock mode and with real data, with loading, empty and error states.

## 7. Interfaces

- **You consume:** predictions (Role 1), events (Role 2).
- **You provide Role 4:** `finance.impact` function (pure) so the dashboard can show the same shortfall range; Role 4 may import `ml.finance.impact` directly, so keep its signature stable: `compute_impact(events_df, tariff, period) -> dict`.
- **You never need** Role 1's or 2's code beyond reading their files.

## 8. Pitfalls to avoid

- Netting surplus against shortfall.
- Annualising 34 days into a yearly loss.
- Counting data-quality events as confirmed loss.
- Different "total kWh" than the dashboard (agree on `sum(ac_kw) x 0.25`).
- Mixing time zones or shifting timestamps in the heatmap.
- Interpolating missing intervals silently.
- Presenting the tariff as a fact.

## 9. Antigravity starter prompts

```
I am Role 3. Read AGENTS.md, docs/PROJECT_HANDBOOK.md, docs/roles/ROLE_3_ANALYTICS_FINANCE.md,
docs/DATA_AND_ML_SPEC.md section 11. Implement ml/finance/impact.py with pytest tests on hand-made event tables
(shortfall, surplus, data_quality). Check conservative <= central <= upper. Do not touch other roles' folders.
```
```
I am Role 3. Build frontend/src/pages/history/ against frontend/public/mock/history-daily.json and history-heatmap.json
using the shared API client and chart components. Include loading, empty and error states and a "How to read this chart" caption per chart.
```
