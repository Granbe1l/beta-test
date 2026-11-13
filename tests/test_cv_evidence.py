"""P0: cross-source cohort is strictly validated, not 75/75 by fiat."""
from datetime import datetime, timedelta, timezone

from scripts.cv_evidence import cv_receipt
from src.ui.observed import evidence_readiness, verified_joint_cohort

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)
SOURCES = ("issues", "pull_requests", "workflow_runs")


def sample(name, spans, state=None):
    state = state or {}
    return {
        "repository": {"full_name": name},
        "status": {s: state.get(s, "complete") for s in SOURCES},
        "coverage": {s: {
            "coverage_start": NOW-timedelta(days=spans[s]),
            "last_success_at": NOW,
        } for s in SOURCES},
        "open_backlog_status": "partial",
        "issue_rows": [], "pr_rows": [], "ci_rows": [],
    }


def test_verified_cohorts_are_strict_intersections_not_75_repo_claim():
    records = [
        sample("org/A", {"issues": 35, "pull_requests": 35, "workflow_runs": 35}),
        sample("org/B", {"issues": 35, "pull_requests": 7, "workflow_runs": 35}),
        sample("org/C", {"issues": 2, "pull_requests": 35, "workflow_runs": 35}),
        sample("org/D", {"issues": 35, "pull_requests": 35, "workflow_runs": 35},
               state={"workflow_runs": "stale"}),
    ]
    read = evidence_readiness(records, now=NOW)
    assert read["tracked"] == 4
    assert read["verified_7d"] == {
        "issues": 3, "pull_requests": 4, "workflow_runs": 3}
    assert read["verified_28d"] == {
        "issues": 3, "pull_requests": 3, "workflow_runs": 2}
    assert read["joint_verified_7d"] == 2
    assert read["joint_verified_28d"] == 1
    assert [r["repository"]["full_name"] for r in verified_joint_cohort(records, 28, NOW)] == ["org/A"]
    assert [r["repository"]["full_name"] for r in verified_joint_cohort(records, 7, NOW)] == ["org/A", "org/B"]


def test_empty_and_partial_source_cannot_be_verified_by_selection():
    assert evidence_readiness([], now=NOW)["joint_verified_7d"] == 0
    r = sample("org/partial", {s: 180 for s in SOURCES},
               state={"issues": "partial"})
    assert verified_joint_cohort([r], 7, NOW) == []
    assert verified_joint_cohort([r], 28, NOW) == []


def test_cv_receipt_reports_real_rows_and_cohort_denominators():
    a = sample("org/A", {s: 35 for s in SOURCES})
    b = sample("org/B", {s: 2 for s in SOURCES})
    a["issue_rows"] = [{"id": 1}, {"id": 2}]
    a["pr_rows"] = [{"id": 3}]
    b["ci_rows"] = [{"id": 4}]
    receipt = cv_receipt(
        [a, b], generated_at=NOW-timedelta(hours=2), now=NOW)
    assert receipt["tracked_repositories"] == 2
    assert receipt["stored_observations"] == {
        "issue_records": 2, "pull_request_records": 1, "workflow_run_records": 1}
    assert receipt["matching_all_three_sources"] == {"7d": 1, "28d": 1}
    assert receipt["verified_source_windows"]["28d"]["issues"] == 1
    assert receipt["independently_verified_full_open_backlogs"] == 0
    assert receipt["fresh_under_12h"]
    assert "2 curated public GitHub projects" in receipt["suggested_cv_line"]
    assert "not complete project histories" in receipt["scope"]


def test_outdated_snapshot_receipt_does_not_call_it_fresh():
    row = sample("org/A", {s: 35 for s in SOURCES})
    result = cv_receipt(
        [row], generated_at=NOW-timedelta(hours=13), now=NOW)
    assert not result["fresh_under_12h"]
    assert result["matching_all_three_sources"] == {"7d": 1, "28d": 1}
