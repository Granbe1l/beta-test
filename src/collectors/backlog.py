"""Bounded, independent audit of CURRENT open GitHub issues.

A recent-updates scan cannot discover very old open issues which were not
updated recently. This separate source is *not* a 28-day event-history scan.
Only a completely exhausted REST pagination can certify its open backlog
at collection time. Pull requests in the Issues endpoint are excluded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select

from src.collectors.normalize import issue
from src.collectors.client import PageResult
from src.collectors.backlog_search import search_open_issues_by_created
from src.database.models import Issue, SyncLog, utcnow
from src.database.store import get_checkpoint, safe_error, write_records


def fetch_open_backlog(client, repo, settings, *, now=None):
    """REST oldest-first scan; shard by creation time only if REST is capped.

    The initial REST source remains observable if Search API calls fail.
    When sharding fully succeeds its returned Issue IDs become the
    authoritative current-open inventory for reconciliation.
    """
    result = client.paginate(
        f"/repos/{repo.full_name}/issues",
        {"state": "open", "sort": "created", "direction": "asc",
         "per_page": settings.per_page},
        settings.max_pages, cutoff=None, sort_key="created_at",
    )
    rows = {}
    for raw in result.items:
        value = issue(raw, repo.id)
        if value is not None and value.get("state") == "open":
            rows[value["id"]] = value
    if not result.complete and callable(getattr(client, "get", None)):
        shard = search_open_issues_by_created(
            client, repo, settings, now=now, max_calls=20)
        if shard.complete:
            # Fully exhausted shards, not an inferred total from partial REST
            rows = {row["id"]: row for row in shard.items}
        else:
            for row in shard.items:
                rows[row["id"]] = row
        total = result.pages + shard.pages
        result = PageResult(
            list(rows.values()), total, bool(shard.complete),
            not shard.complete, False,
        )
    return list(rows.values()), result

def sync_open_backlog(session, client, repo, settings, now=None):
    """Store sampled open rows even on cap; certify only exhausted lists.

    Closed/stale identities are not invented: if a complete current scan no
    longer includes a previously observed open issue, mark it unverified
    rather than assigning a fabricated close time.
    """
    now = now or utcnow()
    cp = get_checkpoint(session, repo.id, "open_backlog")
    log = SyncLog(repo_id=repo.id, source="open_backlog", started_at=now)
    session.add(log)
    session.commit()
    try:
        rows, result = fetch_open_backlog(client, repo, settings, now=now)
        write_records(session, "issues", rows)
        if result.complete:
            observed_ids = {row["id"] for row in rows}
            existing = session.scalars(
                select(Issue).where(Issue.repo_id == repo.id,
                                    Issue.state == "open")
            ).all()
            for previously_open in existing:
                if previously_open.id not in observed_ids:
                    # The endpoint returns both issues and PRs, but this
                    # query deliberately reconciles standalone Issues only.
                    previously_open.state = "not_confirmed_open"
            cp.coverage_start = now
            cp.last_success_at = now
            cp.high_watermark = now
            cp.last_error = None
        else:
            cp.last_error = (
                "Open-issue backlog pagination/search sharding incomplete; "
                "observed rows do not establish total open backlog"
            )
        cp.status = "complete" if result.complete else "partial"
        cp.pages_fetched = result.pages
        cp.records_fetched = len(rows)
        log.status = cp.status
        log.page_count = result.pages
        log.record_count = len(rows)
        log.finished_at = utcnow()
        session.commit()
        return {
            "repo": repo.full_name, "source": "open_backlog",
            "status": cp.status, "records": len(rows), "pages": result.pages,
            "full_open_backlog_verified": bool(result.complete),
        }
    except Exception as exc:
        session.rollback()
        cp = get_checkpoint(session, repo.id, "open_backlog")
        cp.status = "failed"
        cp.last_error = safe_error(exc)
        existing_log = session.get(SyncLog, log.id)
        existing_log.status = "failed"
        existing_log.finished_at = utcnow()
        existing_log.error = safe_error(exc)
        session.commit()
        return {
            "repo": repo.full_name, "source": "open_backlog",
            "status": "failed", "error": type(exc).__name__,
        }
