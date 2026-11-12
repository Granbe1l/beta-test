"""Sample coverage and aggregation tests; no invented production totals."""
from datetime import datetime, timedelta, timezone

from src.ui.observed import coverage_counts, summary

NOW = datetime(2026, 11, 12, 13, 0, tzinfo=timezone.utc)


def item(day_offset, **kwargs):
    return {"created_at": NOW - timedelta(days=day_offset), **kwargs}


def test_observed_kpis_match_retrieved_rows_and_keep_coverage_denominator():
    base = {
        "status": {"issues": "partial", "pull_requests": "complete",
                   "workflow_runs": "partial"},
        "issue_rows": [
            item(8, state="open"),
            item(40, state="open"),
            item(50, state="closed"),
        ],
        "pr_rows": [
            item(10, state="open", draft=True, merged_at=None),
            item(5, state="open", draft=False, merged_at=None),
            item(7, state="closed", draft=False, merged_at=NOW - timedelta(days=1)),
        ],
        "ci_rows": [
            item(2, status="completed", conclusion="success"),
            item(4, status="completed", conclusion="failure"),
            item(100, status="completed", conclusion="success"),
        ],
    }
    result = summary([base], now=NOW, observation_days=90)
    assert result["repositories"] == 1
    assert result["coverage"] == {"issues": 0, "pull_requests": 1, "workflow_runs": 0}
    assert result["open_issues"] == 2
    assert result["aged_issues"] == 1
    assert result["aged_share"] == 50
    assert result["open_changes"] == 2
    assert result["draft_changes"] == 1
    assert result["merged_changes"] == 1
    assert result["completed_checks"] == 2
    assert result["successful_checks"] == 1
    assert result["failed_checks"] == 1
    assert result["check_success_share"] == 50


def test_unknown_source_is_missing_not_zero():
    empty = {"status": {"issues": "unavailable", "pull_requests": "stale",
                        "workflow_runs": "failed"},
             "issue_rows": [], "pr_rows": [], "ci_rows": []}
    result = summary([empty], now=NOW)
    assert result["open_issues"] is None
    assert result["open_changes"] is None
    assert result["completed_checks"] is None
    assert result["aged_share"] is None
    assert result["check_success_share"] is None
    assert coverage_counts([empty]) == {"issues": 0, "pull_requests": 0, "workflow_runs": 0}


def test_zero_is_valid_for_complete_empty_source():
    empty = {"status": {"issues": "complete", "pull_requests": "complete",
                        "workflow_runs": "complete"},
             "issue_rows": [], "pr_rows": [], "ci_rows": []}
    result = summary([empty], now=NOW)
    assert result["open_issues"] == 0
    assert result["open_changes"] == 0
    assert result["completed_checks"] == 0
    assert result["aged_share"] is None
