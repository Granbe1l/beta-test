"""Pure view-model helpers; use no Streamlit runtime and never mutate source rows."""
from __future__ import annotations

from datetime import datetime, timezone
from src.analytics.metrics import utc


def issue_age_days(record: dict, now: datetime | None = None) -> float:
    """Open item age vs closed item lifetime, in days (not a lateness claim)."""
    now = utc(now or datetime.now(timezone.utc))
    closed = utc(record.get("closed_at")) if record.get("state") == "closed" else None
    end = closed or now
    return max(0.0, (end - utc(record["created_at"])).total_seconds() / 86400)


def filter_work_items(rows: list[dict], search: str = "", state: str = "All", age: str = "All",
                      label: str = "All", now: datetime | None = None) -> list[dict]:
    """Filter issue register. Missing matches never imply absent repository work."""
    now = utc(now or datetime.now(timezone.utc))
    term = search.strip().casefold()
    filtered = []
    for record in rows:
        if state != "All" and record.get("state", "").casefold() != state.casefold():
            continue
        title = (record.get("title") or "").casefold()
        if term and term not in title and term not in str(record.get("number", "")):
            continue
        if label != "All" and label not in (record.get("labels") or []):
            continue
        days = issue_age_days(record, now)
        if age == "0–6 days" and not days < 7:
            continue
        if age == "7–29 days" and not 7 <= days < 30:
            continue
        if age == "30–89 days" and not 30 <= days < 90:
            continue
        if age == "90+ days" and days < 90:
            continue
        filtered.append(record)
    return sorted(filtered, key=lambda r: utc(r["created_at"]), reverse=True)


def filter_pull_requests(rows: list[dict], search: str = "", state: str = "All",
                         draft: str = "All", sort: str = "Newest", now: datetime | None = None) -> list[dict]:
    now = utc(now or datetime.now(timezone.utc))
    term = search.strip().casefold()
    filtered = []
    for record in rows:
        if state != "All" and record.get("state", "").casefold() != state.casefold():
            continue
        if draft == "Draft only" and not record.get("draft"):
            continue
        if draft == "Not draft" and record.get("draft"):
            continue
        if term and term not in (record.get("title") or "").casefold() and term not in str(record.get("number", "")):
            continue
        filtered.append(record)
    if sort == "Longest open":
        filtered.sort(key=lambda r: (r.get("state") == "open", issue_age_days(r, now)), reverse=True)
    else:
        filtered.sort(key=lambda r: utc(r["created_at"]), reverse=sort != "Oldest")
    return filtered


def filter_workflow_runs(rows: list[dict], search: str = "", outcome: str = "All", branch: str = "All") -> list[dict]:
    term = search.strip().casefold()
    filtered = [r for r in rows if
                (not term or term in (r.get("workflow_name") or "").casefold())
                and (outcome == "All" or r.get("conclusion") == outcome)
                and (branch == "All" or r.get("branch") == branch)]
    return sorted(filtered, key=lambda r: utc(r["created_at"]), reverse=True)


def page_slice(items: list, page: int = 1, per_page: int = 10) -> list:
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be positive")
    return items[(page - 1) * per_page:page * per_page]
