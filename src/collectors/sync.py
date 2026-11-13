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


def fetch_source(client: GitHubClient, repo: Repository, source: str, since: datetime,
                 settings: Settings, now: datetime, *, precise_created=False):
    path = f"/repos/{repo.full_name}"
    iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    if source == "issues":
        result = client.paginate(path + "/issues", {"state": "all", "sort": "updated", "direction": "desc", "since": iso, "per_page": settings.per_page}, settings.max_pages, cutoff=since)
    elif source == "pull_requests":
        result = client.paginate(path + "/pulls", {"state": "all", "sort": "updated", "direction": "desc", "per_page": settings.per_page}, settings.max_pages, cutoff=since)
    else:
        # Workflow run filtering supports created, NOT updated/since. Explicit coverage only.
        # Ordinary queries retain exact UTC day semantics. When a busy day
        # hits GitHub's page cap, use UTC hour bounds so completed subwindows
        # can be certified independently. Day coverage is not inferred from
        # any incomplete or skipped hourly shard.
        if precise_created:
            floor_start = utc(since).replace(microsecond=0)
            ceil_end = utc(now).replace(microsecond=0)
            if utc(now).microsecond:
                ceil_end += timedelta(seconds=1)
            bounds = (f"{floor_start.strftime('%Y-%m-%dT%H:%M:%SZ')}.."
                      f"{ceil_end.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        else:
            bounds = f"{since.strftime('%Y-%m-%d')}..{now.strftime('%Y-%m-%d')}"
        result = client.paginate(
            path + "/actions/runs",
            {"created": bounds, "per_page": settings.per_page},
            settings.max_pages, cutoff=since, sort_key="created_at",
            wrapper="workflow_runs")
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
    # Recent completed UTC days or six-hour shards may be reused for 24
    # hours; earlier histories can be retained longer. The CURRENT UTC day
    # is ALWAYS fetched again because a saved shard cannot prove new runs
    # that appeared after that earlier sample was taken.
    cutoff = now.date() - timedelta(days=7)
    reusable, reusable_shards = {}, {}
    for key, last_verified in prior.items():
        if not isinstance(key, str):
            continue
        if len(key) == 10:
            date, is_shard = key, False
        elif len(key) == 13 and key[10] == "@" and key[11:] in ("00", "06", "12", "18"):
            date, is_shard = key[:10], True
        else:
            continue
        try:
            parsed = datetime.fromisoformat(str(last_verified).replace("Z", "+00:00"))
            if date >= now.date().isoformat():
                continue
            if date < cutoff.isoformat() or utc(parsed) >= now - timedelta(hours=24):
                (reusable_shards if is_shard else reusable)[key] = str(last_verified)
        except (ValueError, TypeError):
            continue
    all_dates = [(since.date() + timedelta(days=i)).isoformat()
                 for i in range((now.date() - since.date()).days + 1)]
    required = set(all_dates)
    verified = dict(reusable)
    records = {}
    pages_total = 0
    interval_count = 0

    def load(start_day, end_day, *, precise_bounds=None):
        nonlocal pages_total, interval_count
        remaining = pages_cap - pages_total
        if remaining <= 0:
            return None
        budget = getattr(client, "max_requests", None)
        used = getattr(client, "request_count", 0)
        if budget is not None and used + 2 >= budget:
            return None
        if precise_bounds is not None:
            lower = max(since, precise_bounds[0])
            upper = min(now, precise_bounds[1])
        else:
            lower = max(since, datetime.combine(start_day, time.min,
                                                tzinfo=timezone.utc))
            upper = min(now, datetime.combine(end_day, time.max,
                                              tzinfo=timezone.utc))
        if lower > upper:
            raise ValueError("Cannot certify an empty CI created-time range")
        # Bound one API subinterval; a 6-hour shard does not bypass the
        # pagination cap or the global GitHub API request budget.
        from dataclasses import replace
        bounded_settings = replace(settings, max_pages=min(settings.max_pages, remaining))
        rows, pagination = fetch_source(
            client, repo, "workflow_runs", lower, bounded_settings, upper,
            precise_created=precise_bounds is not None)
        pages_total += pagination.pages
        interval_count += 1
        for row in rows:
            records[row["id"]] = row
        return pagination

    end = now.date()
    partial_shards = dict(reusable_shards)
    while end >= since.date():
        begin = max(since.date(), end - timedelta(days=6))
        days = [(begin + timedelta(days=i)).isoformat()
                for i in range((end - begin).days + 1)]
        missing = [d for d in days if d not in reusable]
        if not missing:
            end = begin - timedelta(days=1)
            continue
        # A previously capped day with certified hour shards must resume
        # from those shards, not waste six pages on the same capped week.
        has_shard_progress = any(
            key.startswith(day + "@")
            for day in missing for key in partial_shards
        )
        if len(missing) == len(days) and len(days) > 1 and not has_shard_progress:
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
        unfinished = False
        for day in reversed(missing):
            day_value = datetime.fromisoformat(day).date()
            old_shards = [key for key in partial_shards if key.startswith(day + "@")]
            if not old_shards:
                try:
                    daily = load(day_value, day_value)
                except Exception:
                    daily = None
                if daily is None:
                    unfinished = True
                    break
                if daily.complete:
                    verified[day] = now.isoformat()
                    continue
            # A capped daily endpoint is not complete. Split into four UTC
            # six-hour intervals and retain each CERTIFIED slice separately.
            # This never treats a capped weekly/day response as a zero or
            # claims any time interval that the API did not exhaust.
            required_shards = []
            for hour in (0, 6, 12, 18):
                lower = datetime.combine(day_value, time(hour=hour),
                                         tzinfo=timezone.utc)
                upper = lower + timedelta(hours=6) - timedelta(seconds=1)
                if upper < since or lower > now:
                    continue
                key = f"{day}@{hour:02d}"
                required_shards.append(key)
                if key in partial_shards:
                    continue
                try:
                    segment = load(day_value, day_value,
                                   precise_bounds=(lower, upper))
                except Exception:
                    segment = None
                if segment is None:
                    unfinished = True
                    break
                if segment.complete:
                    partial_shards[key] = now.isoformat()
            if not unfinished and all(key in partial_shards for key in required_shards):
                verified[day] = now.isoformat()
            if unfinished:
                break
        if unfinished:
            break
        end = begin - timedelta(days=1)

    complete = required.issubset(set(verified))
    result = PageResult(
        items=[], pages=pages_total, complete=complete,
        cap_reached=not complete, cutoff_reached=False)
    # Additional provenance is preserved by sync_one in SyncCheckpoint.
    result.verified_days = {
        key: stamp for key, stamp in sorted({**partial_shards, **verified}.items())
        if key[:10] >= (now.date() - timedelta(days=120)).isoformat()
        and (len(key) == 10 or key[:10] not in verified)
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


def sync_one(session: Session, client: GitHubClient, repo: Repository, source: str,
             settings: Settings, reconcile=False, now=None,
             min_window_days=None) -> dict:
    now = now or utcnow()
    cp = get_checkpoint(session, repo.id, source)
    since = start_window(cp, settings, now, reconcile)
    if min_window_days:
        # A narrow 1/7d successful checkpoint must not permanently trap
        # future syncs in short overlap-only windows. Retry a full 28d
        # event history for a small, deliberately selected subset.
        since = min(since, utc(now) - timedelta(days=min_window_days))
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
        # A failed OPTIONAL broad repair is not evidence that an already
        # verified narrow checkpoint became incomplete. Keep the last
        # complete window and timestamp until genuinely replaced, but log
        # the new partial attempt separately and never claim 28-day coverage.
        preserve_old_complete = bool(
            min_window_days and not pagination.complete
            and cp.status == "complete" and cp.last_success_at
        )
        if not preserve_old_complete:
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
                "attempts": attempts, "window_days": round((now - actual_since).total_seconds() / 86400, 2),
                "requested_repair_window_days": min_window_days}
    except Exception as exc:
        # Revert all in-flight rows/checkpoint changes, keep historical records.
        session.rollback()
        cp = get_checkpoint(session, repo.id, source)
        # An optional historical repair error must not erase an earlier
        # properly completed narrow window; keep its timestamp and status
        # while the failed attempt is recorded in the SyncLog.
        if not (min_window_days and cp.status == "complete"
                and cp.last_success_at):
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
    inventory = cps.get("open_backlog")
    full_backlog = bool(inventory and inventory.status == "complete" and
                        inventory.last_success_at and
                        utc(inventory.last_success_at) >= now - timedelta(hours=12))
    basis = "verified_open_inventory" if full_backlog else "sampled_updated_events"
    session.add(Observation(repo_id=repo_id, measured_at=now,
                            open_issues_observed=len(issues),
                            aged_issues_observed=sum((now - utc(i.created_at)).days >= 30 for i in issues),
                            open_prs_observed=len(prs),
                            collection_basis=basis))
    session.commit()
    return True



def backlog_priority_order(session: Session, repositories: list[Repository],
                           settings: Settings, now: datetime) -> list[Repository]:
    """Use remaining budget for audited 28d cohorts first; rotate fairly.

    This does not promote new repositories or modify source selection.
    Full-backlog inventory is separate from recent-event verification.
    """
    now = utc(now)
    cutoff = now - timedelta(days=28)
    fresh_cutoff = now - timedelta(hours=settings.stale_hours)

    def qualifies(repo):
        for source in SOURCES:
            cp = session.get(SyncCheckpoint, (repo.id, source))
            if (cp is None or cp.status != "complete" or
                    cp.last_success_at is None or cp.coverage_start is None or
                    utc(cp.last_success_at) < fresh_cutoff or
                    utc(cp.coverage_start) > cutoff):
                return False
        return True

    eligible = []
    remainder = []
    for repo in repositories:
        cp = session.get(SyncCheckpoint, (repo.id, "open_backlog"))
        if (cp and cp.status == "complete" and cp.last_success_at and
                utc(cp.last_success_at) >= fresh_cutoff):
            continue
        (eligible if qualifies(repo) else remainder).append(repo)

    slot = int(now.timestamp() // (4 * 3600))
    def rotate(rows):
        rows = sorted(rows, key=lambda r: r.full_name)
        if not rows:
            return rows
        offset = (slot * 7) % len(rows)
        return rows[offset:] + rows[:offset]
    return rotate(eligible) + rotate(remainder)



def verification_maintenance_priority(session: Session, repo: Repository,
                                      settings: Settings, now: datetime):
    """Risk score from ACTUAL 28-day source checkpoints, not inferred activity.

    0 = previously verified across all three sources, expiring within four
        hours (or already stale); refresh it before exploratory work.
    1 = two of three sources have complete 28d coverage; close the gap next.
    2 = all three verified and still comfortably fresh.
    3 = other exploratory/short/partial sources, retained for later scans.

    Stale timestamps never count as currently Verified in the dashboard.
    """
    now = utc(now)
    threshold = now - timedelta(days=28)
    checkpoints = [session.get(SyncCheckpoint, (repo.id, source))
                   for source in SOURCES]
    complete = [cp for cp in checkpoints if (
        cp is not None and cp.status == "complete"
        and cp.coverage_start is not None and cp.last_success_at is not None
        and utc(cp.coverage_start) <= threshold
    )]
    if len(complete) == len(SOURCES):
        oldest_success = min(utc(cp.last_success_at) for cp in complete)
        at_risk = oldest_success <= now - timedelta(
            hours=max(0, settings.stale_hours - 4))
        return (0 if at_risk else 2, oldest_success)
    if len(complete) >= 2:
        return (1, now)
    return (3, now)


def verification_maintenance_order(session: Session,
                                   repositories: list[Repository],
                                   settings: Settings, now: datetime):
    """Refresh expiring 28d cohorts before spending quota on broad repairs.

    Rotate ties every four hours so incomplete sources still get chances.
    Every repository remains selected, including exploratory ones.
    """
    if not repositories:
        return []
    now = utc(now)
    rotated = sorted(repositories, key=lambda r: r.full_name)
    offset = (int(now.timestamp() // (4 * 3600)) * 17) % len(rotated)
    rotated = rotated[offset:] + rotated[:offset]
    ranks = {repo.id: verification_maintenance_priority(
        session, repo, settings, now) for repo in rotated}
    return sorted(rotated, key=lambda r: ranks[r.id])

def coverage_repair_targets(session: Session, repositories: list[Repository],
                            now: datetime, *, max_repos=4) -> dict[int, set[str]]:
    """Target low-page short Issue/PR windows, without selecting easier repos.

    A source with status=complete but coverage_start only 1/7 days ago
    cannot support a 28-day analysis. Standard 48h watermark overlaps
    cannot extend that historical start backward on later runs. Limit
    extra 28d attempts to four repositories per collector run and only
    low-page prior sources; saturated high-volume endpoints remain
    explicitly exploratory until their API history can actually be scanned.
    """
    if max_repos < 1:
        return {}
    cutoff = utc(now) - timedelta(days=28)
    candidates = []
    for repo in repositories:
        sources, effort = set(), 0
        for source in ("issues", "pull_requests"):
            cp = session.get(SyncCheckpoint, (repo.id, source))
            if (cp and cp.status == "complete" and cp.coverage_start and
                    utc(cp.coverage_start) > cutoff and
                    cp.pages_fetched is not None and
                    1 <= int(cp.pages_fetched) <= 4):
                sources.add(source)
                effort += int(cp.pages_fetched)
        if sources:
            candidates.append((repo, sources, effort))
    # Repositories with two repairable source windows get considered first;
    # six-hour slot rotation prevents a fixed set always absorbing the
    # spare scan budget. Eligibility is a cost forecast, NOT source proof.
    candidates.sort(key=lambda item: (-len(item[1]), item[2], item[0].full_name))
    if candidates:
        slot = int(utc(now).timestamp() // (4 * 3600))
        offset = (slot * 3) % len(candidates)
        candidates = candidates[offset:] + candidates[:offset]
    return {repo.id: sources for repo, sources, _ in candidates[:max_repos]}


def synchronize(session: Session, client: GitHubClient, settings: Settings, reconcile=False,
                initial_batch_size: int | None = None, run_at=None,
                audit_open_backlog=False, max_backlog_repos=8,
                repair_coverage=False, max_repair_repos=4) -> list[dict]:
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
            repos = verification_maintenance_order(
                session, repos, settings, run_at or utcnow())
    repair_targets = (
        coverage_repair_targets(session, repos, run_at or utcnow(),
                                max_repos=max_repair_repos)
        if repair_coverage else {}
    )
    if repair_targets:
        # Optional historical repairs must never jump ahead of previously
        # verified cohorts about to lose their 12h freshness. Other repairs
        # still run before comfortable/low-risk sources.
        now = run_at or utcnow()
        critical = [r for r in repos if
                    verification_maintenance_priority(session, r, settings, now)[0] == 0]
        critical_ids = {r.id for r in critical}
        repairs = [r for r in repos if
                   r.id in repair_targets and r.id not in critical_ids]
        handled = critical_ids | {r.id for r in repairs}
        repos = critical + repairs + [r for r in repos if r.id not in handled]
        print("Targeted 28d Issue/PR repair attempts:", {
            r.full_name: sorted(repair_targets[r.id])
            for r in repos if r.id in repair_targets
        })
    visited = []
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
        slot = int((run_at or utcnow()).timestamp() // (4 * 3600))
        source_order = SOURCES[slot % len(SOURCES):] + SOURCES[:slot % len(SOURCES)]
        for source in source_order:
            result.append(sync_one(
                session, client, repo, source, settings,
                reconcile=reconcile, now=run_at or utcnow(),
                min_window_days=(28 if source in repair_targets.get(repo.id, ())
                                 else None)))
        if not audit_open_backlog:
            record_observations(session, repo.id)
        visited.append(repo)

    if audit_open_backlog and repos:
        # Only AFTER normal Issue/PR/CI scans, use remaining API budget.
        # Prioritize current 28-day verified cohorts even if they were not
        # visited in this collection batch. This avoids auditing only the
        # same rotating partial sources while ignoring verified cohorts.
        from src.collectors.backlog import sync_open_backlog
        now = run_at or utcnow()
        all_selected = list(session.scalars(
            select(Repository).where(Repository.selected.is_(True))
        ))
        ordered = backlog_priority_order(session, all_selected, settings, now)
        processed = 0
        for repo in ordered:
            if processed >= max_backlog_repos:
                break
            budget = getattr(client, "max_requests", None)
            if (budget is not None and
                    budget - getattr(client, "request_count", 0) <
                    settings.max_pages + 3):
                break
            result.append(sync_open_backlog(
                session, client, repo, settings, now=now))
            processed += 1
    if audit_open_backlog:
        # Measure AFTER inventory reconciliation; older observation samples
        # use a distinct basis and must not be compared to full inventories.
        for repo in visited:
            record_observations(session, repo.id, now=run_at or utcnow())
    return result
