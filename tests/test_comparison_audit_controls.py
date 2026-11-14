"""Independent audit: honest 28-day denominators, short scans and real history."""
from datetime import datetime, timedelta, timezone
from src.analytics.comparison_audit import audit_comparison_readiness

NOW = datetime(2026, 11, 14, 3, tzinfo=timezone.utc)


def source(name: str, complete=True):
    start = NOW - timedelta(days=40)
    return {
        "repository": {"full_name": name, "category": "Utilities"},
        "status": {"issues": "complete" if complete else "partial",
                   "pull_requests": "complete",
                   "workflow_runs": "complete"},
        "coverage": {
            k: {"coverage_start": start}
            for k in ("issues", "pull_requests", "workflow_runs")
        },
        "issue_rows": [],
        "pr_rows": [{
            "merged_at": NOW-timedelta(days=1),
            "created_at": NOW-timedelta(days=2),
        }],
        "ci_rows": [
            {"created_at": NOW-timedelta(days=1), "status": "completed",
             "conclusion": "success"},
            {"created_at": NOW-timedelta(days=1), "status": "queued"},
        ],
        "observations": [],
        "open_backlog_status": "partial",
        "issues": {"aged_denominator": None, "aged_open": None},
    }


def test_real_source_controls_preserve_verified_zero_and_withhold_partial():
    reports = [source("example/a"), source("example/b", complete=False)]
    audit = audit_comparison_readiness(reports, now=NOW)
    assert audit["status"] == "passed"
    assert audit["tracked_repositories"] == 2
    assert audit["source_row_counts_independently_verified"] == 5
    assert audit["verified_true_zeros"] == 1
    assert audit["unverified_values_confirmed_unknown"] == 1
    assert audit["negative_partial_checkpoint_gates_passed"] == 6
    assert audit["negative_short_window_gates_passed"] == 6
    assert audit["historical_matched_verified_pair"] is None


def test_historical_pair_requires_original_verified_inventory_dates():
    a, b = source("example/a"), source("example/b")
    for report in (a, b):
        report["observations"] = [
            {"measured_at": NOW-timedelta(days=2),
             "collection_basis": "verified_open_inventory",
             "open_issues_observed": 7, "open_prs_observed": 3},
            {"measured_at": NOW-timedelta(days=1),
             "collection_basis": "verified_open_inventory",
             "open_issues_observed": 8, "open_prs_observed": 2},
        ]
    audit = audit_comparison_readiness([a, b], now=NOW)
    assert audit["historical_matched_verified_pair"] is not None
    assert audit["historical_matched_verified_pair"]["matched_repositories"] == 2
