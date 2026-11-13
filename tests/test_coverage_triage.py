"""P0: Audit gaps must reveal what is missing without creating completeness."""
from datetime import datetime, timedelta, timezone

from scripts.coverage_triage import coverage_gaps

NOW = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)


def check(name, issue_status, issue_since, *, ci_status="partial"):
    return {
        "name": name,
        "status": {
            "issues": issue_status, "pull_requests": "complete",
            "workflow_runs": ci_status,
        },
        "source_details": {
            "issues": {
                "status": issue_status, "coverage_start": issue_since,
                "pages_fetched": 6, "last_error": (
                    "Page cap" if issue_status == "partial" else None),
            },
            "pull_requests": {
                "status": "complete",
                "coverage_start": NOW - timedelta(days=60),
                "pages_fetched": 2,
            },
            "workflow_runs": {
                "status": ci_status,
                "coverage_start": NOW - timedelta(days=35),
                "pages_fetched": 18,
            },
        },
    }


def test_complete_7d_scan_is_a_28d_gap_even_with_complete_status():
    a = check("a/one", "complete", NOW - timedelta(days=7),
              ci_status="complete")
    b = check("b/two", "partial", NOW - timedelta(days=28))
    report = coverage_gaps({
        "repositories": [a, b],
        "coverage_summary": {
            "issues": {"verified_28d": 0},
            "pull_requests": {"verified_28d": 2},
            "workflow_runs": {"verified_28d": 1},
        },
    }, now=NOW)
    assert report["gap_count"] == 3
    assert report["actual_verified_28d"]["issues"] == 0
    assert report["top_gaps"][0]["repository"] == "b/two"
    assert report["top_gaps"][0]["reason"] == "api_page_cap_or_partial"
    short = next(x for x in report["top_gaps"] if x["repository"] == "a/one")
    assert short["reason"] == "complete_short_fallback_only"
    assert short["fetched_pages"] == 6


def test_empty_audit_cannot_invent_verified_sources():
    report = coverage_gaps({}, now=NOW)
    assert report["repository_count"] == 0
    assert report["actual_verified_28d"] == {
        "issues": None, "pull_requests": None, "workflow_runs": None}
    assert report["top_gaps"] == []
