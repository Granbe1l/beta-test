"""P2.1: one bounded batch per GitHub source, not 5 queries x 75 projects.

Fixture records only exist in test SQLite, never the public snapshot or UI.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import event

from src.analytics.read import load_reports
from src.database.models import (
    Repository, Issue, PullRequest, WorkflowRun, SyncCheckpoint, Observation,
)

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)


def test_batch_loader_keeps_source_semantics_and_30_observation_cap(db):
    other = Repository(
        id=102, full_name="sample/another", owner="sample", name="another",
        url="https://github.com/sample/another", language="Python",
        category="Data & backend", selected=True, stars=7,
    )
    excluded = Repository(
        id=999, full_name="sample/excluded", owner="sample", name="excluded",
        url="https://github.com/sample/excluded", language="Python",
        category="Data & backend", selected=False, stars=0,
    )
    db.add_all([other, excluded])
    for repo_id in (101, 102):
        url = "https://github.com/sample/" + (
            "project" if repo_id == 101 else "another")
        db.add(Issue(
            id=1000 + repo_id, repo_id=repo_id, number=1, url=url+"/issues/1",
            title="Test issue", state="open", created_at=NOW-timedelta(days=40),
            updated_at=NOW-timedelta(days=1), labels=["bug"], comments_count=0,
            fetched_at=NOW,
        ))
        db.add(PullRequest(
            id=2000 + repo_id, repo_id=repo_id, number=1, url=url+"/pull/1",
            title="Test PR", state="closed", draft=False,
            created_at=NOW-timedelta(days=6),
            updated_at=NOW-timedelta(days=2),
            closed_at=NOW-timedelta(days=2),
            merged_at=NOW-timedelta(days=2),
            labels=[], fetched_at=NOW,
        ))
        db.add(WorkflowRun(
            id=3000 + repo_id, repo_id=repo_id,
            url=url+"/actions/runs/1", workflow_name="CI",
            status="completed", conclusion="success",
            created_at=NOW-timedelta(hours=5),
            updated_at=NOW-timedelta(hours=4),
            fetched_at=NOW,
        ))
        for source in ("issues", "pull_requests", "workflow_runs", "open_backlog"):
            db.add(SyncCheckpoint(
                repo_id=repo_id, source=source, status="complete",
                last_success_at=NOW-timedelta(hours=1),
                coverage_start=NOW-timedelta(days=110),
            ))
        for age_hours in range(35):
            db.add(Observation(
                repo_id=repo_id, measured_at=NOW-timedelta(hours=age_hours),
                open_issues_observed=age_hours,
                aged_issues_observed=1, open_prs_observed=age_hours,
                collection_basis="verified_open_inventory",
            ))
    db.flush()

    # Read-only SQL must stay constant for the selected set, independent of
    # how many individual repositories or historical records exist.
    statements = []
    def count_sql(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().lower().startswith("select"):
            statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", count_sql)
    try:
        reports = load_reports(db, now=NOW)
    finally:
        event.remove(db.bind, "before_cursor_execute", count_sql)

    assert len(statements) == 6, (
        f"Expected one query each for repos/checkpoints/Issue/PR/CI/observations;"
        f" got {len(statements)}: {statements}")
    assert len(reports) == 2  # unselected repo is never retrieved
    assert [r["repository"]["full_name"] for r in reports] == [
        "sample/another", "sample/project",
    ]
    for report in reports:
        assert report["coverage_ok"]
        assert report["open_backlog_status"] == "complete"
        assert report["status"] == {
            "issues": "complete", "pull_requests": "complete",
            "workflow_runs": "complete",
        }
        assert report["issues"]["observed_open_partial"] == 1
        assert report["issues"]["aged_open"] == 1
        assert report["prs"]["total_observed"] == 1
        assert report["ci"]["total_observed"] == 1
        assert len(report["issue_rows"]) == 1
        assert len(report["pr_rows"]) == 1
        assert len(report["ci_rows"]) == 1
        assert len(report["observations"]) == 30
        # Same 30 most recent timestamps as original per-repository LIMIT 30.
        assert [x["open_issues_observed"] for x in report["observations"]] == list(range(30))


def test_empty_selection_does_not_scan_source_tables(db):
    db.query(Repository).update({Repository.selected: False})
    db.flush()
    statements = []
    def count_sql(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().lower().startswith("select"):
            statements.append(statement)
    event.listen(db.bind, "before_cursor_execute", count_sql)
    try:
        assert load_reports(db, now=NOW) == []
    finally:
        event.remove(db.bind, "before_cursor_execute", count_sql)
    assert len(statements) == 1
