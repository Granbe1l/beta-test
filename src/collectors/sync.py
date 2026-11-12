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
    if reconcile:
        return baseline
    if not cp.high_watermark:
        # A first complete scan of a recent 30-day window is more useful
        # than repeatedly hitting a six-page cap over 120+ days.
        # A separate explicit --reconcile still attempts the long backfill.
        return max(baseline, now - timedelta(days=30))
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


def fetch_ci_windowed(client: GitHubClient, repo: Repository,
                      since: datetime, settings: Settings, now: datetime,
                      *, pages_cap=42):
    """Collect GitHub Actions within non-overlapping UTC calendar windows.

    A busy repo can exceed six pages in one month even when each individual
    week or day fits. The GitHub created parameter supports date ranges:
    split into <=7-day intervals, then individual days on capped weeks.
    Every interval must complete before certifying the requested window.
    """
    from src.collectors.client import PageResult
    from datetime import time

    since = utc(since)
    now = utc(now)
    if since > now:
        raise ValueError("source start cannot be after current time")
    records = {}
    consumed = 0
    fully_scanned = True
    interval_count = 0

    def load(first_day, last_day):
        nonlocal consumed, interval_count
        budget = getattr(client, "max_requests", None)
        used = getattr(client, "request_count", 0)
        if consumed >= pages_cap or (budget is not None and used + 2 >= budget):
            return None
        lower = max(since, datetime.combine(first_day, time.min, tzinfo=timezone.utc))
        upper = min(now, datetime.combine(last_day, time.max, tzinfo=timezone.utc))
        rows, result = fetch_source(client, repo, "workflow_runs",
                                    lower, settings, upper)
        consumed += result.pages
        interval_count += 1
        for row in rows:
            records[row["id"]] = row
        return result

    ending = now.date()
    while ending >= since.date():
        beginning = max(since.date(), ending - timedelta(days=6))
        try:
            weekly = load(beginning, ending)
        except Exception:
            fully_scanned = False
            break
        if weekly is None:
            fully_scanned = False
            break
        if not weekly.complete:
            # Retain partial weekly rows, but verify EACH daily interval.
            day = ending
            while day >= beginning:
                try:
                    daily = load(day, day)
                except Exception:
                    fully_scanned = False
                    break
                if daily is None or not daily.complete:
                    fully_scanned = False
                    break
                day -= timedelta(days=1)
            if day >= beginning:
                fully_scanned = False
        if not fully_scanned:
            break
        ending = beginning - timedelta(days=1)

    result = PageResult(
        items=[], pages=consumed, complete=fully_scanned,
        cap_reached=not fully_scanned, cutoff_reached=False
    )
    return list(records.values()), result, since, interval_count, consumed


def fetch_source_adaptive(client: GitHubClient, repo: Repository, source: str,
                          since: datetime, settings: Settings, now: datetime):
    """Narrow an overflowing recent-window scan without inventing completeness.

    The first bounded attempt is preserved. If its page limit is reached,
    retry over seven and then one day. Old evidence remains in the database;
    the source checkpoint records the ACTUAL completed window, never the
    originally requested larger window. Explicit reconciliation also retains
    the broad attempt's fetched rows.
    """
    # GitHub Actions supports created-date filtering: partition busy
    # sources so capped 30-day lists do not automatically stay partial.
    if source == "workflow_runs" and (utc(now) - utc(since)).days <= 32:
        return fetch_ci_windowed(client, repo, since, settings, now)

    candidates = [since]
    # Try a comparable 28-day window before falling back to shorter 7/1-day
    # windows. A successful short window never certifies the whole month.
    for days in (28, 7, 1):
        narrowed = max(since, now - timedelta(days=days))
        if narrowed > candidates[-1]:
            candidates.append(narrowed)

    merged = {}
    total_pages = 0
    attempts = 0
    result = None
    effective_since = since
    for candidate in candidates:
        # Preserve enough API calls to continue to another source/repository.
        budget = getattr(client, "max_requests", None)
        used = getattr(client, "request_count", 0)
        if attempts and budget is not None and used + settings.max_pages + 1 > budget:
            break
        try:
            rows, attempt_result = fetch_source(client, repo, source,
                                                candidate, settings, now)
        except Exception:
            if not attempts:
                raise
            # A failed narrower retry must not discard a successful
            # previous bounded-but-partial page set.
            break
        attempts += 1
        total_pages += attempt_result.pages
        effective_since = candidate
        result = attempt_result
        for row in rows:
            merged[row["id"]] = row
        if result.complete:
            break
    if result is None:
        raise RuntimeError("No GitHub source response was available")
    return list(merged.values()), result, effective_since, attempts, total_pages


def sync_one(session: Session, client: GitHubClient, repo: Repository, source: str, settings: Settings, reconcile=False, now=None) -> dict:
    now = now or utcnow()
    cp = get_checkpoint(session, repo.id, source)
    since = start_window(cp, settings, now, reconcile)
    log = SyncLog(repo_id=repo.id, source=source, started_at=now)
    session.add(log)
    session.commit()
    try:
        rows, pagination, actual_since, attempts, total_pages = fetch_source_adaptive(
            client, repo, source, since, settings, now)
        write_records(session, source, rows)
        status = "complete" if pagination.complete else "partial"
        log.status = status
        log.finished_at = utcnow()
        log.record_count = len(rows)
        log.page_count = total_pages
        cp.status = status
        cp.pages_fetched = total_pages
        cp.records_fetched = len(rows)
        cp.last_error = (
            None if pagination.complete else
            "Page cap reached; source remains partial for requested window"
        )
        if pagination.complete:
            # Read the OLD checkpoint before advancing its success timestamp.
            old_start = utc(cp.coverage_start) if cp.coverage_start else None
            old_success = utc(cp.last_success_at) if cp.last_success_at else None
            # A narrow fallback certifies only that fallback window.
            # Historical coverage can be retained only if the previous
            # complete window overlaps this one, with no unscanned gap.
            if old_start and old_success and old_success >= actual_since:
                cp.coverage_start = min(old_start, actual_since)
            else:
                cp.coverage_start = actual_since
            cp.last_success_at = now
            # Watermark set to retrieval time to ensure no-change runs advance too.
            # Overlap protects against late indexing / updates.
            cp.high_watermark = now
        session.commit()
        return {"repo": repo.full_name, "source": source,
                "status": status, "records": len(rows), "pages": total_pages,
                "attempts": attempts, "window_days": round((now - actual_since).total_seconds() / 86400, 2)}
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




def refresh_repo_metadata(session: Session, client, repo: Repository, now=None) -> bool:
    """Refresh last-push metadata without changing the selected cohort.

    A recent GitHub push is a signal of repository activity, not evidence of
    a new feature. Failed lookups preserve the last known metadata and do
    not invalidate independently collected issues/PR records.
    """
    get = getattr(client, "get", None)
    if get is None:  # Simple deterministic clients in unit tests
        return False
    try:
        data, _ = get(f"/repos/{repo.full_name}")
        if not isinstance(data, dict) or int(data.get("id", -1)) != repo.id:
            raise ValueError("GitHub repository ID mismatch")
        pushed = data.get("pushed_at")
        if pushed:
            repo.pushed_at = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        if isinstance(data.get("stargazers_count"), int):
            repo.stars = data["stargazers_count"]
        if isinstance(data.get("archived"), bool):
            repo.archived = data["archived"]
        if isinstance(data.get("language"), str):
            repo.language = data["language"]
            from src.discovery.selection import category
            repo.category = category({"language": repo.language})
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        print(f"Repository metadata unavailable for {repo.full_name}: {type(exc).__name__}")
        return False

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
        # Bootstrap completely unvisited repositories before refreshing the
        # rest. Once seeded, rotate and interleave partial/stale with complete
        # sources so neither group can starve under the API budget.
        first_time = [r for r in repos if not any(
            session.get(SyncCheckpoint, (r.id, source)) is not None
            for source in SOURCES)]
        if first_time:
            repos = first_time[:initial_batch_size]
        elif repos:
            slot = int((run_at or utcnow()).timestamp() // (6 * 3600))
            offset = (slot * 17) % len(repos)
            rotated = repos[offset:] + repos[:offset]
            now = run_at or utcnow()
            needs, healthy = [], []
            for r in rotated:
                cps = [session.get(SyncCheckpoint, (r.id, source))
                       for source in SOURCES]
                is_incomplete = any(
                    cp is None or cp.status != "complete" or
                    cp.last_success_at is None or
                    utc(cp.last_success_at) < now - timedelta(hours=settings.stale_hours)
                    for cp in cps)
                (needs if is_incomplete else healthy).append(r)
            ordered = []
            # Prefer incompletes while keeping a fair share of healthy repos.
            while needs or healthy:
                ordered.extend(needs[:2])
                del needs[:2]
                if healthy:
                    ordered.append(healthy.pop(0))
            repos = ordered
    for repo in repos:
        # Stop before exhausting the allocated API quota; never mark unvisited
        # repositories as failed or advance their last-success timestamps.
        budget = getattr(client, "max_requests", None)
        if budget is not None and getattr(client, "request_count", 0) + 3 * settings.max_pages * 3 + 6 >= budget:
            print("Collector request budget reached: unvisited repositories retain prior checkpoints")
            break
        refresh_repo_metadata(session, client, repo, now=run_at or utcnow())
        for source in SOURCES:
            result.append(sync_one(session, client, repo, source, settings, reconcile=reconcile))
        record_observations(session, repo.id)
    return result
