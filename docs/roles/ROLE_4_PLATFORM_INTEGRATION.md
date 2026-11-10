# ROLE 4 — Platform and Integration Lead (API Core, App Shell, Dashboard, QA, Docs)

**Owner:** ____________
**Features:** 1 Dashboard Overview + the shared platform every other feature runs on
**Read first:** `AGENTS.md`, all of `docs/` (you are the keeper of contracts), especially `docs/ARCHITECTURE_AND_API.md`, `docs/TEAM_WORKFLOW.md`.

## 1. Mission

Make it possible for three people to work in parallel and for the pieces to fit on the first try: scaffold, stubs, mocks, shared components, API core, dashboard, Postman, integration tests, release. You are also the merge owner and the guardian of the contracts.

**Your Day-0/1 work unblocks everyone. Do it first and push to `main` early, even if rough.**

## 2. You own (read and write)

```
backend/app/main.py   backend/app/core/ (config.py, data_store.py, errors.py, schemas_common.py)
backend/app/routers/meta.py   backend/app/routers/dashboard.py
backend/app/schemas/common.py (re-exports schemas_common.py)   backend/app/schemas/dashboard.py   backend/app/services/dashboard_service.py
frontend/index.html  vite.config.js  package.json
frontend/src/main.js   router.js   styles/   api/client.js   state/filters.js   components/   pages/dashboard/
frontend/public/mock/dashboard*.json   meta.json
scripts/make_stub_artifacts.py
postman/
tests/integration/
requirements.txt  .gitignore  README.md
docs/  (upkeep: ARCHITECTURE_AND_API.md, TEAM_WORKFLOW.md, DECISION_LOG.md)
```
You review and merge PRs. You are the only person who changes `core/` and `components/`; others request changes by PR or message.

## 3. Deliverables

| # | Deliverable | When |
|---|---|---|
| D1 | Repo skeleton from Architecture section 2, `.gitignore`, pinned `requirements.txt`, `frontend/package.json` | Day 0 |
| D2 | Backend: app factory, CORS, error envelope, `core/data_store.py`, `/health`, `/meta`; router registration that tolerates a missing router file | Day 1 |
| D3 | `scripts/make_stub_artifacts.py` -> `artifacts/_stub/` with **all** schemas in Architecture section 3 (synthetic but plausible; bell-shaped daily curve, 22 inverters, a few injected dips; events with every category) | Day 1 |
| D4 | Frontend shell: hash router, nav, layout, theme (light and dark), `api/client.js` with mock mode, `state/filters.js`, shared components (`kpiCard`, `lineChart`, `barChart`, `heatmap`, `dataTable`, `filterBar`, `badge`, `banner`, `skeleton`) | Day 1 to 2 |
| D5 | Dashboard endpoint and page (Handbook feature 1) | Day 3 to 5 |
| D6 | Postman collection + environment, one folder per router, tests for status and envelope | grows daily; green by Day 6 |
| D7 | Integration tests: totals equal CSV sums; every endpoint returns envelope; banned-vocabulary grep; contract schema checks | Day 5 to 7 |
| D8 | README with setup, screenshots, demo script; docs kept in sync | Day 8 to 10 |

## 4. Details of the key pieces

**`core/data_store.py`** (the only place that reads artifacts)
- Loads CSV/JSON at start-up from `ARTIFACT_DIR` (default `artifacts/`; set to `artifacts/_stub` for stubs). If a real file is missing, fall back to the stub file of the same name and mark `meta.source` as `"stub"`; if neither exists, raise `artifact_missing`.
- Provides typed accessors: `get_predictions(plant, start, end, inverter, split)`, `get_events(...)`, `get_point_flags(...)`, `get_metrics()`, `get_band_params(plant)`.
- Never mutates data returned to callers (copy or read-only views).

**`/meta`**: plants, inverter ids per plant, date range, split dates, selected model per plant, tariff default, `data_version` (hash or mtime of artifacts), `source` (`artifacts` or `stub`).

**Dashboard** (`/dashboard/overview`, Architecture section 6):
- `actual_kwh = sum(ac_kw_actual) x 0.25`, `predicted_kwh = sum(ac_kw_pred) x 0.25` over the same rows (rows with a prediction).
- `deviation_pct = (actual - predicted) / predicted x 100`.
- Anomaly counts from `events_plant*.csv`; shortfall tiers via `ml.finance.impact.compute_impact` (Role 3) or, until it exists, a local stub function marked TODO.
- `data_quality_score = 100 x share(flag_any == False)`.
- `top_candidates`: inverters with the most `inverter_specific` shortfall events in the period (shown with confidence). Title it "Candidates for inspection", never "faulty inverters".
- Plant time series: sum over inverters per timestamp.
- Respect `split`: when "Unseen test period only" is on, filter to `split == test`.

**`api/client.js`**: `get`, `post`, query builder, envelope parser, `ApiError`, mock mode, timeout and one retry for GET.

**Filters state**: `plant`, `start`, `end`, `testOnly`; synced to the URL query; emits a change event the pages subscribe to.

## 5. Quality gates (you run these before every merge to `main`)

1. `pytest -q` passes (includes leakage test imports from Role 1 once available).
2. `npm run build` passes; the app runs in mock mode and against the backend.
3. Postman collection passes (runner or Newman).
4. Banned-vocabulary grep: no "fault", "failure", "defective", "broken", "malfunction" in `backend/`, `frontend/src/`, `ml/`, `artifacts/**/*.json`, `frontend/public/mock/`.
5. No contract drift: JSON key sets of responses match `ARCHITECTURE_AND_API.md` (schema tests).
6. PR checklist in `TEAM_WORKFLOW.md` section 4 satisfied.

## 6. Integration schedule (you drive)

- **Checkpoint A (Day 3):** Role 1's first `predictions_plant*.csv` is in `main`. You switch `ARTIFACT_DIR` to real, run the backend and dashboard smoke test, and post results in the team channel.
- **Checkpoint B (Day 6):** all 7 pages load with real data; Postman green; list mismatches by owner.
- **Freeze (2 days before deadline):** only bug fixes.
- **Release:** tag `v1.0`, final README and screenshots, rehearse the demo (Handbook section 11).

## 7. Acceptance criteria

- A teammate can clone, run the documented commands, and see the app in under 10 minutes using stubs, and with real data once Role 1's artifacts exist.
- Dashboard totals equal sums computed independently from the CSV in a test.
- Changing the filter bar updates every card and chart on the dashboard.
- Errors from the API show a readable banner with retry; the app never shows a blank page.
- Responsive layout down to a laptop width; keyboard focus visible; colour-blind-safe palette; light and dark mode.
- No inline `fetch` outside `client.js`; no `innerHTML` with API strings.

## 8. Pitfalls to avoid

- Waiting to be perfect before pushing the scaffold (others are blocked until you do).
- Letting stub data look "too real" so that people forget which mode they are in (show a "Stub data" banner when `meta.source == "stub"`).
- Changing a contract without the PR + decision log + mock + Postman update.
- Summing across inverters with missing rows without saying so.
- Two different definitions of "total kWh" across pages.

## 9. Antigravity starter prompts

```
I am Role 4. Read AGENTS.md, docs/PROJECT_HANDBOOK.md, docs/roles/ROLE_4_PLATFORM_INTEGRATION.md and
docs/ARCHITECTURE_AND_API.md. Create scripts/make_stub_artifacts.py that writes artifacts/_stub/ files with exactly
the schemas in section 3 (both plants, 22 inverters, 34 days at 15-minute resolution, synthetic bell-shaped curves with noise,
a few injected dips, events covering all five categories). Seed 42. Add a schema test.
```
```
I am Role 4. Scaffold frontend/ with Vite and vanilla JS: hash router, nav, light and dark theme, src/api/client.js
with mock mode (VITE_USE_MOCK), state/filters.js synced to the URL, and shared components listed in the role file.
No frameworks. Every page needs loading, empty and error states.
```
