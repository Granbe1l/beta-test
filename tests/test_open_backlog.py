"""P0: Open GitHub issue inventory must not be confused with recent activity."""
from datetime import timedelta
from dataclasses import replace
from sqlalchemy import select, func

from src.collectors.backlog import fetch_open_backlog, sync_open_backlog
from src.collectors.client import PageResult
from src.database.models import Repository, Issue, PullRequest, SyncCheckpoint
from src.analytics.read import load_reports
from src.analytics.snapshot import export_snapshot, read_snapshot
from .conftest import NOW, issue_payload, pr_payload


class OpenIssueClient:
    def __init__(self, rows, *, complete=True, pages=1):
        self.rows = rows
        self.complete = complete
        self.pages = pages
        self.calls = []
        self.max_requests = 850
        self.request_count = 0

    def paginate(self, path, params, max_pages, **kwargs):
        self.calls.append((path, params, max_pages, kwargs))
        self.request_count += 1
        return PageResult(
            items=self.rows, pages=self.pages, complete=self.complete,
            cap_reached=not self.complete, cutoff_reached=False,
        )


def test_open_issue_scan_uses_oldest_first_and_excludes_prs(db, cfg):
    repo = db.get(Repository, 101)
    old = issue_payload(7, updated="2021-01-01T00:00:00Z")
    pr = issue_payload(8, is_pr=True)
    client = OpenIssueClient([old, pr])
    rows, result = fetch_open_backlog(client, repo, cfg)
    assert [row["number"] for row in rows] == [7]
    assert result.complete
    path, args, cap, opts = client.calls[0]
    assert path == "/repos/sample/project/issues"
    assert args["state"] == "open" and args["sort"] == "created"
    assert args["direction"] == "asc"
    assert "since" not in args
    assert opts["cutoff"] is None


def test_complete_open_inventory_reconciles_stale_open_without_fake_closure(db, cfg):
    repo = db.get(Repository, 101)
    old = issue_payload(1, updated="2021-01-01T00:00:00Z")
    old["created_at"] = "2020-01-01T00:00:00Z"
    stale = issue_payload(2, updated="2020-01-01T00:00:00Z")
    db.add(Issue(
        id=stale["id"], repo_id=101, number=2, url=stale["html_url"],
        title="No longer on full open list", state="open",
        created_at=NOW - timedelta(days=600),
        updated_at=NOW - timedelta(days=350),
        labels=[],
    ))
    db.commit()
    result = sync_open_backlog(db, OpenIssueClient([old]), repo, cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "open_backlog"))
    assert result["status"] == "complete"
    assert cp.last_success_at is not None
    preserved = db.get(Issue, stale["id"])
    assert preserved.state == "not_confirmed_open" and preserved.closed_at is None
    assert db.get(Issue, old["id"]).state == "open"
    assert db.scalar(select(func.count()).select_from(PullRequest)) == 0
    report = load_reports(db, now=NOW)[0]
    assert report["open_backlog_status"] == "complete"
    assert report["issues"]["observed_open_partial"] == 1
    assert report["coverage"]["open_backlog"]["source"] == "open_backlog"


def test_partial_open_inventory_never_claims_full_backlog_or_erases_old_rows(db, cfg):
    repo = db.get(Repository, 101)
    old = issue_payload(1, updated="2021-01-01T00:00:00Z")
    db.add(Issue(
        id=1002, repo_id=101, number=2, url="https://github.com/sample/project/issues/2",
        title="Another issue", state="open",
        created_at=NOW-timedelta(days=400),
        updated_at=NOW-timedelta(days=20), labels=[],
    ))
    db.commit()
    result = sync_open_backlog(
        db, OpenIssueClient([old], complete=False, pages=cfg.max_pages),
        repo, cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "open_backlog"))
    assert result["status"] == "partial"
    assert not result["full_open_backlog_verified"]
    assert cp.last_success_at is None
    assert "exceeded" in cp.last_error
    assert db.get(Issue, 1002).state == "open"
    assert db.get(Issue, 1001).state == "open"
    r = load_reports(db, now=NOW)[0]
    assert r["open_backlog_status"] == "partial"
    assert r["coverage"]["open_backlog"]["status"] == "partial"


def test_empty_complete_open_issue_list_is_valid_and_no_fabricated_close_date(db, cfg):
    repo = db.get(Repository, 101)
    sync_open_backlog(db, OpenIssueClient([]), repo, cfg, now=NOW)
    report = load_reports(db, now=NOW)[0]
    assert report["open_backlog_status"] == "complete"
    assert report["issues"]["observed_open_partial"] == 0


def test_backlog_checkpoint_roundtrips_through_real_snapshot(db, cfg, tmp_path):
    from src.analytics.read import selection_info
    from src.database.models import SelectionRun
    repo = db.get(Repository, 101)
    sync_open_backlog(db, OpenIssueClient([issue_payload(1)]), repo, cfg, now=NOW)
    db.add(SelectionRun(
        id=51, started_at=NOW, completed_at=NOW,
        candidate_count=1, accepted_count=1, status="complete"))
    db.commit()
    report = load_reports(db, now=NOW)
    snap = tmp_path / "backlog.json.gz"
    export_snapshot(snap, report, selection_info(db), generated_at=NOW)
    restored, _, _ = read_snapshot(snap, now=NOW + timedelta(hours=2))
    assert restored[0]["open_backlog_status"] == "complete"
    assert restored[0]["coverage"]["open_backlog"]["source"] == "open_backlog"
    old, _, _ = read_snapshot(snap, now=NOW + timedelta(hours=20))
    assert old[0]["open_backlog_status"] == "stale"


def test_full_open_inventory_does_not_certify_updated_event_history(db, cfg):
    from src.analytics.metrics import calculate_issues
    raw = issue_payload(9, updated="2020-01-01T00:00:00Z")
    from src.collectors.normalize import issue
    rows = [issue(raw, 101)]
    with_verified_backlog = calculate_issues(
        rows, NOW, observation_days=28, complete=False,
        coverage_start=None, backlog_complete=True)
    assert with_verified_backlog["full_open_backlog_verified"] is True
    assert with_verified_backlog["observed_open"] == 1
    assert with_verified_backlog["aged_percent"] == 100.0
    assert with_verified_backlog["trend_valid"] is False
    assert with_verified_backlog["weekly_opened"] is None
    assert with_verified_backlog["weekly_closed"] is None


def test_source_complete_recent_window_never_claims_full_backlog():
    from src.analytics.metrics import calculate_issues
    result = calculate_issues(
        [], NOW, observation_days=28, complete=True,
        coverage_start=NOW - timedelta(days=32))
    assert result["full_open_backlog_verified"] is False
    assert result["trend_valid"] is True


def test_backlog_sync_is_explicitly_opt_in_and_uses_spare_budget(db, cfg):
    from src.collectors.sync import synchronize
    from .test_scale75 import SourceClient
    repo = db.get(Repository, 101)
    # Legacy collectors and tests do not silently perform the optional
    # independent backlog scan; the scheduled pipeline explicitly opts in.
    result = synchronize(db, SourceClient(), cfg, run_at=NOW)
    assert not any(x["source"] == "open_backlog" for x in result)
