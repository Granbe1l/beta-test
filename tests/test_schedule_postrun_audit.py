"""P1.3 audit must run after real scheduled ingestion completes."""
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("event,branch,expected", [
    ("schedule", "main", True), ("workflow_dispatch", "main", True),
    ("push", "main", False), ("schedule", "candidate", False),
    ("workflow_dispatch", "candidate", False),
])
def test_observer_admits_main_rescue_without_admitting_other_branches(event, branch, expected):
    workflow = (ROOT / ".github/workflows/schedule-audit.yml").read_text()
    expression = workflow.split("if: >-", 1)[1].split("runs-on:", 1)[0].strip()
    expression = " ".join(expression.split()).replace("||", "or").replace("&&", "and")
    github = SimpleNamespace(event_name="workflow_run", event=SimpleNamespace(
        workflow_run=SimpleNamespace(event=event, head_branch=branch)))
    assert eval(expression, {"__builtins__": {}}, {"github": github}) is expected


def test_reliability_audit_runs_after_actual_completed_refresh_not_inside_it():
    ingester = (ROOT / ".github/workflows/public-snapshot.yml").read_text()
    observer = (ROOT / ".github/workflows/schedule-audit.yml").read_text()
    assert "schedule:" in ingester
    assert "23 1,5,9,13,17,21 * * *" in ingester
    assert "run: python scripts/schedule_reliability.py" not in ingester
    assert "workflow_run:" in observer
    assert "Refresh curated public GitHub snapshot" in observer
    assert "types: [completed]" in observer
    assert "github.event.workflow_run.event == 'schedule'" in observer
    assert "run: python scripts/schedule_reliability.py" in observer
    assert "actions: read" in observer and "contents: read" in observer
    assert "contents: write" not in observer


def test_schedule_history_still_refuses_to_count_a_run_until_completion():
    from datetime import datetime, timedelta, timezone
    from scripts.schedule_reliability import schedule_health

    now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)

    def run(hours_ago, *, status="completed", conclusion="success"):
        return {
            "event": "schedule", "head_branch": "main",
            "created_at": (now - timedelta(hours=hours_ago)).isoformat(),
            "status": status, "conclusion": conclusion,
        }

    # The in-progress current run cannot certify a success before finishing.
    rows = [run(0, status="in_progress", conclusion=None), run(4), run(8)]
    assert schedule_health(rows, now=now)["status"] == "needs_review"

    # The post-completion observer can evaluate the very same event as success.
    rows[0]["status"] = "completed"
    rows[0]["conclusion"] = "success"
    assert schedule_health(rows, now=now)["status"] == "verified_recent_cycles"
