# Solar project guardrails (set activation to "Always On")

Full instructions: `AGENTS.md` (root) and `docs/`. This file is the short version that must never be forgotten.

## Modelling
- Expected-power model inputs = weather + time features only. Never use DC_POWER, DAILY_YIELD, TOTAL_YIELD, lagged AC_POWER, inverter id, or day index.
- Split by time: train -> validation -> test, consecutive blocks. No shuffling. Fit anything learned (scalers, thresholds, bands) on train/validation only.
- Report daylight-only metrics as primary (night rows inflate R2).

## Language
- Never write "fault", "failure", "defective", "broken", "malfunction" in UI text, API fields, labels or comments.
- Use: "deviation", "shortfall", "surplus", "candidate for inspection", "unexplained", "possible measurement irregularity".
- Every anomaly shown to a user must carry a category, a confidence level, and a "what would confirm this" hint.

## Contracts
- Column names, endpoint paths, JSON keys and enum values come from `docs/ARCHITECTURE_AND_API.md`. Do not rename them without a PR that also edits that file and `docs/DECISION_LOG.md`.
- Units: kW, kWh, deg C, kW/m2, INR. Timestamps: ISO-8601 without timezone.

## Integrity
- No hard-coded results. Numbers shown in the UI come from the API; the API computes them from artifacts.
- Stay inside the owned folders of the current role (see AGENTS.md section 8).
- If unsure, run `/resolve-doubt`. If docs are silent, log a PROPOSED entry in `docs/DECISION_LOG.md` instead of guessing.
