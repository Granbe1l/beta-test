"""Regression checks for adaptive real-data completeness.

A successfully scanned 7-day window is not misrepresented as 120-day history.
Previously persisted records and checkpoint success timestamps survive partials.
"""
from dataclasses import replace
from datetime import timedelta

from src.collectors.client import PageResult
from src.collectors.sync import sync_one, start_window
from src.database.models import Repository, SyncCheckpoint, Issue
from sqlalchemy import select, func
from .conftest import NOW, issue_payload


class AdaptiveClient:
    def __init__(self, limit=1000, always_partial=False):
        self.max_requests = limit
        self.request_count = 0
        self.calls = []
        self.always_partial = always_partial

    def paginate(self, path, params, max_pages, **kwargs):
        self.calls.append((path, params.copy(), kwargs.copy()))
        self.request_count += 1
        since = kwargs.get("cutoff")
        complete = not self.always_partial and since >= NOW - timedelta(days=8)
        return PageResult(
            items=[issue_payload(1), issue_payload(2)],
            pages=max_pages if not complete else 1,
            complete=complete,
            cap_reached=not complete,
            cutoff_reached=False,
        )


def test_adaptive_recent_window_reaches_complete_when_full_backfill_cannot(db, cfg):
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2, backfill_days=120)
    c = AdaptiveClient()
    response = sync_one(db, c, repo, "issues", cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "issues"))
    assert response["status"] == "complete"
    assert response["attempts"] == 2
    assert response["window_days"] == 7
    assert cp.coverage_start.date() == (NOW - timedelta(days=7)).date()
    assert cp.last_success_at.replace(tzinfo=None) == NOW.replace(tzinfo=None)
    assert cp.high_watermark.replace(tzinfo=None) == NOW.replace(tzinfo=None)
    assert response["pages"] == 3
    assert db.scalar(select(func.count()).select_from(Issue)) == 2
    assert len(c.calls) == 2
    assert c.calls[0][2]["cutoff"] == NOW - timedelta(days=30)
    assert c.calls[1][2]["cutoff"] == NOW - timedelta(days=7)


def test_full_cap_after_retries_stays_partial_and_does_not_advance_watermark(db, cfg):
    repo = db.get(Repository, 101)
    c = AdaptiveClient(always_partial=True)
    r = sync_one(db, c, repo, "issues", cfg, now=NOW)
    cp = db.get(SyncCheckpoint, (101, "issues"))
    assert r["status"] == "partial"
    assert r["attempts"] == 3
    assert r["window_days"] == 1
    assert cp.high_watermark is None
    assert cp.last_success_at is None
    assert db.scalar(select(func.count()).select_from(Issue)) == 2


def test_retry_respects_remaining_request_budget_and_preserves_partial(db, cfg):
    repo = db.get(Repository, 101)
    c = AdaptiveClient(limit=2, always_partial=True)
    c.request_count = 1
    res = sync_one(db, c, repo, "issues", cfg, now=NOW)
    assert res["status"] == "partial"
    assert res["attempts"] == 1
    assert c.request_count == 2


def test_fallback_does_not_falsely_extend_previous_coverage_over_gap(db, cfg):
    repo = db.get(Repository, 101)
    cp = db.get(SyncCheckpoint, (101, "issues"))
    if cp is None:
        cp = SyncCheckpoint(repo_id=101, source="issues", status="partial")
        db.add(cp)
    cp.coverage_start = NOW - timedelta(days=90)
    cp.last_success_at = NOW - timedelta(days=25)
    cp.high_watermark = None
    db.commit()

    c = AdaptiveClient()
    res = sync_one(db, c, repo, "issues", cfg, now=NOW)
    assert res["status"] == "complete"
    cp = db.get(SyncCheckpoint, (101, "issues"))
    assert cp.coverage_start.date() == (NOW - timedelta(days=7)).date()


def test_explicit_reconcile_still_requests_full_backfill(db, cfg):
    repo = db.get(Repository, 101)
    cp = SyncCheckpoint(repo_id=101, source="issues", status="unavailable")
    db.add(cp)
    db.commit()
    assert start_window(cp, cfg, NOW, reconcile=True) == NOW - timedelta(days=cfg.backfill_days)
