---
description: Resolve a doubt about the solar project by checking the handbook, contracts and decision log before acting
---

# /resolve-doubt

Use this when you are unsure about a requirement, column, endpoint, metric, rule, ownership, or wording. Do not skip steps and do not guess.

## Steps

1. **Restate the doubt** in one sentence. Name the role you are working as.
2. **Search the docs** for the exact term and close synonyms in this order, and note file + heading for every hit:
   - `docs/ARCHITECTURE_AND_API.md` (contracts, endpoints, schemas)
   - `docs/DECISION_LOG.md` (newest ACCEPTED entry wins)
   - `docs/DATA_AND_ML_SPEC.md` (method, formulas, thresholds)
   - `docs/PROJECT_HANDBOOK.md` (scope, vocabulary, acceptance criteria)
   - `docs/roles/ROLE_<n>_*.md` (ownership, deliverables)
   - `docs/MENTOR_QA.md` (reasoning behind choices)
3. **Classify the result**
   - A. Answered clearly -> state the answer and quote the source. Continue the task.
   - B. Sources conflict -> apply precedence from `AGENTS.md` section 3. State which source won and why. Continue.
   - C. Docs are silent -> go to step 4.
4. **If silent**: pick the smallest reversible option that respects the non-negotiables in `AGENTS.md` section 4.
   - Append a `PROPOSED` entry to `docs/DECISION_LOG.md` using the template in that file.
   - Tell the human exactly what you assumed.
   - If the choice is hard to reverse (contract rename, split change, target change, data deletion), STOP and ask instead.
5. **Check the non-negotiables** against your plan: no leakage, time-ordered split, no "fault" wording, no invented numbers, contracts unchanged, owned folders only.
6. **Answer in this format**
   - Doubt:
   - Sources checked (file > heading):
   - Resolution (A / B / C):
   - Action taken or proposed:
   - Anything the human must confirm:
