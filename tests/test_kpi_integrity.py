"""Cross-check real SQL aggregations against Python snapshot logic."""
from datetime import datetime, timedelta, timezone

import pytest

from scripts.verify_kpi_integrity import audit_consistency
from src.analytics.metrics import calculate_issues

NOW = datetime(2026, 11, 13, 3, 0, tzinfo=timezone.utc)
BASE = "https://github.com/sample/project"


def fixture_report(*, verified=True, full_backlog=False):
    issues = [
        {"id": 1, "state": "open", "created_at": NOW-timedelta(days=70)},
        {"id": 2, "state": "open", "created_at": NOW-timedelta(days=1)},
        {"id": 3, "state": "closed", "created_at": NOW-timedelta(days=65)},
    ]
    prs = [
        {"id": 100, "merged_at": NOW-timedelta(days=1)},
        {"id": 101, "merged_at": None},
    ]
    ci = [
        {"id": 200, "status": "completed", "conclusion": "success",
         "created_at": NOW-timedelta(days=2)},
        {"id": 201, "status": "completed", "conclusion": "failure",
         "created_at": NOW-timedelta(days=3)},
    ]
    sources = ("issues", "pull_requests", "workflow_runs")
    status = {s: "complete" if verified else "partial" for s in sources}
    coverage = {s: {"status": status[s],
                    "coverage_start": NOW-timedelta(days=35),
                    "last_success_at": NOW}
                for s in sources}
    return {
        "repository": {"full_name": "sample/project"},
        "issue_rows": issues, "pr_rows": prs, "ci_rows": ci,
        "status": status, "coverage": coverage,
        "open_backlog_status": "complete" if full_backlog else "partial",
        "issues": calculate_issues(
            issues, NOW, observation_days=90,
            complete=verified, coverage_start=NOW-timedelta(days=35),
            backlog_complete=full_backlog),
    }


def sql_row(*, verified=True, full_backlog=False):
    return {
        "repository": "sample/project",
        "retrieved_issue_rows": 3,
        "retrieved_pr_rows": 2,
        "retrieved_ci_rows": 2,
        "observed_open_issues": 2,
        "observed_aged_open_issues": 1,
        "observed_merged_28d": 1,
        "observed_successful_checks_28d": 1,
        "observed_failed_checks_28d": 1,
        "open_inventory_verified": int(full_backlog),
        "issues_verified_28d": int(verified),
        "prs_verified_28d": int(verified),
        "ci_verified_28d": int(verified),
    }


def test_all_stored_metrics_agree_even_when_open_backlog_partial():
    report = fixture_report()
    result = audit_consistency([report], [sql_row()], now=NOW)
    assert result["status"] == "passed"
    assert result["joint_verified_28d"] == 1
    assert result["full_open_backlog"] == 0


def test_independent_complete_inventory_is_not_28day_requirement():
    r = fixture_report(verified=False, full_backlog=True)
    result = audit_consistency(
        [r], [sql_row(verified=False, full_backlog=True)], now=NOW)
    assert result["joint_verified_28d"] == 0
    assert result["full_open_backlog"] == 1


def test_false_verified_flag_fails_instead_of_inflating_cv_cohort():
    with pytest.raises(AssertionError, match="coverage not consistent"):
        audit_consistency(
            [fixture_report(verified=False)],
            [sql_row(verified=True)], now=NOW)


def test_wrong_sql_denominator_or_false_complete_backlog_fails():
    invalid = sql_row()
    invalid["retrieved_issue_rows"] = 4
    with pytest.raises(AssertionError, match="stored record count differs"):
        audit_consistency([fixture_report()], [invalid], now=NOW)
    invalid = sql_row(full_backlog=True)
    with pytest.raises(AssertionError, match="open-backlog completeness differs"):
        audit_consistency([fixture_report()], [invalid], now=NOW)


def test_wrong_python_age_sample_is_detected():
    invalid = fixture_report(full_backlog=True)
    invalid["issues"]["sample_aged_open"] = 0
    with pytest.raises(AssertionError, match="Python age sample differs"):
        audit_consistency(
            [invalid], [sql_row(full_backlog=True)], now=NOW)


def test_repeated_repo_or_cohort_substitution_is_rejected():
    with pytest.raises(AssertionError, match="Repeated repository"):
        audit_consistency([fixture_report(), fixture_report()], [sql_row()],
                          now=NOW)
    with pytest.raises(AssertionError, match="selected SQL repository identity"):
        changed = sql_row()
        changed["repository"] = "sample/another"
        audit_consistency([fixture_report()], [changed], now=NOW)
