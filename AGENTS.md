# AGENTS.md — Instructions for Antigravity (and any AI agent)

Project: **Solar Power Generation Prediction & Performance Deviation Analysis**
Dataset: Kaggle `anikannal/solar-power-generation-data` (2 plants, 22 inverters each, 15-min data, ~34 days).
Team: 4 people, 4 roles. Stack: Python (FastAPI, pandas, scikit-learn) + JavaScript (Vite, Chart.js, Fetch API).

This file is the entry point. It is short on purpose. The details live in `docs/`.

---

## 1. Read order (before writing any code)

1. This file.
2. `docs/PROJECT_HANDBOOK.md` — what we build and why.
3. The role file of the person you are helping: `docs/roles/ROLE_<n>_*.md`.
4. `docs/ARCHITECTURE_AND_API.md` — folder layout, data contracts, API contract.
5. `docs/DATA_AND_ML_SPEC.md` — cleaning, features, split, models, anomaly rules, finance formulas.
6. `docs/DECISION_LOG.md` — newest accepted decision wins.

Only open files 4–6 when the task touches data, models, endpoints or UI payloads.

## 2. Start of every session

State in one line: `Working as Role <n> (<name>). Owned folders: <list>.`
If the user did not say which role, infer from the branch name (`roleN/...`) or ask once.
Stay inside the owned folders. If you must edit outside them, say so in the PR description.

## 3. When documents disagree (precedence, highest first)

1. Data and API contracts in `docs/ARCHITECTURE_AND_API.md`
2. Newest `ACCEPTED` entry in `docs/DECISION_LOG.md`
3. `docs/DATA_AND_ML_SPEC.md`
4. `docs/PROJECT_HANDBOOK.md`
5. Role files
6. Your own preference (lowest)

Never silently pick a side. Report the conflict (see section 5).

## 4. Non-negotiables (violating any of these is a bug)

1. **No leakage.** The expected-power model must NOT use `DC_POWER`, `DAILY_YIELD`, `TOTAL_YIELD`, lagged `AC_POWER`, inverter id, or a day index as features. Weather and time features only. Trailing windows only (no future rows).
2. **Time-ordered evaluation only.** Train, validation, test are consecutive date blocks. Never `train_test_split(shuffle=True)`. Fit scalers, thresholds and prediction bands on training or validation data only.
3. **Never call a deviation a "fault".** The data has no maintenance logs, alarms or inspection reports. Use the approved vocabulary in `docs/PROJECT_HANDBOOK.md` section 8 ("deviation", "candidate for inspection", "unexplained"). Banned in UI text, API fields and comments: fault, failure, defective, broken, malfunction (unless external evidence is attached by a human).
4. **Do not invent numbers.** Every metric, count, rupee value or chart value must be computed from data by code. No hard-coded results in the UI except clearly marked mock fixtures in `frontend/public/mock/`.
5. **Contracts are frozen unless changed by PR.** Do not rename columns, endpoints, JSON keys or enum values on your own. Changing a contract = edit `docs/ARCHITECTURE_AND_API.md` + add a `DECISION_LOG.md` entry + tell the team.
6. **Units.** Power in kW, energy in kWh (kW x 0.25 h per 15-min row), temperature in deg C, irradiation in kW/m2, money in INR. Timestamps are ISO-8601 strings without timezone, e.g. `2020-05-15T06:30:00`.
7. **Reproducible.** Fixed random seed `42`. Versions pinned. One command regenerates each artifact (see section 7).
8. **Honest claims.** Say "on the unseen test period", not "in general". Report limitations (only ~34 days, no rainfall, one sensor per plant).

## 5. Doubt protocol (use whenever you are unsure)

Run the workflow `/resolve-doubt` if available, otherwise follow these steps:

1. **Search the docs first.** Look in the files listed in section 1 for the exact term (column name, endpoint, metric, rule). Quote the file and heading you relied on.
2. **If docs answer it** -> follow them and continue.
3. **If docs conflict** -> apply the precedence in section 3, continue with the winner, and add a note to the PR description.
4. **If docs are silent** -> choose the smallest, most reversible option that respects section 4. Append a `PROPOSED` entry to `docs/DECISION_LOG.md` (template inside that file) and mention it in your reply so a human can accept or reject it.
5. **If the choice is hard to reverse** (renaming a contract, changing the split, changing the target, deleting data) -> stop and ask the human. Do not guess.
6. Never fill a gap by fabricating data, metrics or file contents.

## 6. Working style

- Small, reviewable changes. One concern per PR. Branch name `role<n>/<topic>`.
- Python: type hints, docstrings on public functions, `ruff` clean, `pytest` for logic.
- JavaScript: ES modules, no framework, `fetch` only through `frontend/src/api/client.js`, no inline secrets.
- Every new endpoint: Pydantic response model + example in `docs/ARCHITECTURE_AND_API.md` + a Postman request in `postman/`.
- Every new page: loading, empty, and error states. Works in mock mode (`VITE_USE_MOCK=true`).
- Add or update tests with the code. Do not delete failing tests to make CI pass.
- Explain what you changed and why in plain language at the end of each task (the team includes beginners).

## 7. Commands (keep these working)

```
# one-time
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# data + ML pipeline (Role 1)
python -m ml.pipeline.build_dataset      # raw CSV -> artifacts/processed/
python -m ml.pipeline.train              # -> artifacts/models/, artifacts/predictions/, artifacts/metrics/
# anomaly + analytics (Role 2, Role 3)
python -m ml.anomaly.run                 # -> artifacts/anomalies/
# stub data so nobody is blocked (Role 4)
python scripts/make_stub_artifacts.py    # -> artifacts/_stub/

# run
uvicorn backend.app.main:app --reload --port 8000
cd frontend && npm run dev               # http://localhost:5173

# test
pytest -q
cd frontend && npm test
```

## 8. Folder ownership (summary; full tree in `docs/ARCHITECTURE_AND_API.md`)

| Role | Owns |
|---|---|
| 1 ML Engineer | `ml/data`, `ml/features`, `ml/models`, `ml/pipeline`, `backend/app/routers/predict.py`, `models.py`, `frontend/src/pages/prediction`, `pages/models` |
| 2 Anomaly & Weather Engineer | `ml/anomaly`, `ml/weather`, `backend/app/routers/anomalies.py`, `weather.py`, `frontend/src/pages/anomalies`, `pages/weather` |
| 3 Analytics & Finance Engineer | `ml/history`, `ml/finance`, `backend/app/routers/history.py`, `finance.py`, `frontend/src/pages/history`, `pages/finance` |
| 4 Platform & Integration Lead | `backend/app/core`, `main.py`, `routers/dashboard.py`, `meta.py`, `frontend/src` shell + shared components + dashboard page, `scripts/`, `postman/`, `tests/integration`, `docs/` upkeep |

## 9. Output format when answering teammates

1. What you understood (1–2 lines).
2. Which docs you relied on (file + heading).
3. The change (code) and how to run or test it.
4. Assumptions or open questions (also logged in `DECISION_LOG.md` if non-trivial).
