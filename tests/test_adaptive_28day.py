"""Adaptive pages must never certify uncollected older GitHub activity."""
from datetime import timedelta
from dataclasses import replace

from src.collectors.sync import fetch_source_adaptive, sync_one
from src.database.models import Repository, SyncCheckpoint
from .conftest import NOW


class Page:
    def __init__(self, complete):
        self.items = []
        self.pages = 1
        self.complete = complete


class CappedThenComplete:
    def __init__(self):
        self.calls = []
        self.request_count = 0
        self.max_requests = 850

    def paginate(self, path, params, pages, **kwargs):
        self.calls.append((path, params, kwargs))
        self.request_count += 1
        return Page(len(self.calls) >= 2)


def test_28_day_adaptive_retry_does_not_claim_30_day_coverage(db, cfg):
    repo = db.get(Repository, 101)
    client = CappedThenComplete()
    cfg = replace(cfg, backfill_days=120, max_pages=6)
    since = NOW - timedelta(days=30)
    records, result, effective_since, attempts, pages = fetch_source_adaptive(
        client, repo, "issues", since, cfg, NOW)
    assert result.complete is True
    assert attempts == 2
    assert pages == 2
    assert effective_since == NOW - timedelta(days=28)
    assert records == []


def test_short_completed_fallback_cannot_certify_original_window(db, cfg):
    repo = db.get(Repository, 101)

    class CompletedSevenDays(CappedThenComplete):
        def paginate(self, path, params, pages, **kwargs):
            self.calls.append((path, params, kwargs))
            self.request_count += 1
            return Page(len(self.calls) >= 3)

    client = CompletedSevenDays()
    cfg = replace(cfg, backfill_days=120, max_pages=6)
    out = sync_one(db, client, repo, "issues", cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "issues"))
    assert out["status"] == "complete"
    assert cp.coverage_start.date() == (NOW - timedelta(days=7)).date()
    assert out["attempts"] == 3
