# Team Workflow

> How four people build one project in parallel without waiting for each other.

---

## 1. Roles at a glance

| Role | Name (fill in) | Features owned | Main folders | Role file |
|---|---|---|---|---|
| 1 ML Engineer | ________ | 2 Prediction, 6 Model Performance | `ml/data`, `ml/features`, `ml/models`, `ml/pipeline`, routers `predict`, `models`, pages `prediction`, `models` | `docs/roles/ROLE_1_ML_ENGINEER.md` |
| 2 Anomaly and Weather Engineer | ________ | 3 Anomaly Detection, 4 Weather Analysis | `ml/anomaly`, `ml/weather`, routers `anomalies`, `weather`, pages `anomalies`, `weather` | `docs/roles/ROLE_2_ANOMALY_WEATHER.md` |
| 3 Analytics and Finance Engineer | ________ | 5 Historical Analysis, 7 Financial Impact | `ml/history`, `ml/finance`, routers `history`, `finance`, pages `history`, `finance` | `docs/roles/ROLE_3_ANALYTICS_FINANCE.md` |
| 4 Platform and Integration Lead | ________ | 1 Dashboard Overview, app shell, API core, QA | `backend/app/core`, `main.py`, routers `meta`, `dashboard`, `frontend/src` shell and components, `scripts/`, `postman/`, `tests/integration` | `docs/roles/ROLE_4_PLATFORM_INTEGRATION.md` |

Each role owns a **vertical slice**: data logic -> API router -> UI page. That keeps hand-offs to a few files instead of constant conversation.

## 2. How we avoid depending on each other

1. **Contract first.** Schemas and endpoints are already written in `docs/ARCHITECTURE_AND_API.md`.
2. **Stub artifacts.** Role 4 generates `artifacts/_stub/` (synthetic files with the real schemas) on Day 1. Everyone can develop against them. Setting `ARTIFACT_DIR=artifacts/_stub` (env var) switches the backend to stubs; the default is `artifacts/`.
3. **Mock mode.** The frontend works without a backend (`VITE_USE_MOCK=true`) using `frontend/public/mock/*.json`. Each role writes the mock JSON for its own endpoints (copied from the contract examples).
4. **Own your folders.** Two people never edit the same file. Shared files (`ARCHITECTURE_AND_API.md`, `core/`, `components/`) change only by PR with the owner (Role 4) approving.
5. **No waiting rule.** If you need something from a teammate that is not ready, use the stub, mock it locally, or write a 20-line local version inside your own folder; swap later. Do not block.

### Dependency map (who needs what, and the fallback)

| Needs | From | Real source | Fallback until ready |
|---|---|---|---|
| `merged_plant*.csv`, `predictions_plant*.csv` | Role 1 | `artifacts/` | `artifacts/_stub/` (Role 4, Day 1) |
| `events_plant*.csv`, `point_flags_*.csv` | Role 2 | `artifacts/anomalies/` | stub events (Role 4) |
| `ml/common/conformal.py` | Role 1 | repo | local copy in `ml/anomaly/` |
| Shared UI components, api client | Role 4 | `frontend/src` | build locally in own page folder |
| Endpoint JSON shape | owner of endpoint | `ARCHITECTURE_AND_API.md` | follow the contract examples |

Direction of data flow is one way: **Role 1 -> Role 2 -> Role 3**, with Role 4 reading everything. Because the file schemas are fixed, each downstream role can start on Day 1 with stubs.

## 3. Phases (map to your real deadline; shown as relative days)

**Phase 0 — Foundation (Day 0 to 1, everyone, about half a day together)**
- Create repo structure from `ARCHITECTURE_AND_API.md` section 2; copy these docs and `AGENTS.md`, `.agents/`.
- Everyone reads: Handbook, Architecture and API, their own role file. Everyone fills in names in section 1 above.
- Role 4: backend skeleton (`/health`, `/meta`), frontend shell, `scripts/make_stub_artifacts.py`, push to `main`.
- Role 1: download data into `data/raw/`, start EDA.
- Everyone: create branch `role<n>/...` from `main`.

**Phase 1 — Build the slice (Day 2 to 5, in parallel)**
- Role 1: dataset build, quality flags, baselines and models, metrics, `predictions_plant*.csv`; `/predict` and `/models/*`.
- Role 2: bands, point flags, events, attribution on stub data first, then real predictions; injection benchmark; weather analysis.
- Role 3: history aggregations, finance formulas with unit tests on tiny frames; pages with stub data.
- Role 4: dashboard page, shared components, Postman collection, integration tests, data-quality score.
- **Checkpoint A (end of Day 3):** Role 1 pushes first real `predictions_plant*.csv` (even from the simple baseline). Others switch from stub to real for a smoke test.

**Phase 2 — Integrate (Day 6 to 8)**
- Run the real pipeline end to end; fix schema mismatches.
- **Checkpoint B (Day 6):** all 7 pages render with real data; Postman collection green.
- Role 2 and Role 3 re-run with the final selected model; Role 4 verifies dashboard totals against CSV sums.

**Phase 3 — Polish and defend (Day 9 to 10)**
- Docs, screenshots, README, demo rehearsal; mentor Q&A practice (`docs/MENTOR_QA.md`).
- Freeze features 2 days before the deadline; only bug fixes after the freeze.

## 4. Git rules

- Branches: `main` (always runnable), feature branches `role<n>/<topic>`, for example `role2/event-attribution`.
- Commits: `<area>: <imperative summary>` such as `anomaly: add conformal band calibration`.
- PRs: small (under about 400 changed lines when possible), one concern, a short description with "What / Why / How to test / Docs touched".
- Review: one teammate reviews every PR within a day; Role 4 merges. Nobody pushes directly to `main` after Phase 0.
- Merge conflicts: pull `main` into your branch daily. Because folders are owned, conflicts should be rare.
- Never commit: `data/raw/`, `.venv/`, `node_modules/`, secrets. Do commit: small artifacts under `artifacts/` (target under 15 MB total) and mock JSON.
- If a contract must change: PR touching `ARCHITECTURE_AND_API.md` + `DECISION_LOG.md`, tagged `contract` in the title, approved by the affected roles.

### PR checklist (copy into the PR description)

- [ ] Stayed inside owned folders (or explained why not)
- [ ] No contract change (or contract PR linked)
- [ ] Tests added or updated and passing
- [ ] No leakage features, no banned vocabulary, no hard-coded results
- [ ] Works in mock mode (frontend) or with stub artifacts (backend)
- [ ] Postman request added or updated (endpoints)
- [ ] Docs updated (this file or the relevant spec) if behaviour changed

## 5. Definition of Done for any task

Code runs from a clean clone with the documented commands; tests pass; loading/empty/error states exist; numbers come from data; a teammate reviewed it; docs updated; decision logged if you chose something not in the docs.

## 6. Communication

- Daily 10-minute stand-up: yesterday / today / blocked (only the **blocked** part needs discussion).
- A shared chat channel with these pins: repo link, `AGENTS.md`, this file.
- Ask the doubt in the open: if Antigravity or a teammate is unsure, run `/resolve-doubt`, then post the outcome (or the `PROPOSED` decision) in the channel.
- Weekly (or every 3 days) 30-minute integration call at each checkpoint.

## 7. Using Antigravity well

**Where the files go (Antigravity reads them automatically in the workspace):**
- `AGENTS.md` at the repository root (supported by recent Antigravity versions; if your version does not pick it up, copy the same file to `GEMINI.md` in the root).
- Rules: `.agents/rules/` (current docs use this name; some older guides use `.agent/rules/`). The safest way: open Antigravity -> Customizations -> Rules -> **+ Workspace**, create one rule to see which folder it uses, and place `solar-guardrails.md` there. Set it to **Always On**.
- Workflows: `.agents/workflows/resolve-doubt.md`; run it in chat with `/resolve-doubt`.
- Each rule or workflow file must stay under 12,000 characters (Antigravity limit). Keep the long material in `docs/`, which the agent opens on demand.
- The agent does not always open `docs/` by itself. Start sessions with the prompt templates below, which point it to the right files, or mention files with `@docs/PROJECT_HANDBOOK.md`.

**Starter prompt (paste at the start of a session; replace N):**
```
I am Role N in this project. Read AGENTS.md, docs/PROJECT_HANDBOOK.md and docs/roles/ROLE_N_*.md first.
Then read docs/ARCHITECTURE_AND_API.md (contracts) and docs/DATA_AND_ML_SPEC.md (method) for anything I ask that touches data, models or endpoints.
Work only in my owned folders. Follow the non-negotiables. If anything is unclear, run /resolve-doubt before coding.
My task now: <one specific task from my role file>.
```

**Good task sizes for the agent:** "implement `ml/data/quality_flags.py` per spec section 4 with unit tests", "build the anomalies list page against `public/mock/anomalies.json`". Avoid "build the whole project".

**Always review agent output for:** forbidden features, shuffled splits, renamed columns, hard-coded numbers, the word "fault", changes outside your folders.

## 8. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Role 1 pipeline late | medium | high | stubs + Checkpoint A with a baseline model first |
| Date parsing or missing-data surprises | high | medium | explicit formats, asserts, `data_report.json`, EDA early |
| Model does not generalize to test days | medium | medium | report honestly; show walk-forward; simpler model preferred |
| Too many events (noisy detector) | medium | medium | persistence rule, 99% band, tune only via logged decisions |
| Scope creep | high | high | stretch items only after Definition of Done; freeze 2 days before |
| Agent edits outside scope / invents numbers | medium | medium | `AGENTS.md`, rules file, PR checklist, tests |
| Merge pain | low | medium | folder ownership, small PRs, daily pull |
| Tariff challenged by mentor | medium | low | configurable, sourced in `DECISION_LOG.md`, sensitivity chart |
