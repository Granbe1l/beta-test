"""Verified freshness protects real data without altering strict source evidence."""
from datetime import timedelta

from src.collectors.sync import (
    SOURCES, synchronize, utc, verified_refresh_priority_order,
)
from src.database.models import Repository, SyncCheckpoint

from .conftest import NOW


def _repo(db, repo_id, name):
    row = Repository(
        id=repo_id, full_name=f"public/{name}", owner="public", name=name,
        url=f"https://github.com/public/{name}", language="Python",
        category="Data & backend", stars=250, selected=True,
    )
    db.add(row)
    return row


def _cp(repo_id, source, hours, days=42, pages=1):
    return SyncCheckpoint(
        repo_id=repo_id, source=source, status="complete",
        coverage_start=NOW - timedelta(days=days),
        high_watermark=NOW - timedelta(hours=hours),
        last_success_at=NOW - timedelta(hours=hours),
        pages_fetched=pages, records_fetched=5,
    )


def test_refresh_priority_saves_12h_verified_cohort_before_partial_and_fresh(db, cfg):
    old = _repo(db, 201, "near-stale")
    fresh = _repo(db, 202, "fresh-full")
    almost = _repo(db, 203, "two-complete")
    partial = _repo(db, 204, "needs-repair")
    for source in SOURCES:
        db.add(_cp(old.id, source, 11))
        db.add(_cp(fresh.id, source, 1))
    for source in SOURCES[:2]:
        db.add(_cp(almost.id, source, 2))
    db.add(_cp(partial.id, "issues", 2, days=7, pages=2))
    db.commit()
    incoming = [partial, fresh, almost, old, db.get(Repository, 101)]
    ordered = verified_refresh_priority_order(db, incoming, cfg, NOW)
    assert ordered[0].id == old.id
    assert ordered[1].id == almost.id
    assert ordered.index(fresh) > ordered.index(partial)
    # The short-window repo remains outside the full 28-day cohort.
    assert partial not in ordered[:2]


def test_stale_three_source_still_attempts_real_refetch_not_fabricated_success(db, cfg, monkeypatch):
    at_risk = _repo(db, 205, "at-risk")
    short = _repo(db, 206, "repair")
    for source in SOURCES:
        db.add(_cp(at_risk.id, source, 13))
    db.add(_cp(short.id, "issues", 1, days=7, pages=2))
    # The fixture repository must have been visited already: the existing
    # initial bootstrap branch deliberately precedes freshness prioritization.
    db.add(SyncCheckpoint(repo_id=101, source="issues", status="partial"))
    db.commit()
    visits = []

    def simulated_real_fetch(session, client, repo, source, settings, **kwargs):
        # Isolate scheduling, don't assert completed collection or update
        # the source checkpoint without an actual source response.
        visits.append((repo.id, source))
        return {"repo": repo.full_name, "source": source,
                "status": "partial", "records": 0}

    monkeypatch.setattr("src.collectors.sync.sync_one", simulated_real_fetch)
    monkeypatch.setattr("src.collectors.sync.refresh_repo_metadata",
                        lambda *args, **kwargs: False)
    result = synchronize(
        db, object(), cfg, initial_batch_size=20, run_at=NOW,
        repair_coverage=True, protect_verified=True,
    )
    assert visits[0][0] == at_risk.id
    assert len(result) == len(visits)
    assert utc(db.get(SyncCheckpoint, (at_risk.id, "issues")).last_success_at) == (
        NOW - timedelta(hours=13)
    )
    assert utc(db.get(SyncCheckpoint, (short.id, "issues")).coverage_start) > (
        NOW - timedelta(days=28)
    )
