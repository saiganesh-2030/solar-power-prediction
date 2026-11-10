# Decision Log

> One place for "why we did it this way". Newest `ACCEPTED` entry wins when entries conflict.
> Anyone (including Antigravity) may add a `PROPOSED` entry. The team lead or Role 4 changes it to `ACCEPTED` or `REJECTED` after a short discussion.

## Template (copy to the bottom)

```
### D-0XX — <short title>
- Status: PROPOSED | ACCEPTED | REJECTED | SUPERSEDED by D-0YY
- Date: YYYY-MM-DD    Proposed by: <name or "Antigravity (Role N)">
- Context: what question came up, which docs were silent or conflicting
- Decision: what we do
- Alternatives considered: ...
- Consequences / contracts touched: ...
- Evidence: numbers, plots, or doc references
```

---

### D-001 — Stack
- Status: ACCEPTED
- Context: Allowed tools are ML, JavaScript, REST API, Fetch API, FastAPI, Postman.
- Decision: Python (FastAPI, pandas, scikit-learn) for ML and API; vanilla JavaScript with Vite and Chart.js for the frontend; Fetch API through one client module; Postman collection for API tests.
- Alternatives: React (more setup and a learning curve for the team), TensorFlow.js (little benefit for tabular regression with this data size).
- Consequences: fewer moving parts; contracts matter more than framework choices.

### D-002 — Team split by vertical slice with contracts and stubs
- Status: ACCEPTED
- Decision: four roles, each owning a feature slice end to end; hand-offs only through file schemas and JSON contracts; Role 4 provides stub artifacts and mock mode.
- Consequences: low dependency; Role 4 must deliver stubs on Day 1.

### D-003 — Target and unit of modelling
- Status: ACCEPTED
- Decision: target is inverter-level `AC_POWER` (kW); models per plant; plant totals are sums of inverter predictions.
- Alternatives: plant-level model only (loses peer comparison and inverter-specific evidence).

### D-004 — Fleet-normal model: no inverter id, no DC, no lagged AC, no yields
- Status: ACCEPTED
- Decision: weather and time features only (`DATA_AND_ML_SPEC.md` section 5).
- Why: avoids leakage and avoids learning an underperforming inverter's low output as normal. DC_POWER is used only for a separate DC-to-AC consistency check.

### D-005 — No database; artifacts as files
- Status: ACCEPTED
- Decision: CSV and JSON artifacts loaded by FastAPI at start-up (about 135k generation rows in total across both plants).
- Revisit if: data grows by orders of magnitude or live ingestion is needed.

### D-006 — Chronological split and train-only predictions
- Status: ACCEPTED
- Decision: 70/15/15 by calendar days; tuning by walk-forward inside train only; model selection on validation; test reported once; predictions for all rows come from the train-only fit so val and test remain unseen.
- Alternatives: refit on train+val for deployment (possible later; report would then need a new unseen period, which we do not have).

### D-007 — Daylight-only metrics are primary
- Status: ACCEPTED
- Why: night rows are zeros and inflate R2.

### D-008 — Evidence ladder and vocabulary policy
- Status: ACCEPTED
- Decision: five categories, three confidence levels, a "what would confirm this" list, and a ban on the word "fault" and its synonyms in the product.
- Why: the problem statement forbids labelling deviations as equipment faults without supporting evidence.

### D-009 — Tariff is a configurable assumption
- Status: PROPOSED (team must fill in and source it)
- Decision: `DEFAULT_TARIFF_INR_PER_KWH` set in `ml/common/config.py` and returned by `/meta`; UI lets the user change it; sensitivity shown.
- Action: Role 3 proposes a value with a source (for example the tariff in a power purchase agreement or a published feed-in rate the mentor accepts) and records it here.

### D-010 — Initial detector thresholds
- Status: ACCEPTED as starting values
- Decision: band coverage 99%, persistence 3 intervals, fleet fraction 0.6, peer limits 0.85/1.15 (`DATA_AND_ML_SPEC.md` section 2).
- Revisit: tune only with evidence (flag rate on val vs test, injection benchmark) and log the change.

### D-011 — Shared conformal helper location
- Status: ACCEPTED
- Decision: `ml/common/conformal.py` is owned by Role 1; Role 2 may use a local copy until it exists.

### D-012 — Energy shortfall tiers
- Status: ACCEPTED
- Decision: conservative (beyond band), central (vs prediction), upper (central plus data-quality events); surplus separate and never netted (`DATA_AND_ML_SPEC.md` section 11).

### D-013 — Common schemas location and re-export
- Status: ACCEPTED
- Date: 2026-11-10    Proposed by: Role 4 (Platform & Integration Lead)
- Context: `ARCHITECTURE_AND_API.md` listed `core/schemas_common.py` while `ROLE_4_PLATFORM_INTEGRATION.md` referenced `schemas/common.py`.
- Decision: Common request/response envelopes (`GenericSuccessEnvelope`, `MetaEnvelope`, `ErrorEnvelope`, etc.) live in `backend/app/core/schemas_common.py` and are re-exported from `backend/app/schemas/common.py`.
- Alternatives considered: Keeping them exclusively in `core/` or exclusively in `schemas/`.
- Consequences / contracts touched: Both `backend/app/core/schemas_common.py` and `backend/app/schemas/common.py` exist and are canonical.
- Evidence: Both core error handlers and router schemas can import envelopes cleanly without circular dependencies.

### D-014 — Baseline default tariff placeholder
- Status: ACCEPTED
- Date: 2026-11-10    Proposed by: Role 4 (Platform & Integration Lead)
- Context: D-009 established that tariff is a configurable assumption, but left the default placeholder value open. API contract examples in `ARCHITECTURE_AND_API.md` section 6 use 4.0.
- Decision: `DEFAULT_TARIFF_INR_PER_KWH` is 4.0 in `ml/common/config.py` as a placeholder until Role 3 supplies a sourced value (see D-009).
- Alternatives considered: Leaving undefined or 0.0, which breaks stub calculations on Day 0/1.
- Consequences / contracts touched: Default tariff returned by `/meta` is 4.0 INR/kWh.
- Evidence: Consistent with contract examples in `docs/ARCHITECTURE_AND_API.md` section 6.
