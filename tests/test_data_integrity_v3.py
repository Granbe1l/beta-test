"""Regression tests for defensible coverage, triage, and audit reporting."""
from datetime import datetime, timedelta, timezone

import pytest

from src.ui.observed import qualified_reports, analysis_window_coverage
from src.analytics.findings import portfolio_findings
from scripts.report_coverage_delta import delta_report

NOW = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)


def report(name, issue_days=28, pr_days=7, issue_state="complete",
           pr_state="complete"):
    return {
        "repository": {"full_name": name, "url": f"https://github.com/{name}"},
        "status": {"issues": issue_state, "pull_requests": pr_state,
                   "workflow_runs": "unavailable"},
        "coverage": {
            "issues": {"coverage_start": NOW - timedelta(days=issue_days)},
            "pull_requests": {"coverage_start": NOW - timedelta(days=pr_days)},
        },
    }


def test_verified_windows_are_source_specific_and_time_bound():
    a = report("org/a")
    b = report("org/b", issue_days=7, pr_days=28)
    c = report("org/c", issue_days=50, pr_days=50, issue_state="stale")
    assert [r["repository"]["full_name"] for r in qualified_reports(
        [a, b, c], "issues", days=28, now=NOW)] == ["org/a"]
    assert [r["repository"]["full_name"] for r in qualified_reports(
        [a, b, c], "pull_requests", days=28, now=NOW)] == ["org/b"]
    assert len(qualified_reports([a, b, c], "issues", days=7, now=NOW)) == 2
    assert analysis_window_coverage([a, b, c], days=28, now=NOW)["issues"] == 1


def test_unknown_or_invalid_coverage_never_counts_as_verified():
    r = report("org/x")
    r["coverage"]["issues"]["coverage_start"] = None
    assert qualified_reports([r], "issues", now=NOW) == []
    with pytest.raises(ValueError):
        qualified_reports([r], "unknown", now=NOW)
    with pytest.raises(ValueError):
        qualified_reports([r], "issues", days=0, now=NOW)


def make_finding_report(name, issue_pct, ci_pct):
    return {
        "repository": {"full_name": name, "url": f"https://github.com/{name}"},
        "issues": {"aged_denominator": 20, "aged_percent": issue_pct,
                   "aged_open": round(issue_pct * .2)},
        "prs": {"median_merge_days": None, "merge_duration_n": 0},
        "ci": {"known_conclusion_denominator": 30,
               "success_percent": ci_pct, "success": round(ci_pct * .3)},
        "closure": None,
    }


def test_review_order_is_evidence_based_not_project_quality_score():
    r = make_finding_report("org/busy", 75, 30)
    selected = portfolio_findings([r], max_findings=3)
    assert [f["type"] for f in selected] == ["ci", "issue-aging"]
    assert all(f["review_priority"] == "Review first" for f in selected)
    assert all("score" not in f for f in selected)


def test_collection_audit_report_discloses_real_denominators_and_delta():
    before = {"counts": {"issues": 100, "pull_requests": 200, "workflow_runs": 50},
              "coverage_summary": {key: {
                  "complete": 10, "partial": 25, "stale": 4,
                  "unavailable": 36, "verified_28d": 2,
                  "total_repositories": 75}
                  for key in ("issues", "pull_requests", "workflow_runs")}}
    after = {"counts": {"issues": 110, "pull_requests": 230, "workflow_runs": 70},
             "coverage_summary": {key: {
                 "complete": 12, "partial": 23, "stale": 4,
                 "unavailable": 36, "verified_28d": 3,
                 "total_repositories": 75}
                 for key in ("issues", "pull_requests", "workflow_runs")}}
    content = delta_report(before, after)
    assert "12/75 (+2)" in content
    assert "3/75 (+1)" in content
    assert "**110** records (+10" in content
    assert "not full repository histories" in content
    with pytest.raises(ValueError):
        delta_report(before, {})
