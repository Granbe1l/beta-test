"""Scheduled-run reliability requires actual cron events at plausible intervals."""
from datetime import datetime, timedelta, timezone

from scripts.schedule_reliability import schedule_health

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def run(hours_ago, *, event="schedule", conclusion="success", branch="main"):
    return {
        "event": event, "conclusion": conclusion, "status": "completed",
        "head_branch": branch,
        "created_at": (NOW - timedelta(hours=hours_ago)).isoformat(),
        "html_url": "https://github.com/sample/project/actions/runs/123",
    }


def test_only_real_cron_runs_count_toward_reliability():
    rows = [run(0, event="push"), run(6, event="workflow_dispatch"),
            run(12, branch="feature"), run(18)]
    result = schedule_health(rows)
    assert result["status"] == "insufficient_history"
    assert result["actual_scheduled_runs"] == 1


def test_three_successful_six_hour_cron_runs_verify_cycle():
    result = schedule_health([run(18), run(12), run(6)])
    assert result["status"] == "verified_recent_cycles"
    assert result["successful_scheduled_runs"] == 3
    assert result["observed_intervals_hours"] == [6, 6]


def test_missing_or_failed_scheduled_run_never_passes():
    assert schedule_health([run(6), run(12, conclusion="failure"), run(18)])[
        "status"] == "needs_review"
    assert schedule_health([run(6), run(25), run(31)])[
        "status"] == "needs_review"
