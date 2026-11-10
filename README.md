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
python -m ml.anomaly.run

# 4. run the API (add ARTIFACT_DIR=artifacts/_stub to use stub data)
uvicorn backend.app.main:app --reload --port 8000     # docs: http://localhost:8000/docs

# 5. run the frontend
cd frontend && npm install && npm run dev             # http://localhost:5173
# no backend yet? VITE_USE_MOCK=true npm run dev
```

## Principles (short)

- Expected power is estimated from weather and time only (no leakage).
- Evaluation is chronological, on unseen days; daylight-only metrics are primary.
- Deviations are described with evidence and confidence, never labelled as equipment faults.
- Every number shown comes from data through the API.

## Status

Update this table as work progresses.

| Area | Status |
|---|---|
| Data pipeline | not started |
| Models and metrics | not started |
| Anomaly engine | not started |
| API | not started |
| Frontend pages | not started |
| Tests and Postman | not started |
