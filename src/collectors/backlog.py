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
from src.database.models import Issue, SyncLog, utcnow
from src.database.store import get_checkpoint, safe_error, write_records


def fetch_open_backlog(client, repo, settings):
    """Ascending oldest-first is stable for examples; never fake completion."""
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
        rows, result = fetch_open_backlog(client, repo, settings)
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
                "Open-issue backlog exceeded bounded API pagination; "
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
