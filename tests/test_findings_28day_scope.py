"""P1 regression: reviewer findings use verified 28-day rows, not stale 90-day aggregates."""
from datetime import datetime, timedelta, timezone

from src.analytics.findings import findings_for_repo
from src.analytics.metrics import calculate_ci


def _report(now):
    base = "https://github.com/example/activity"
    prs = []
    for idx in range(6):
        merged_at = now - timedelta(days=idx + 1)
        prs.append({
            "state": "closed", "draft": False,
            "url": base + f"/pull/{idx + 1}",
            "created_at": merged_at - timedelta(days=2 + idx),
            "merged_at": merged_at, "closed_at": merged_at,
        })
    prs.append({
        "state": "closed", "draft": False,
        "url": base + "/pull/99",
        "created_at": now - timedelta(days=72),
        "merged_at": now - timedelta(days=60),
    })
    ci = []
    for idx in range(12):
        ci.append({
            "status": "completed",
            "conclusion": "success" if idx < 7 else "failure",
            "created_at": now - timedelta(days=idx + 1),
            "url": base + f"/actions/runs/{idx + 1}",
        })
    return {
        "repository": {"full_name": "example/activity", "url": base},
        "issues": {"aged_denominator": None, "aged_percent": None},
        "closure": None,
        # Restore mode computes default 90-day stats; do not use when only
        # the verified 28-day source window is available.
        "prs": {"median_merge_days": None, "merge_duration_n": 0},
        "ci": {"known_conclusion_denominator": None, "success_percent": None},
        "pr_rows": prs,
        "ci_rows": ci,
        "status": {"issues": "complete", "pull_requests": "complete",
                   "workflow_runs": "complete"},
        "coverage": {
            "issues": {"coverage_start": now - timedelta(days=30)},
            "pull_requests": {"coverage_start": now - timedelta(days=31)},
            "workflow_runs": {"coverage_start": now - timedelta(days=31)},
        },
    }


def test_finds_verified_28day_pr_and_ci_without_90day_coverage():
    now = datetime.now(timezone.utc)
    items = {f["type"]: f for f in findings_for_repo(_report(now))}
    assert {"merge-duration", "ci"} <= set(items)
    assert items["merge-duration"]["period_days"] == 28
    assert items["merge-duration"]["metric_value"] == "4.5 days"
    assert "28-day" in items["merge-duration"]["evidence_scope"]
    assert items["ci"]["period_days"] == 28
    assert items["ci"]["observed"] == 7
    assert items["ci"]["denominator"] == 12
    assert items["ci"]["examples"][0]["url"].endswith("/actions/runs/12")
    assert all("/pull/99" != x["url"].replace(
        "https://github.com/example/activity", ""
    ) for x in items["merge-duration"]["examples"])


def test_incomplete_28day_sources_never_inherit_90day_values():
    report = _report(datetime.now(timezone.utc))
    report["status"]["pull_requests"] = "partial"
    report["status"]["workflow_runs"] = "partial"
    report["prs"]["median_merge_days"] = 0.2
    report["prs"]["merge_duration_n"] = 1000
    report["ci"]["known_conclusion_denominator"] = 1000
    report["ci"]["success_percent"] = 5
    assert not any(f["type"] in ("merge-duration", "ci")
                   for f in findings_for_repo(report))


def test_skipped_only_does_not_raise_ci_failure_finding():
    now = datetime.now(timezone.utc)
    report = _report(now)
    report["ci_rows"] = [
        {"status": "completed",
         "conclusion": ("success" if i < 4 else "skipped"),
         "created_at": now - timedelta(days=1)}
        for i in range(12)
    ]
    metric = calculate_ci(report["ci_rows"], now, observation_days=28,
                          complete=True,
                          coverage_start=now - timedelta(days=31))
    assert metric["known_conclusion_denominator"] == 12
    assert metric["success_percent"] < 80
    assert metric["failure"] == 0 and metric["skipped"] == 8
    assert not any(f["type"] == "ci" for f in findings_for_repo(report))
