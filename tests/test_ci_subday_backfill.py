"""P1.1: full 28-day CI proof must survive high-volume API date caps."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from src.collectors.client import PageResult
from src.collectors.sync import fetch_ci_windowed, fetch_source
from src.database.models import Repository

NOW = datetime(2026, 11, 13, 20, tzinfo=timezone.utc)


class SaturatedCalendarClient:
    """Fixture: date-wide scans cap out but individual six-hour scans exhaust."""
    def __init__(self, *, shards_complete=True):
        self.max_requests = 850
        self.request_count = 0
        self.calls = []
        self.shards_complete = shards_complete

    def paginate(self, path, params, max_pages, **kwargs):
        assert path.endswith("/actions/runs")
        window = params["created"]
        self.calls.append((window, max_pages))
        self.request_count += 1
        hourly = "T" in window
        # Only explicit six-hour slices are complete, never a capped date.
        return PageResult(
            items=[], pages=1 if hourly and self.shards_complete else max_pages,
            complete=hourly and self.shards_complete,
            cap_reached=not (hourly and self.shards_complete),
            cutoff_reached=False)


def test_capped_days_become_verified_only_after_all_real_hour_windows(db, cfg):
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2)
    cli = SaturatedCalendarClient()
    since = NOW - timedelta(days=2)
    rows, status, effective_since, attempts, pages = fetch_ci_windowed(
        cli, repo, since, cfg, NOW, pages_cap=35)
    assert status.complete
    assert pages <= 35
    assert effective_since == since
    assert set(d for d in status.verified_days if len(d) == 10) == {
        "2026-11-11", "2026-11-12", "2026-11-13"}
    # The final oldest partial UTC date may also have a date-wide probe;
    # at least one genuine hourly range must exist for every saturated day.
    assert all(any("T" in query and query.startswith(day)
                   for query, _ in cli.calls)
               for day in ("2026-11-11", "2026-11-12", "2026-11-13"))
    assert cli.request_count == attempts
    assert rows == []  # no test data invented from an empty API response


def test_incomplete_hour_shards_never_certify_a_day(db, cfg):
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2)
    cli = SaturatedCalendarClient(shards_complete=False)
    since = NOW - timedelta(days=2)
    _, status, *_ = fetch_ci_windowed(cli, repo, since, cfg,
                                      NOW, pages_cap=18)
    assert not status.complete
    assert all(len(k) != 10 for k in status.verified_days)
    assert not status.verified_days
    assert all(max_pages <= cfg.max_pages for _, max_pages in cli.calls)


def test_completed_hour_shards_resume_without_claiming_skipped_windows(db, cfg):
    repo = db.get(Repository, 101)
    cfg = replace(cfg, max_pages=2)
    first = SaturatedCalendarClient()
    since = NOW - timedelta(days=2)
    _, partial, *_ = fetch_ci_windowed(first, repo, since, cfg,
                                       NOW, pages_cap=12)
    assert not partial.complete
    assert any("@" in key for key in partial.verified_days)
    assert "2026-11-11" not in partial.verified_days
    second = SaturatedCalendarClient()
    _, done, *_ = fetch_ci_windowed(
        second, repo, since, cfg, NOW+timedelta(hours=1), pages_cap=12,
        verified_days=partial.verified_days)
    assert done.complete
    assert "2026-11-11" in done.verified_days
    assert "2026-11-12" in done.verified_days
    assert "2026-11-13" in done.verified_days


def test_precise_actions_created_filter_is_hour_bounded(db, cfg):
    repo = db.get(Repository, 101)
    cli = SaturatedCalendarClient()
    first = datetime(2026, 11, 13, 6, 0, tzinfo=timezone.utc)
    last = datetime(2026, 11, 13, 11, 59, 59, tzinfo=timezone.utc)
    rows, result = fetch_source(cli, repo, "workflow_runs", first, cfg, last,
                                precise_created=True)
    assert rows == [] and result.complete
    assert cli.calls[0][0] == (
        "2026-11-13T06:00:00Z..2026-11-13T11:59:59Z")
