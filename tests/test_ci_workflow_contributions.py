"""P2: workflow mix uses same period and known-outcome denominator as CI KPI."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.analytics.ci_workflow import workflow_contributions
from src.analytics.comparisons import checks_in_period
from src.analytics.case_studies import build_case_studies

NOW = datetime(2026, 11, 14, 4, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def test_known_and_unknown_exactly_reconcile_with_ci_period_totals():
    runs = []
    conclusions = ("success", "failure", "timed_out", "skipped",
                   "cancelled", None)
    for i, c in enumerate(conclusions):
        runs.append({"workflow_name": f"Workflow {i}",
                     "status": "completed", "conclusion": c,
                     "created_at": NOW - timedelta(days=1)})
    runs.append({"workflow_name": "Excluded", "status": "completed",
                 "conclusion": "failure",
                 "created_at": NOW - timedelta(days=40)})
    runs.append({"workflow_name": "Queued", "status": "queued",
                 "conclusion": None, "created_at": NOW - timedelta(days=1)})
    data = workflow_contributions(runs, now=NOW, max_groups=3)
    check = checks_in_period(runs, now=NOW, days=28)
    assert data["completed_total"] == check["total"] == 6
    assert data["known_total"] == check["known"] == 5
    assert data["unknown_total"] == check["unknown"] == 1
    assert data["recorded_name_groups"] == 6
    assert len(data["rows"]) == 4  # top three + actual aggregated remainder
    assert sum(x["Known results"] for x in data["rows"]) == 5
    assert sum(x["Unknown"] for x in data["rows"]) == 1
    assert sum(x["Success"] for x in data["rows"]) == 1
    assert sum(x["Failure / timeout"] for x in data["rows"]) == 2
    assert sum(x["Skipped"] for x in data["rows"]) == 1
    assert sum(x["Other known"] for x in data["rows"]) == 1


def test_one_busy_workflow_share_is_descriptive_not_a_rank():
    runs = [
        {"workflow_name": ("build" if i < 8 else "docs"),
         "status": "completed",
         "conclusion": "success" if i % 2 else "failure",
         "created_at": NOW - timedelta(days=1)}
        for i in range(10)
    ]
    d = workflow_contributions(runs, now=NOW)
    assert d["known_total"] == 10
    assert d["rows"][0]["Workflow (recorded name)"] == "build"
    assert d["rows"][0]["Share of known outcomes (%)"] == 80
    assert d["rows"][0]["Known results"] == 8
    assert "not independent defects" in d["disclaimer"]


def test_missing_workflow_names_are_explicit_not_assumed_to_be_other_services():
    sample = [{"status": "completed", "conclusion": "success",
               "created_at": NOW - timedelta(days=1)}]
    d = workflow_contributions(sample, now=NOW)
    assert d["rows"][0]["Workflow (recorded name)"] == "(workflow name unavailable)"


def test_real_browser_contract_opens_three_available_case_tabs():
    script = (ROOT / "scripts/capture_ui.py").read_text(encoding="utf-8")
    assert "Verified all available source-backed case tabs" in script
    for value in ("Older open work", "Automated check results",
                  "Time to merge code changes", "/issues/",
                  "/actions/runs/", "/pull/"):
        assert value in script
    ui = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert 'with st.expander("Recorded workflow mix · 28 days"):' in ui
    assert "context[\"known_total\"]" in ui
