"""Tests for date-bucketed GitHub Actions scans and honest source coverage."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.collectors.client import PageResult
from src.collectors.sync import fetch_source_adaptive, fetch_ci_windowed, sync_one
from src.database.models import Repository, SyncCheckpoint
from .conftest import NOW, run_payload


class WindowedCIClient:
    def __init__(self, *, cap_daily=False, budget=850):
        self.calls = []
        self.request_count = 0
        self.max_requests = budget
        self.cap_daily = cap_daily

    def paginate(self, path, params, max_pages, **kwargs):
        assert path.endswith("/actions/runs")
        date_range = params["created"]
        first, last = date_range.split("..")
        count = (datetime.fromisoformat(last) - datetime.fromisoformat(first)).days + 1
        self.calls.append(date_range)
        self.request_count += 1
        complete = count == 1 and not self.cap_daily
        return PageResult(
            items=[run_payload(1)],
            pages=max_pages if not complete else 1,
            complete=complete,
            cap_reached=not complete,
            cutoff_reached=False,
        )


def test_saturated_week_is_split_into_complete_utc_days(db, cfg):
    client = WindowedCIClient()
    cfg = replace(cfg, max_pages=2, backfill_days=30)
    since = NOW - timedelta(days=7)
    records, result, actual_since, intervals, pages = fetch_source_adaptive(
        client, db.get(Repository, 101), "workflow_runs", since, cfg, NOW)
    assert result.complete
    assert actual_since == since
    assert len(records) == 1  # Stable GitHub ID is not counted eight times.
    assert len(client.calls) > 2
    assert pages == result.pages
    assert intervals == len(client.calls)
    assert any(a == b for a,b in (v.split("..") for v in client.calls))


def test_one_day_overflow_stays_partial_and_does_not_advance_watermark(db, cfg):
    client = WindowedCIClient(cap_daily=True)
    cfg = replace(cfg, max_pages=2, backfill_days=30)
    result = sync_one(db, client, db.get(Repository, 101),
                      "workflow_runs", cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "workflow_runs"))
    assert result["status"] == "partial"
    assert cp.high_watermark is None
    assert cp.last_success_at is None
    assert len(client.calls) >= 2


def test_request_budget_does_not_justify_full_window_coverage(db, cfg):
    client = WindowedCIClient(budget=4)
    cfg = replace(cfg, max_pages=2, backfill_days=30)
    result = sync_one(db, client, db.get(Repository, 101),
                      "workflow_runs", cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "workflow_runs"))
    assert result["status"] == "partial"
    assert cp.high_watermark is None



def test_verified_ci_days_resume_after_partial_collector_run(db, cfg):
    """Persist day-level progress to avoid rescanning the same weeks."""
    class LargeButCompleteWindow:
        def __init__(self):
            self.calls = []
            self.max_requests = 850
            self.request_count = 0
        def paginate(self, path, params, max_pages, **kwargs):
            self.calls.append(params["created"])
            self.request_count += 1
            return PageResult(items=[run_payload(1)], pages=6, complete=True,
                              cap_reached=False, cutoff_reached=False)

    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=6, backfill_days=30)
    client = LargeButCompleteWindow()
    first = sync_one(db, client, repo, "workflow_runs", cfg, now=NOW)
    saved = db.get(SyncCheckpoint, (101, "workflow_runs"))
    days_completed = dict(saved.verified_days)
    assert first["status"] == "partial"
    assert len(days_completed) >= 14
    assert saved.last_success_at is None
    first_attempts = client.request_count

    # The second scheduled execution can reuse the completed day buckets
    # and finish the 30-day window with fewer GitHub requests.
    second = sync_one(db, client, repo, "workflow_runs", cfg,
                      now=NOW + timedelta(hours=6))
    done = db.get(SyncCheckpoint, (101, "workflow_runs"))
    assert second["status"] == "complete"
    assert len(done.verified_days) >= 29
    # A fresh check of the current UTC day is mandatory even when older
    # verified day buckets are reused; it may cost one extra request.
    assert client.request_count - first_attempts <= first_attempts
    assert done.high_watermark is not None


def test_recent_cached_days_are_expired_but_older_days_are_reusable(db, cfg):
    from src.collectors.sync import fetch_ci_windowed
    from datetime import timezone
    client = WindowedCIClient()
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2)
    since = NOW - timedelta(days=8)
    previously = {
        (NOW - timedelta(days=i)).date().isoformat():
            (NOW - timedelta(hours=12)).isoformat()
        for i in range(9)
    }
    rows, result, *_ = fetch_ci_windowed(client, repo, since, cfg, NOW,
                                         verified_days=previously)
    assert result.complete
    # Today's cached interval is not valid through the current run time.
    assert client.request_count == 1
    assert client.calls[-1].split("..") == [
        NOW.date().isoformat(), NOW.date().isoformat()]
    old = {k: (NOW - timedelta(days=2)).isoformat()
           for k in previously}
    rows, expired, *_ = fetch_ci_windowed(client, repo, since, cfg, NOW,
                                          verified_days=old)
    assert expired.verified_days
    assert client.request_count > 0



def test_verified_day_checkpoints_survive_snapshot_export_and_restore(db, cfg, tmp_path):
    """Each scheduled Actions runner starts from a restored SQLite snapshot."""
    from src.analytics.read import load_reports
    from src.analytics.snapshot import export_snapshot
    from src.collectors.restore import hydrate_snapshot
    from src.database.store import make_engine, init_db, session_factory

    days = {"2026-11-10": NOW.isoformat(), "2026-11-09": NOW.isoformat()}
    db.add(SyncCheckpoint(repo_id=101, source="workflow_runs",
                          status="partial", verified_days=days))
    db.commit()
    report = load_reports(db, now=NOW)
    snapshot = tmp_path / "snapshot.json.gz"
    selection = {"id": 1, "parameters": {"test": "real checkpoint roundtrip"},
                 "candidates": 1, "selected": 1, "decisions": [],
                 "status": "complete"}
    export_snapshot(snapshot, report, selection, generated_at=NOW)

    engine = make_engine(f"sqlite:///{tmp_path / 'rehydrated.sqlite3'}")
    init_db(engine)
    try:
        with session_factory(engine)() as restored:
            result = hydrate_snapshot(restored, snapshot)
            cp = restored.get(SyncCheckpoint, (101, "workflow_runs"))
            assert result["restored"] == 1
            assert cp.verified_days == days
            assert cp.status == "partial"
    finally:
        engine.dispose()


def test_today_requires_actual_ci_recheck_even_when_previously_verified(db, cfg):
    """Never count current-day events as fetched merely from a prior 6h run."""
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2)
    yesterday = (NOW - timedelta(days=1)).date().isoformat()
    today = NOW.date().isoformat()
    client = WindowedCIClient()
    saved = {
        yesterday: (NOW - timedelta(hours=1)).isoformat(),
        today: (NOW - timedelta(hours=1)).isoformat(),
    }
    rows, result, *rest = fetch_ci_windowed(
        client, repo, NOW - timedelta(days=1), cfg, NOW,
        verified_days=saved)
    assert result.complete
    assert len(client.calls) == 1
    assert client.calls[0] == today + ".." + today
    assert result.verified_days[today] == NOW.isoformat()


def test_unverified_current_day_never_passes_entire_window(db, cfg):
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2)
    yesterday = (NOW - timedelta(days=1)).date().isoformat()
    today = NOW.date().isoformat()
    client = WindowedCIClient(cap_daily=True)
    saved = {
        yesterday: NOW.isoformat(),
        today: NOW.isoformat(),
    }
    _, result, *_ = fetch_ci_windowed(
        client, repo, NOW - timedelta(days=1), cfg, NOW,
        verified_days=saved)
    assert not result.complete
    assert result.verified_days.get(today) is None
    assert client.calls == [today + ".." + today]
