"""Tests for date-bucketed GitHub Actions scans and honest source coverage."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.collectors.client import PageResult
from src.collectors.sync import fetch_source_adaptive, sync_one
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
