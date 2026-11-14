"""Keep real 28-day Verified history fresh without weakening the gate."""
from datetime import datetime, timedelta, timezone

from src.collectors import sync
from src.database.models import Repository, SyncCheckpoint

NOW = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
SOURCES = ("issues", "pull_requests", "workflow_runs")


def add_repo(db, repo_id):
    row = Repository(
        id=repo_id, owner="public", name=str(repo_id),
        full_name=f"public/{repo_id}", url=f"https://github.com/public/{repo_id}",
        language="Python", category="Data & backend",
        selected=True, stars=120,
    )
    db.add(row)
    return row


def checkpoint(repo_id, source, *, age_hours=1, days=29, status="complete"):
    return SyncCheckpoint(
        repo_id=repo_id, source=source, status=status,
        coverage_start=NOW - timedelta(days=days),
        last_success_at=NOW - timedelta(hours=age_hours),
        high_watermark=NOW - timedelta(hours=age_hours),
        pages_fetched=1, records_fetched=10,
    )


def prepared(db):
    # 101 is comfortably fresh. 102 is expiring before the next four-hour
    # run, while 103 already crossed the 12-hour freshness threshold.
    for rid in (102, 103, 104, 105):
        add_repo(db, rid)
    for rid, age in ((101, 1), (102, 10), (103, 13)):
        for src in SOURCES:
            db.add(checkpoint(rid, src, age_hours=age))
    for src in SOURCES[:2]:
        db.add(checkpoint(104, src))
    db.add(checkpoint(104, SOURCES[-1], status="partial"))
    db.add(checkpoint(105, SOURCES[0], days=7))
    db.commit()
    return [db.get(Repository, rid) for rid in (101, 102, 103, 104, 105)]


def test_verified_maintenance_prioritizes_expiring_and_stale_28day_cohorts(db, cfg):
    repos = prepared(db)
    order = sync.verification_maintenance_order(db, repos, cfg, NOW)
    assert [row.id for row in order] == [103, 102, 104, 101, 105]
    assert sync.verification_maintenance_priority(db, repos[0], cfg, NOW)[0] == 2
    assert sync.verification_maintenance_priority(db, repos[2], cfg, NOW)[0] == 0
    assert sync.verification_maintenance_priority(db, repos[3], cfg, NOW)[0] == 1
    assert sync.verification_maintenance_priority(db, repos[4], cfg, NOW)[0] == 3


def test_optional_historical_repair_cannot_preempt_expiring_verified(db, cfg, monkeypatch):
    prepared(db)
    scanned = []

    def fake_sync(session, client, repo, source, settings, **kwargs):
        scanned.append(repo.id)
        return {"repo": repo.full_name, "source": source, "status": "complete"}

    monkeypatch.setattr(sync, "sync_one", fake_sync)
    monkeypatch.setattr(sync, "refresh_repo_metadata", lambda *args, **kwargs: False)
    monkeypatch.setattr(sync, "record_observations", lambda *args, **kwargs: False)
    monkeypatch.setattr(sync, "coverage_repair_targets",
                        lambda *args, **kwargs: {105: {"issues"}})

    class FakeClient:
        max_requests = None
        request_count = 0

    result = sync.synchronize(
        db, FakeClient(), cfg, run_at=NOW,
        initial_batch_size=20, repair_coverage=True,
    )
    assert len(result) == 15
    assert scanned[0:6:3] == [103, 102]
    assert scanned[6] == 105  # repair runs after urgent refreshes


def test_four_hour_refresh_and_manual_candidate_audit_do_not_weaken_verified_definition():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    refresh = (root / ".github/workflows/public-snapshot.yml").read_text()
    scout = (root / ".github/workflows/candidate-audit.yml").read_text()
    assert "cron: '23 1,5,9,13,17,21 * * *'" in refresh
    assert "workflow_dispatch:" in scout
    assert "cron:" not in scout
    assert "STALE_HOURS: '12'" in refresh
    assert "--max-requests 850" in refresh
