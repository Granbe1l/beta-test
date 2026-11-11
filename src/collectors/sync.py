"""Atomic, bounded, incremental GitHub ingestion (not a complete history mirror)."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from src.collectors.client import GitHubClient
from src.collectors.normalize import issue, pull_request, workflow_run
from src.database.models import Repository, Issue, PullRequest, Observation, SyncCheckpoint, SyncLog, utcnow
from src.database.store import get_checkpoint, safe_error, write_records
from src.config.settings import Settings

NORMALIZERS = {"issues": issue, "pull_requests": pull_request, "workflow_runs": workflow_run}
SOURCES = ("issues", "pull_requests", "workflow_runs")


def utc(dt):
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


@contextmanager
def sync_lock(engine):
    """One global writer: PostgreSQL advisory lock or an exclusive local lockfile."""
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            acquired = conn.execute(text("SELECT pg_try_advisory_lock(58621911)")).scalar()
            if not acquired: raise RuntimeError("another sync is running")
            try: yield
            finally: conn.execute(text("SELECT pg_advisory_unlock(58621911)"))
    else:
        path = Path(engine.url.database or "local.sqlite3").with_suffix(".sync.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(path, "a+")
        try:
            if os.name == "nt":
                import msvcrt
                fh.write(" "); fh.flush()
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            fh.close()


def start_window(cp: SyncCheckpoint, settings: Settings, now: datetime, reconcile: bool) -> datetime:
    baseline = now - timedelta(days=settings.backfill_days)
    if reconcile or not cp.high_watermark:
        return baseline
    # All source endpoints use overlap; GitHub workflow runs filter by created date.
    return max(baseline, utc(cp.high_watermark) - timedelta(hours=settings.overlap_hours if cp.source != "workflow_runs" else max(336, settings.overlap_hours)))


def fetch_source(client: GitHubClient, repo: Repository, source: str, since: datetime, settings: Settings, now: datetime):
    path = f"/repos/{repo.full_name}"
    iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    if source == "issues":
        result = client.paginate(path + "/issues", {"state": "all", "sort": "updated", "direction": "desc", "since": iso, "per_page": settings.per_page}, settings.max_pages, cutoff=since)
    elif source == "pull_requests":
        result = client.paginate(path + "/pulls", {"state": "all", "sort": "updated", "direction": "desc", "per_page": settings.per_page}, settings.max_pages, cutoff=since)
    else:
        # Workflow run filtering supports created, NOT updated/since. Explicit coverage only.
        bounds = f"{since.strftime('%Y-%m-%d')}..{now.strftime('%Y-%m-%d')}"
        result = client.paginate(path + "/actions/runs", {"created": bounds, "per_page": settings.per_page}, settings.max_pages, cutoff=since, sort_key="created_at", wrapper="workflow_runs")
    normalized = []
    seen = set()
    for raw in result.items:
        row = NORMALIZERS[source](raw, repo.id)
        if row and row["id"] not in seen:
            normalized.append(row)
            seen.add(row["id"])
    return normalized, result


def sync_one(session: Session, client: GitHubClient, repo: Repository, source: str, settings: Settings, reconcile=False, now=None) -> dict:
    now = now or utcnow()
    cp = get_checkpoint(session, repo.id, source)
    since = start_window(cp, settings, now, reconcile)
    log = SyncLog(repo_id=repo.id, source=source, started_at=now)
    session.add(log)
    session.commit()
    try:
        rows, pagination = fetch_source(client, repo, source, since, settings, now)
        write_records(session, source, rows)
        status = "complete" if pagination.complete else "partial"
        log.status = status
        log.finished_at = utcnow()
        log.record_count = len(rows)
        log.page_count = pagination.pages
        cp.status = status
        cp.pages_fetched = pagination.pages
        cp.records_fetched = len(rows)
        cp.last_error = None
        if pagination.complete:
            cp.last_success_at = now
            cp.coverage_start = min(since, utc(cp.coverage_start)) if cp.coverage_start else since
            # Watermark set to retrieval time to ensure no-change runs advance too.
            # Overlap protects against late indexing / updates.
            cp.high_watermark = now
        session.commit()
        return {"repo": repo.full_name, "source": source, "status": status, "records": len(rows), "pages": pagination.pages}
    except Exception as exc:
        # Revert all in-flight rows/checkpoint changes, keep historical records.
        session.rollback()
        cp = get_checkpoint(session, repo.id, source)
        cp.status = "failed"
        cp.last_error = safe_error(exc)
        persisted_log = session.get(SyncLog, log.id)
        persisted_log.status = "failed"
        persisted_log.finished_at = utcnow()
        persisted_log.error = safe_error(exc)
        session.commit()
        return {"repo": repo.full_name, "source": source, "status": "failed", "error": type(exc).__name__}


def record_observations(session: Session, repo_id: int, now=None):
    now = now or utcnow()
    cps = {cp.source: cp for cp in session.scalars(select(SyncCheckpoint).where(SyncCheckpoint.repo_id == repo_id))}
    if not all(cps.get(s) and cps[s].status == "complete" for s in ("issues", "pull_requests")):
        return False
    issues = list(session.scalars(select(Issue).where(Issue.repo_id == repo_id, Issue.state == "open")))
    prs = list(session.scalars(select(PullRequest).where(PullRequest.repo_id == repo_id, PullRequest.state == "open")))
    session.add(Observation(repo_id=repo_id, measured_at=now,
                            open_issues_observed=len(issues),
                            aged_issues_observed=sum((now - utc(i.created_at)).days >= 30 for i in issues),
                            open_prs_observed=len(prs)))
    session.commit()
    return True


def synchronize(session: Session, client: GitHubClient, settings: Settings, reconcile=False,
                initial_batch_size: int | None = None, run_at=None) -> list[dict]:
    result = []
    repos = list(session.scalars(select(Repository).where(Repository.selected.is_(True)).order_by(Repository.full_name)))
    if initial_batch_size is not None and initial_batch_size > 0:
        # Bootstrap previously unseen repositories gradually. Once all have
        # a checkpoint, incrementally refresh all selected repos each cycle.
        first_time = [r for r in repos if not any(
            session.get(SyncCheckpoint, (r.id, source)) is not None
            for source in SOURCES
        )]
        if first_time:
            repos = first_time[:initial_batch_size]
        elif repos:
            # Rotate traversal order to avoid starving later repositories
            # when the GitHub API request budget is exhausted.
            slot = int((run_at or utcnow()).timestamp() // (6 * 3600))
            offset = (slot * 17) % len(repos)
            repos = repos[offset:] + repos[:offset]
    for repo in repos:
        # Stop before exhausting the allocated API quota; never mark unvisited
        # repositories as failed or advance their last-success timestamps.
        budget = getattr(client, "max_requests", None)
        if budget is not None and getattr(client, "request_count", 0) + 3 * settings.max_pages + 5 >= budget:
            print("Collector request budget reached: unvisited repositories retain prior checkpoints")
            break
        for source in SOURCES:
            result.append(sync_one(session, client, repo, source, settings, reconcile=reconcile))
        record_observations(session, repo.id)
    return result
