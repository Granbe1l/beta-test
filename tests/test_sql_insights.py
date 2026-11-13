"""Real SQL aggregation: independent CTEs must not multiply record counts."""
from datetime import timedelta

from scripts.sql_insights import sql_delivery_signals
from src.database.models import Issue, PullRequest, WorkflowRun, SyncCheckpoint
from .conftest import NOW


def test_sql_ctes_keep_source_denominators_and_coverage_explicit(db):
    base = "https://github.com/sample/project"
    db.add_all([
        Issue(id=9001, repo_id=101, number=1, url=base + "/issues/1",
              title="Old open item", state="open",
              created_at=NOW - timedelta(days=60),
              updated_at=NOW - timedelta(days=1), labels=[]),
        Issue(id=9002, repo_id=101, number=2, url=base + "/issues/2",
              title="New open item", state="open",
              created_at=NOW - timedelta(days=2),
              updated_at=NOW - timedelta(days=1), labels=[]),
        Issue(id=9003, repo_id=101, number=3, url=base + "/issues/3",
              title="Already closed", state="closed",
              created_at=NOW - timedelta(days=35),
              updated_at=NOW - timedelta(days=1), labels=[]),
        PullRequest(id=9101, repo_id=101, number=4, url=base + "/pull/4",
                    title="Merged change", state="closed", draft=False,
                    created_at=NOW - timedelta(days=5),
                    updated_at=NOW - timedelta(days=1),
                    closed_at=NOW - timedelta(days=1),
                    merged_at=NOW - timedelta(days=1), labels=[]),
        PullRequest(id=9102, repo_id=101, number=5, url=base + "/pull/5",
                    title="Open change", state="open", draft=False,
                    created_at=NOW - timedelta(days=2),
                    updated_at=NOW - timedelta(days=1), labels=[]),
        WorkflowRun(id=9201, repo_id=101, url=base + "/actions/runs/9201",
                    workflow_name="CI", status="completed", conclusion="success",
                    created_at=NOW - timedelta(days=1),
                    updated_at=NOW - timedelta(days=1)),
        WorkflowRun(id=9202, repo_id=101, url=base + "/actions/runs/9202",
                    workflow_name="CI", status="completed", conclusion="failure",
                    created_at=NOW - timedelta(days=1),
                    updated_at=NOW - timedelta(days=1)),
        SyncCheckpoint(repo_id=101, source="issues", status="complete",
                       coverage_start=NOW - timedelta(days=40),
                       last_success_at=NOW - timedelta(hours=2)),
        SyncCheckpoint(repo_id=101, source="pull_requests", status="partial",
                       coverage_start=NOW - timedelta(days=40),
                       last_success_at=NOW - timedelta(hours=2)),
        SyncCheckpoint(repo_id=101, source="workflow_runs", status="complete",
                       coverage_start=NOW - timedelta(days=40),
                       last_success_at=NOW - timedelta(hours=20)),
    ])
    db.commit()

    result = sql_delivery_signals(db, now=NOW)
    assert len(result) == 1
    row = result[0]
    assert row["repository"] == "sample/project"
    assert row["retrieved_issue_rows"] == 3
    assert row["observed_open_issues"] == 2
    assert row["observed_aged_open_issues"] == 1
    assert row["retrieved_pr_rows"] == 2
    assert row["observed_merged_28d"] == 1
    assert row["retrieved_ci_rows"] == 2
    assert row["observed_successful_checks_28d"] == 1
    assert row["observed_failed_checks_28d"] == 1
    assert row["issues_verified_28d"] == 1
    assert row["prs_verified_28d"] == 0
    assert row["ci_verified_28d"] == 0
    assert row["open_inventory_verified"] == 0


def test_sql_audit_empty_selected_cohort_returns_empty(db):
    from src.database.models import Repository
    repo = db.get(Repository, 101)
    repo.selected = False
    db.commit()
    assert sql_delivery_signals(db, now=NOW) == []


def test_sql_open_inventory_flag_requires_distinct_fresh_complete_checkpoint(db):
    first = sql_delivery_signals(db, now=NOW)[0]
    assert first["open_inventory_verified"] == 0
    db.add(SyncCheckpoint(
        repo_id=101, source="open_backlog", status="complete",
        last_success_at=NOW - timedelta(hours=1),
        coverage_start=NOW - timedelta(hours=1)))
    db.commit()
    verified = sql_delivery_signals(db, now=NOW)[0]
    assert verified["open_inventory_verified"] == 1
    assert verified["issues_verified_28d"] == 0
    cp = db.get(SyncCheckpoint, (101, "open_backlog"))
    cp.status = "partial"
    db.commit()
    assert sql_delivery_signals(db, now=NOW)[0]["open_inventory_verified"] == 0
