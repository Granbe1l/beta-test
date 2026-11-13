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
        # Start at the exact decision window. A 30-day bootstrap followed
        # by another 28-day retry spent the page budget on near-duplicate
        # high-volume data, starving other repositories' source scans.
        # An explicit --reconcile still requests the long backfill window.
        return max(baseline, now - timedelta(days=28))
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
                      *, pages_cap=18, verified_days=None):
    """Resume *completed* CI creation-date buckets instead of rescanning them.

    Each UTC calendar day is marked verified only after its bounded source
    scan completed (or an entire week containing it completed). Retain old
    verified days across separate scheduled collection jobs. Recent seven
    days are always revalidated because GitHub workflow conclusions can
    change or a run can be re-run. A completed old bucket attests to the
    retrieved creation-date interval, NOT immutable historical outcomes.

    Every date in the requested window must be verified for a source to
    earn status=complete. Exhausted API budget leaves partial state while
    preserving both rows and completed day buckets for the next run.
    """
    from src.collectors.client import PageResult
    from datetime import time

    since, now = utc(since), utc(now)
    if since > now:
        raise ValueError("source start cannot be after current time")
    prior = verified_days or {}
    if isinstance(prior, list):  # Compatible with possible early checkpoints.
        prior = {d: "1970-01-01T00:00:00+00:00" for d in prior
                 if isinstance(d, str)}
    # Recent days may change due to reruns. Reuse a certified day for only
    # 24 hours; older-than-seven-day creation buckets can be reused longer.
    cutoff = now.date() - timedelta(days=7)
    reusable = {}
    for date, last_verified in prior.items():
        if not isinstance(date, str) or len(date) != 10:
            continue
        try:
            parsed = datetime.fromisoformat(str(last_verified).replace("Z", "+00:00"))
            if date < cutoff.isoformat() or utc(parsed) >= now - timedelta(hours=24):
                reusable[date] = str(last_verified)
        except (ValueError, TypeError):
            continue
    all_dates = [(since.date() + timedelta(days=i)).isoformat()
                 for i in range((now.date() - since.date()).days + 1)]
    required = set(all_dates)
    verified = dict(reusable)
    records = {}
    pages_total = 0
    interval_count = 0

    def load(start_day, end_day):
        nonlocal pages_total, interval_count
        remaining = pages_cap - pages_total
        if remaining <= 0:
            return None
        budget = getattr(client, "max_requests", None)
        used = getattr(client, "request_count", 0)
        if budget is not None and used + 2 >= budget:
            return None
        lower = max(since, datetime.combine(start_day, time.min,
                                            tzinfo=timezone.utc))
        upper = min(now, datetime.combine(end_day, time.max,
                                          tzinfo=timezone.utc))
        # Strict per-repository budget, not an artificially high global
        # page limit that starves sources belonging to other repositories.
        from dataclasses import replace
        bounded_settings = replace(settings, max_pages=min(settings.max_pages, remaining))
        rows, pagination = fetch_source(client, repo, "workflow_runs",
                                        lower, bounded_settings, upper)
        pages_total += pagination.pages
        interval_count += 1
        for row in rows:
            records[row["id"]] = row
        return pagination

    end = now.date()
    while end >= since.date():
        begin = max(since.date(), end - timedelta(days=6))
        days = [(begin + timedelta(days=i)).isoformat()
                for i in range((end - begin).days + 1)]
        missing = [d for d in days if d not in reusable]
        if not missing:
            end = begin - timedelta(days=1)
            continue
        if len(missing) == len(days) and len(days) > 1:
            try:
                weekly = load(begin, end)
            except Exception:
                weekly = None
            if weekly is None:
                break
            if weekly.complete:
                verified.update({d: now.isoformat() for d in missing})
                end = begin - timedelta(days=1)
                continue
        # If a week was capped, resume its individual days. On subsequent
        # runs only incomplete days are queried; already-certified older
        # days are skipped, saving API requests.
        unfinished = False
        for day in reversed(missing):
            try:
                daily = load(datetime.fromisoformat(day).date(),
                             datetime.fromisoformat(day).date())
            except Exception:
                daily = None
            if daily is None:
                unfinished = True
                break
            if daily.complete:
                verified[day] = now.isoformat()
        if unfinished:
            break
        end = begin - timedelta(days=1)

    complete = required.issubset(set(verified))
    result = PageResult(
        items=[], pages=pages_total, complete=complete,
        cap_reached=not complete, cutoff_reached=False)
    # Additional provenance is preserved by sync_one in SyncCheckpoint.
    result.verified_days = {
        d: stamp for d, stamp in sorted(verified.items())
        if d >= (now.date() - timedelta(days=120)).isoformat()
    }
    return list(records.values()), result, since, interval_count, pages_total



def fetch_source_adaptive(client: GitHubClient, repo: Repository, source: str,
                          since: datetime, settings: Settings, now: datetime,
                          *, verified_days=None):
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
        return fetch_ci_windowed(client, repo, since, settings, now,
                                 verified_days=verified_days)

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
            client, repo, source, since, settings, now,
            verified_days=getattr(cp, "verified_days", None) if source == "workflow_runs" else None)
        write_records(session, source, rows)
        status = "complete" if pagination.complete else "partial"
        log.status = status
        log.finished_at = utcnow()
        log.record_count = len(rows)
        log.page_count = total_pages
        cp.status = status
        cp.pages_fetched = total_pages
        cp.records_fetched = len(rows)
        if source == "workflow_runs" and hasattr(pagination, "verified_days"):
            # Persist verified day buckets even for partially complete scans.
            # On the next runner, snapshot restore brings these checkpoints
            # back so we do not waste the whole request budget on the same days.
            cp.verified_days = pagination.verified_days
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
            overdue, incomplete, healthy = [], [], []
            for r in rotated:
                cps = [session.get(SyncCheckpoint, (r.id, source))
                       for source in SOURCES]
                # Refresh formerly-complete stale sources promptly; then
                # resume partials, while keeping healthy projects in rotation.
                has_overdue = any(
                    cp and cp.status == "complete" and
                    (cp.last_success_at is None or
                     utc(cp.last_success_at) < now - timedelta(hours=settings.stale_hours))
                    for cp in cps)
                has_incomplete = any(cp is None or cp.status != "complete"
                                     for cp in cps)
                if has_overdue:
                    overdue.append(r)
                elif has_incomplete:
                    incomplete.append(r)
                else:
                    healthy.append(r)
            ordered = []
            while overdue or incomplete or healthy:
                if overdue:
                    ordered.append(overdue.pop(0))
                for _ in range(2):
                    if incomplete:
                        ordered.append(incomplete.pop(0))
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
        # Rotate source order per six-hour slot; a high-volume Actions
        # scan should not always be last and starved by Issues/PRs.
        slot = int((run_at or utcnow()).timestamp() // (6 * 3600))
        source_order = SOURCES[slot % len(SOURCES):] + SOURCES[:slot % len(SOURCES)]
        for source in source_order:
            result.append(sync_one(session, client, repo, source, settings,
                                   reconcile=reconcile, now=run_at or utcnow()))
        record_observations(session, repo.id)
    return result
