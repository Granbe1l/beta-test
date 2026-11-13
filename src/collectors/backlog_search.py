"""Bounded GitHub Search fallback for oversized open-Issue backlogs.

REST /issues cannot filter by created date. GitHub Search Issues supports a
created:ISO..ISO qualifier and repo:is:issue:is:open. Search has a 1000
result accessibility cap, so large ranges MUST be bisected. We only
certify complete when EVERY time shard and EVERY requested page are verified
in one attempt, with no incomplete_results warning or budget exhaustion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from src.collectors.client import PageResult
from src.collectors.normalize import issue


def _utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _stamp(value):
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def search_open_issues_by_created(client, repo, settings, *, now=None,
                                  max_calls=20, max_depth=18):
    """Try a strict, single-run inventory using overlapping date-time shards.

    Returns PageResult; partial means NOT all open Issues were collected.
    Date-overlap at bisect boundaries is deduplicated by immutable GitHub ID.
    A complete search is a best-effort GitHub indexed snapshot, not a
    transactional/atomic guarantee against concurrent issue changes.
    """
    now = _utc(now or datetime.now(timezone.utc))
    first = _utc(getattr(repo, "created_at", None) or
                 datetime(2008, 1, 1, tzinfo=timezone.utc))
    if first > now:
        return PageResult([], 0, False, True, False)
    client_get = getattr(client, "get", None)
    if not callable(client_get):
        return PageResult([], 0, False, True, False)

    limit = min(1000, settings.max_pages * settings.per_page)
    results = {}
    calls = 0
    complete = True
    requested = [(first, now, 0)]
    # Only one GitHub repository; no query can read a private source.
    while requested:
        start, end, depth = requested.pop()
        if calls >= max_calls:
            complete = False
            break
        budget = getattr(client, "max_requests", None)
        used = getattr(client, "request_count", 0)
        if budget is not None and budget - used < 3:
            complete = False
            break
        q = (
            f"repo:{repo.full_name} is:issue is:open "
            f"created:{_stamp(start)}..{_stamp(end)}"
        )
        params = {
            "q": q, "per_page": settings.per_page,
            "page": 1, "sort": "created", "order": "asc",
        }
        calls += 1
        try:
            payload, _ = client_get("/search/issues", params)
        except Exception:
            complete = False
            break
        count = payload.get("total_count")
        batch = payload.get("items")
        if (not isinstance(count, int) or count < 0 or
                not isinstance(batch, list)):
            complete = False
            break
        # GitHub Search may report incomplete_results even for a first
        # response with 200. Never interpret that as a full inventory.
        must_split = bool(payload.get("incomplete_results")) or count > limit
        if must_split:
            mid = start + (end - start) / 2
            if depth >= max_depth or (end-start).total_seconds() < 2:
                complete = False
                break
            # Inclusive search boundaries overlap at most one timestamp.
            # Deduplicate rows by GitHub numeric issue ID.
            requested.append((mid, end, depth+1))
            requested.append((start, mid, depth+1))
            continue
        rows = list(batch)
        for page in range(2, ceil(count / settings.per_page) + 1):
            if calls >= max_calls:
                complete = False
                break
            budget = getattr(client, "max_requests", None)
            if budget is not None and budget - getattr(client, "request_count", 0) < 3:
                complete = False
                break
            calls += 1
            try:
                more, _ = client_get("/search/issues", {**params, "page": page})
            except Exception:
                complete = False
                break
            if more.get("incomplete_results") or not isinstance(more.get("items"), list):
                complete = False
                break
            rows.extend(more["items"])
        if not complete:
            break
        # Duplicate IDs/changes during collection should downgrade certainty.
        unique = {raw.get("id"): raw for raw in rows
                  if isinstance(raw, dict) and isinstance(raw.get("id"), int)}
        if len(rows) != count or len(unique) != count:
            complete = False
            break
        for raw in unique.values():
            parsed = issue(raw, repo.id)
            if parsed and parsed.get("state") == "open":
                results[parsed["id"]] = parsed

    return PageResult(
        list(results.values()), calls, complete and not requested,
        not (complete and not requested), False
    )
