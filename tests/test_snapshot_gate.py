"""Guardrails for published source snapshots on scheduled and manual runs."""
from datetime import datetime, timedelta, timezone
import pytest
from scripts.verify_collection import verify_progress

NOW = datetime(2026, 11, 13, 0, tzinfo=timezone.utc)


def audit(success_at=None, records=25, size=3):
    return {
        "repositories": [
            {"name": f"org/repo{i}", "last_success_at": {
                "issues": success_at, "pull_requests": None,
                "workflow_runs": None}}
            for i in range(size)],
        "counts": {"issues": records, "pull_requests": 30, "workflow_runs": 5},
        "coverage_summary": {
            source: {
                "complete": 1, "partial": 1, "stale": 0,
                "failed": 0, "unavailable": size - 2,
                "verified_28d": 1, "total_repositories": size}
            for source in ("issues", "pull_requests", "workflow_runs")},
    }


def test_fresh_checkpoint_qualifies_even_when_no_new_issue_arrives():
    before = audit(NOW - timedelta(hours=6))
    after = audit(NOW)
    report = verify_progress(before, after, expected_repositories=3)
    assert report["fresh_successful_scans"]["issues"] == 3
    assert sum(report["new_records"].values()) == 0


def test_incremental_records_qualify_even_when_all_sources_are_partial():
    before = audit()
    after = audit(records=31)
    result = verify_progress(before, after, expected_repositories=3)
    assert result["new_records"]["issues"] == 6
    assert result["fresh_successful_scans"]["issues"] == 0


def test_no_actual_collection_is_not_published_as_new():
    item = audit()
    with pytest.raises(RuntimeError, match="made no verified"):
        verify_progress(item, item, expected_repositories=3)


def test_lost_repo_or_rows_fails_validation():
    before = audit()
    after = audit(records=20)
    with pytest.raises(ValueError, match="regressed"):
        verify_progress(before, after, expected_repositories=3)
    after = audit()
    after["repositories"].pop()
    with pytest.raises(ValueError, match="Expected 3"):
        verify_progress(before, after, expected_repositories=3)


def test_28d_window_cannot_exceed_completed_scans():
    before = audit()
    after = audit(records=40)
    after["coverage_summary"]["issues"]["verified_28d"] = 2
    with pytest.raises(ValueError, match="inconsistent"):
        verify_progress(before, after, expected_repositories=3)
