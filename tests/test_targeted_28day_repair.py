"""Real source-provenance semantics for limited 28-day repair attempts."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from src.collectors.client import PageResult
from src.collectors.sync import coverage_repair_targets, sync_one, utc
from src.database.models import Repository, SyncCheckpoint

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)


def _checkpoint(repo_id, source, *, days=7, pages=2, status="complete"):
    return SyncCheckpoint(
        repo_id=repo_id, source=source, status=status,
        coverage_start=NOW-timedelta(days=days),
        high_watermark=NOW-timedelta(hours=1),
        last_success_at=NOW-timedelta(hours=1),
        pages_fetched=pages, records_fetched=5,
    )


class RecordedDateClient:
    def __init__(self, complete=True):
        self.calls=[]
        self.complete=complete
        self.max_requests=850
        self.request_count=0

    def paginate(self, path, params, max_pages, **kwargs):
        self.calls.append((path, params))
        self.request_count += 1
        return PageResult(items=[], pages=1 if self.complete else max_pages,
                          complete=self.complete, cap_reached=not self.complete,
                          cutoff_reached=False)


def test_exact_full_28d_history_can_upgrade_old_narrow_source_only_after_complete(db, cfg):
    repository=db.get(Repository, 101)
    db.add(_checkpoint(101, "issues"))
    db.commit()
    client=RecordedDateClient()
    result=sync_one(db, client, repository, "issues", cfg, now=NOW,
                    min_window_days=28)
    assert result["status"] == "complete"
    assert result["requested_repair_window_days"] == 28
    assert result["window_days"] == 28
    assert client.calls[0][1]["since"] == (NOW-timedelta(days=28)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    checkpoint=db.get(SyncCheckpoint, (101,"issues"))
    # SQLite stores timezone-naive DATETIME; compare normalized UTC instants.
    assert utc(checkpoint.coverage_start) <= NOW-timedelta(days=28)


def test_capped_28d_attempt_remains_partial_and_does_not_fake_coverage(db,cfg):
    repository=db.get(Repository,101)
    cp=_checkpoint(101,"pull_requests")
    db.add(cp); db.commit()
    old=cp.coverage_start
    old_success=cp.last_success_at
    old_pages=cp.pages_fetched
    client=RecordedDateClient(complete=False)
    result=sync_one(db,client,repository,"pull_requests",cfg,now=NOW,
                    min_window_days=28)
    assert result["status"] == "partial"
    assert result["requested_repair_window_days"] == 28
    saved=db.get(SyncCheckpoint,(101,"pull_requests"))
    assert saved.coverage_start == old
    assert saved.last_success_at == old_success
    assert saved.pages_fetched == old_pages
    assert saved.status == "complete"  # The earlier 7d scan was genuinely complete
    assert "Page cap" in saved.last_error


def test_repair_selector_prefers_two_short_solvable_sources_and_skips_high_caps(db,cfg):
    rows=[db.get(Repository,101)]
    for num in (102,103,104):
        row=Repository(id=num,owner="public",name=str(num),
                       full_name=f"public/{num}",
                       url=f"https://github.com/public/{num}",
                       language="Python",category="Data & backend",
                       selected=True,stars=50)
        db.add(row);rows.append(row)
    db.add_all([
        _checkpoint(101,"issues",days=7,pages=2),
        _checkpoint(102,"issues",days=7,pages=2),
        _checkpoint(102,"pull_requests",days=6,pages=2),
        _checkpoint(103,"issues",days=7,pages=18),
        _checkpoint(104,"issues",days=45,pages=1),
    ])
    db.commit()
    selected=coverage_repair_targets(db,rows,NOW,max_repos=4)
    assert selected == {101:{"issues"}, 102:{"issues","pull_requests"}}
    restricted=coverage_repair_targets(db,rows,NOW,max_repos=1)
    assert len(restricted)==1
    assert next(iter(restricted)) in (101,102)
    assert coverage_repair_targets(db,rows,NOW,max_repos=0)=={}


def test_workflow_uses_bounded_repair_without_removing_75_original_repos():
    from pathlib import Path
    workflow=(Path(__file__).resolve().parents[1]/
              ".github/workflows/public-snapshot.yml").read_text()
    assert "--repair-coverage" in workflow
    assert "MAX_REPOS: '75'" in workflow
    assert "--max-requests 850" in workflow
    assert "MAX_PAGES_PER_SOURCE: '6'" in workflow


def test_failed_optional_repair_preserves_last_valid_short_checkpoint(db, cfg):
    repository = db.get(Repository,101)
    cp = _checkpoint(101,"issues",days=7,pages=2)
    db.add(cp)
    db.commit()
    old = cp.last_success_at
    class ErrorClient:
        max_requests = 850
        request_count = 0
        def paginate(self, *args, **kwargs):
            raise RuntimeError("Synthetic API error for isolated test")
    result = sync_one(db, ErrorClient(), repository, "issues", cfg,
                      now=NOW, min_window_days=28)
    saved = db.get(SyncCheckpoint, (101, "issues"))
    assert result["status"] == "failed"
    assert saved.status == "complete"
    assert saved.last_success_at == old
    assert "Synthetic API error for isolated test" in saved.last_error
