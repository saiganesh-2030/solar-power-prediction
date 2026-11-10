"""Integration tests for /health, /meta, and /dashboard/overview endpoints.

Verifies:
- /health returns {"status": "ok"}
- /meta returns envelope with valid metadata structure
- /dashboard/overview returns KPIs, timeseries, and top inspection candidates
- Non-negotiable: no banned vocabulary in responses
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.routers.health import get_health
from backend.app.routers.meta import get_meta
from backend.app.routers.dashboard import get_dashboard_overview

BANNED_PATTERN = re.compile(r"\b(fault|failure|defective|malfunction)\b", re.IGNORECASE)

def test_health():
    res = get_health()
    assert res == {"status": "ok"}
    print("✓ test_health passed")

def test_meta():
    res = get_meta()
    data = res.data
    assert data.plants == [1, 2]
    assert "1" in data.inverters
    assert "2" in data.inverters
    assert len(data.inverters["1"]) == 22
    assert data.date_range.start
    assert data.date_range.end
    assert "train" in data.split_dates.model_dump()
    assert data.tariff_default > 0
    assert data.source in ["artifacts", "stub"]

    # Language guardrail check
    text_content = res.model_dump_json()
    match = BANNED_PATTERN.search(text_content)
    assert match is None, f"Found banned vocabulary '{match.group()}' in /meta response"
    print("✓ test_meta passed")

def test_dashboard():
    res = get_dashboard_overview(plant=1)
    data = res.data
    assert data.kpis.actual_kwh > 0
    assert data.kpis.predicted_kwh > 0
    assert data.kpis.anomaly_events.total >= 0
    assert len(data.top_candidates) <= 5
    assert len(data.timeseries.t) > 0

    # Language guardrail check
    text_content = res.model_dump_json()
    match = BANNED_PATTERN.search(text_content)
    assert match is None, f"Found banned vocabulary '{match.group()}' in /dashboard response"
    print("✓ test_dashboard passed")

if __name__ == "__main__":
    test_health()
    test_meta()
    test_dashboard()
    print("All integration tests passed successfully!")
