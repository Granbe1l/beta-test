"""Verify that an adaptive 1-day success cannot masquerade as 28 days."""
from datetime import datetime, timedelta, timezone
from src.ui.observed import coverage_counts, analysis_window_coverage

NOW = datetime(2026, 11, 12, 15, tzinfo=timezone.utc)


def report(window_days, state="complete"):
    return {
        "status": {"issues": state, "pull_requests": state,
                   "workflow_runs": state},
        "coverage": {source: {
            "coverage_start": NOW - timedelta(days=window_days),
            "last_success_at": NOW,
        } for source in ("issues", "pull_requests", "workflow_runs")},
    }


def test_narrow_complete_scan_is_not_28_day_coverage():
    reports = [report(1), report(7), report(30), report(45, state="partial")]
    assert coverage_counts(reports) == {
        "issues": 3, "pull_requests": 3, "workflow_runs": 3}
    assert analysis_window_coverage(reports, days=28, now=NOW) == {
        "issues": 1, "pull_requests": 1, "workflow_runs": 1}


def test_missing_checkpoint_history_is_not_verified_window():
    r = report(90)
    r["coverage"]["issues"] = {}
    assert analysis_window_coverage([r], days=28, now=NOW)["issues"] == 0


def test_most_recent_complete_window_is_counted_for_shorter_span():
    data = [report(7), report(30)]
    assert analysis_window_coverage(data, days=7, now=NOW)["issues"] == 2
    assert analysis_window_coverage(data, days=28, now=NOW)["issues"] == 1
