"""Safeguard inventory maintenance capacity without inventing 50/50 status.

The simulated 4-hour cycles use only fake REST pagination. Real GitHub
coverage must still be established by a published collector source audit.
"""
from datetime import timedelta
from inspect import signature
from sqlalchemy import select

from src.collectors.backlog import sync_open_backlog
from src.collectors.client import PageResult
from src.collectors.sync import backlog_priority_order, synchronize
from src.database.models import Repository, SyncCheckpoint
from .conftest import NOW


class EmptyButExhaustedOpenIssueClient:
    def __init__(self):
        self.max_requests = 850
        self.request_count = 0

    def paginate(self, path, params, max_pages, **kwargs):
        assert path.endswith("/issues")
        assert params["state"] == "open"
        assert params["sort"] == "created"
        assert "since" not in params
        self.request_count += 1
        return PageResult([], 1, True, False, False)


def test_25_scans_per_slot_is_the_bounded_default_and_12h_policy_unchanged():
    assert signature(synchronize).parameters["max_backlog_repos"].default == 25
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    runner = (root / "scripts/run_sync.py").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/public-snapshot.yml").read_text(
        encoding="utf-8")
    assert 'parser.add_argument("--max-backlog-repos"' in runner
    assert "max_backlog_repos=args.max_backlog_repos" in runner
    assert "--audit-open-backlog --max-backlog-repos 50" in workflow
    assert "STALE_HOURS: '12'" in workflow
    assert "--max-requests 850" in workflow
    assert "open-inventory-triage.json" in workflow


def test_two_bounded_four_hour_slots_can_reach_50_without_false_flags(db, cfg):
    # The mock returns exhausted empty Issues lists; production never
    # marks complete unless its real paginator reports complete.
    first = db.get(Repository, 101)
    for i in range(49):
        index = 30000 + i
        db.add(Repository(
            id=index, full_name=f"tests/repo-{i:02d}",
            owner="tests", name=f"repo-{i:02d}",
            url=f"https://github.com/tests/repo-{i:02d}",
            stars=10, selected=True,
        ))
    db.flush()
    all_repos = list(db.scalars(
        select(Repository).where(Repository.selected.is_(True))))
    assert len(all_repos) == 50
    for repo in all_repos:
        for source in ("issues", "pull_requests", "workflow_runs"):
            db.add(SyncCheckpoint(
                repo_id=repo.id, source=source, status="complete",
                coverage_start=NOW - timedelta(days=32),
                last_success_at=NOW,
            ))
    db.commit()
    client = EmptyButExhaustedOpenIssueClient()
    for slot in range(2):
        at = NOW + timedelta(hours=slot * 4)
        queue = backlog_priority_order(db, all_repos, cfg, at)
        assert len(queue) == 50 - slot * 25
        for repo in queue[:25]:
            result = sync_open_backlog(db, client, repo, cfg, now=at)
            assert result["status"] == "complete"
            assert result["full_open_backlog_verified"] is True
    measured = NOW + timedelta(hours=8)
    assert backlog_priority_order(db, all_repos, cfg, measured) == []
    assert sum(
        db.get(SyncCheckpoint, (repo.id, "open_backlog")).status == "complete"
        for repo in all_repos
    ) == 50
    assert client.request_count == 50
    assert client.request_count <= client.max_requests

    # A stale checkpoint loses eligibility: a second maintenance rotation
    # can renew it without marking old data fresh before collection.
    measured = NOW + timedelta(hours=12, minutes=1)
    first_expired = backlog_priority_order(db, all_repos, cfg, measured)
    assert len(first_expired) == 25
    for repo in first_expired:
        sync_open_backlog(db, client, repo, cfg, now=measured)
    measured = NOW + timedelta(hours=16, minutes=1)
    second_expired = backlog_priority_order(db, all_repos, cfg, measured)
    assert len(second_expired) == 25
    for repo in second_expired:
        sync_open_backlog(db, client, repo, cfg, now=measured)
    assert backlog_priority_order(
        db, all_repos, cfg, measured + timedelta(hours=1)) == []


def test_client_partial_result_never_reaches_complete_inventory(db, cfg):
    class Incomplete(EmptyButExhaustedOpenIssueClient):
        def paginate(self, path, params, max_pages, **kwargs):
            self.request_count += 1
            return PageResult([], 2, False, True, False)
    repo = db.get(Repository, 101)
    outcome = sync_open_backlog(db, Incomplete(), repo, cfg, now=NOW)
    assert outcome["status"] == "partial"
    assert not outcome["full_open_backlog_verified"]
    cp = db.get(SyncCheckpoint, (101, "open_backlog"))
    assert cp.status == "partial"
    assert cp.last_success_at is None


def test_production_catchup_scans_33_pending_without_exceeding_shared_budget(db, cfg, monkeypatch):
    """A missed-schedule recovery may need >25 scans, but never weaker proof."""
    from src.collectors import sync
    first = db.get(Repository, 101)
    for i in range(49):
        rid = 50000 + i
        db.add(Repository(
            id=rid, full_name=f"catchup/repo-{i:02d}",
            owner="catchup", name=f"repo-{i:02d}",
            url=f"https://github.com/catchup/repo-{i:02d}",
            stars=10, selected=True,
        ))
    db.flush()
    selected = list(db.scalars(
        select(Repository).where(Repository.selected.is_(True))))
    assert len(selected) == 50
    for repo in selected:
        for source in ("issues", "pull_requests", "workflow_runs"):
            db.add(SyncCheckpoint(
                repo_id=repo.id, source=source, status="complete",
                coverage_start=NOW - timedelta(days=32),
                last_success_at=NOW,
            ))
    # 17 complete fresh inventories and 33 missing (a genuine checkpoint gap).
    for repo in selected[:17]:
        db.add(SyncCheckpoint(
            repo_id=repo.id, source="open_backlog", status="complete",
            coverage_start=NOW, last_success_at=NOW,
        ))
    db.commit()
    assert len(backlog_priority_order(db, selected, cfg, NOW)) == 33
    monkeypatch.setattr(sync, "refresh_repo_metadata", lambda *a, **k: False)
    monkeypatch.setattr(sync, "sync_one", lambda session, client, repo, source,
                        settings, **kw: {"repo": repo.full_name,
                                         "source": source, "status": "complete"})
    monkeypatch.setattr(sync, "record_observations", lambda *a, **k: False)
    client = EmptyButExhaustedOpenIssueClient()
    rows = synchronize(db, client, cfg, run_at=NOW,
                       initial_batch_size=20, audit_open_backlog=True,
                       max_backlog_repos=50)
    inventory_rows = [r for r in rows if r["source"] == "open_backlog"]
    assert len(inventory_rows) == 33
    assert all(row["full_open_backlog_verified"] for row in inventory_rows)
    assert client.request_count == 33 <= client.max_requests
    assert len(backlog_priority_order(db, selected, cfg, NOW)) == 0


def test_production_catchup_still_stops_before_api_reserve(db, cfg, monkeypatch):
    """The higher cap never authorizes spending unavailable API budget."""
    from src.collectors import sync
    repo = db.get(Repository, 101)
    for src in ("issues", "pull_requests", "workflow_runs"):
        db.add(SyncCheckpoint(
            repo_id=repo.id, source=src, status="complete",
            coverage_start=NOW - timedelta(days=32), last_success_at=NOW,
        ))
    db.commit()
    monkeypatch.setattr(sync, "refresh_repo_metadata", lambda *a, **k: False)
    monkeypatch.setattr(sync, "sync_one", lambda session, client, repo, source,
                        settings, **kw: {"repo": repo.full_name,
                                         "source": source, "status": "complete"})
    monkeypatch.setattr(sync, "record_observations", lambda *a, **k: False)
    client = EmptyButExhaustedOpenIssueClient()
    # Within the source scan's own conservative headroom, but not enough for
    # the independent REST+Search reserve: no inventory scan is performed.
    client.max_requests = 25
    output = synchronize(db, client, cfg, run_at=NOW,
                         audit_open_backlog=True, max_backlog_repos=50)
    assert not any(r["source"] == "open_backlog" for r in output)
    assert db.get(SyncCheckpoint, (repo.id, "open_backlog")) is None
    assert client.request_count == 0
