"""Observed daily GitHub issue and pull-request event series, without invented values.

Only real timestamped events in the selected curated repositories are counted.
A bounded/recent-biased API collection is NOT a complete historical trend.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from src.analytics.metrics import utc

FIELDS = (
    ("issue_rows", "created_at", "Issues opened"),
    ("issue_rows", "closed_at", "Issues closed"),
    ("pr_rows", "created_at", "PRs opened"),
    ("pr_rows", "merged_at", "PRs merged"),
)


def daily_event_series(reports: list[dict], days: int = 28, now=None) -> list[dict]:
    """One row per calendar day (UTC) in [today-(days-1), today], inclusive.

    Zeros mean no matching events in *retrieved records*, not no actual work.
    """
    if not isinstance(days, int) or not 1 <= days <= 90:
        raise ValueError("days must be an integer in 1..90")
    now = utc(now or datetime.now(timezone.utc))
    start_date = now.date() - timedelta(days=days - 1)
    values = {}
    for offset in range(days):
        date = (start_date + timedelta(days=offset)).isoformat()
        values[date] = {"Date": date, "Issues opened": 0, "Issues closed": 0,
                        "PRs opened": 0, "PRs merged": 0}
    for report in reports:
        for rows_key, timestamp_key, metric in FIELDS:
            for record in report.get(rows_key) or []:
                stamp = utc(record.get(timestamp_key))
                if not stamp or stamp > now:
                    continue
                key = stamp.date().isoformat()
                if key in values:
                    values[key][metric] += 1
    return list(values.values())


def observed_event_totals(series: list[dict]) -> dict[str, int]:
    return {key: sum(day[key] for day in series)
            for key in ("Issues opened", "Issues closed", "PRs opened", "PRs merged")}

def calendar_activity(reports: list[dict], days: int = 7, now=None) -> dict:
    """Use the same UTC calendar dates as daily_event_series (today partial).

    Unlike rolling N*24 hours, the first day begins at midnight UTC.
    Push metadata is descriptive; no release or project outcome is inferred.
    """
    now = utc(now or datetime.now(timezone.utc))
    totals = observed_event_totals(daily_event_series(reports, days=days, now=now))
    first = now.date() - timedelta(days=days - 1)
    pushes = 0
    for report in reports:
        pushed = utc((report.get("repository") or {}).get("pushed_at"))
        if pushed is not None and first <= pushed.date() <= now.date() and pushed <= now:
            pushes += 1
    return {
        "pushed_recently": pushes,
        "new_issues": totals["Issues opened"],
        "closed_issues": totals["Issues closed"],
        "new_prs": totals["PRs opened"],
        "merged_prs": totals["PRs merged"],
        "utc_first_date": first.isoformat(),
        "utc_last_date": now.date().isoformat(),
    }
