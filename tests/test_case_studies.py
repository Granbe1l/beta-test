"""P1: source-backed conditional case decisions with no fabricated outcomes."""
from datetime import datetime, timedelta, timezone

from src.analytics.case_studies import build_case_studies


def make_report(kind, number):
    now = datetime.now(timezone.utc)
    base = f"https://github.com/example/repo{number}"
    opened = [
        {"number": i, "url": base + f"/issues/{i}",
         "title": f"Tracked Issue {i}", "created_at": now - timedelta(days=31+i),
         "state": "open"} for i in range(12)
    ]
    prs = [
        {"number": i, "url": base + f"/pull/{i}",
         "title": f"Code change {i}", "state": "closed", "draft": False,
         "created_at": now - timedelta(days=i + 9),
         "merged_at": now - timedelta(days=i + 1)}
        for i in range(8)
    ]
    runs = [
        {"url": base + f"/actions/runs/{i}",
         "workflow_name": "Build", "status": "completed",
         "conclusion": "success" if i < 5 else "failure",
         "created_at": now - timedelta(days=i+1)}
        for i in range(12)
    ]
    return {
        "repository": {"full_name": f"example/repo{number}", "url": base},
        "status": {"issues": "complete", "pull_requests": "complete",
                   "workflow_runs": "complete"},
        "coverage": {s: {"coverage_start": now-timedelta(days=40)}
                     for s in ("issues", "pull_requests", "workflow_runs")},
        "open_backlog_status": "complete",
        "issues": {"aged_denominator": 12, "aged_open": 12,
                   "aged_percent": 100},
        "prs": {"median_merge_days": None, "merge_duration_n": 0},
        "ci": {"known_conclusion_denominator": None,
               "success_percent": None},
        "closure": None,
        "issue_rows": opened,
        "pr_rows": prs,
        "ci_rows": runs,
    }


def test_three_types_are_distinct_and_their_urls_are_real_rows():
    reports = [make_report(kind, n) for n, kind in enumerate(
        ("issue-aging", "ci", "merge-duration"), 1)]
    cases = build_case_studies(reports)
    # All three evidence types exist here across three real test-fixture
    # repositories. Greedy single-repo reuse would wrongly hide two cases.
    assert len(cases) == 3
    assert len({c["repository"] for c in cases}) == 3
    assert len({c["kind"] for c in cases}) == len(cases)
    for c in cases:
        report = next(r for r in reports if r["repository"]["full_name"] == c["repository"])
        assert any(c["record_url"] == row["url"] for key in ("issue_rows", "ci_rows", "pr_rows")
                   for row in report[key])
        assert c["metric_context"] and c["not_proven"]
        assert "not a confirmed issue" in c["status"]
        assert "Only if" in c["conditional_decision"] or "only if" in c["conditional_decision"]


def test_partial_window_does_not_generate_any_case():
    r = make_report("ci", 8)
    r["status"]["workflow_runs"] = "partial"
    assert build_case_studies([r]) == []


def test_missing_original_record_does_not_invent_source():
    r = make_report("ci", 9)
    r["ci_rows"] = [{**x, "url": "https://example.invalid/other"} for x in r["ci_rows"]]
    cases = build_case_studies([r])
    assert all(c["kind"] != "ci" for c in cases)


def test_incomplete_open_inventory_does_not_create_issue_age_case():
    r = make_report("issue-aging", 10)
    r["open_backlog_status"] = "partial"
    assert all(c["kind"] != "issue-aging" for c in build_case_studies([r]))
