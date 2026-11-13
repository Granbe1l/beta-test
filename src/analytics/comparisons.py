"""Strictly comparable observations and consistently scoped CI outcomes.

A period comparison is shown only where the exact same repositories have
recorded source-validated backlog observations on both dates. This avoids
inventing historical trends from a recent-updated bounded GitHub API scan.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from src.analytics.metrics import utc


def comparable_observation_pair(reports: list[dict]) -> dict | None:
    """Return latest two dates with at least one common observed repository.

    Compare a fixed matched cohort. No reported percent-change when the
    previous count is zero; no fabricated values for unvisited projects.
    """
    daily = {}
    for report in reports:
        name = report["repository"]["full_name"]
        for observation in report.get("observations") or []:
            when = utc(observation.get("measured_at"))
            if when is None:
                continue
            day = when.date().isoformat()
            value = (observation.get("open_issues_observed"),
                     observation.get("open_prs_observed"))
            basis = observation.get("collection_basis") or "legacy_observed"
            if value[0] is None or value[1] is None:
                continue
            key = (name, day)
            # Retain the last available measurement on each UTC day
            if key not in daily or when > daily[key][0]:
                daily[key] = (when, int(value[0]), int(value[1]), basis)
    dates = sorted({day for _, day in daily}, reverse=True)
    if len(dates) < 2:
        return None
    for latest in dates:
        for earlier in (d for d in dates if d < latest):
            matched = sorted({
                name for name, day in daily if day == latest
                and (name, earlier) in daily
                and daily[(name, earlier)][3] == daily[(name, latest)][3]
            })
            if not matched:
                continue
            return {
                "previous_date": earlier, "current_date": latest,
                "repositories": matched, "matched_count": len(matched),
                "previous_issues": sum(daily[(r, earlier)][1] for r in matched),
                "current_issues": sum(daily[(r, latest)][1] for r in matched),
                "previous_prs": sum(daily[(r, earlier)][2] for r in matched),
                "current_prs": sum(daily[(r, latest)][2] for r in matched),
                "definition": "Observed open items in the same projects using the same collection method on both dates",
            }
    return None


def checks_in_period(runs: list[dict], days: int = 30, now=None) -> dict:
    """One CI numerator/denominator/period for cards, daily bars and donut.

    Unknown conclusions are shown separately and excluded from percentages.
    The complete scan state is not assumed by this function.
    """
    now = utc(now or datetime.now(timezone.utc))
    cutoff = now - timedelta(days=days)
    rows = [r for r in runs
            if r.get("status") == "completed"
            and (created := utc(r.get("created_at"))) is not None
            and cutoff <= created <= now]
    def category(value):
        if value == "success":
            return "Success"
        if value in ("failure", "timed_out"):
            return "Failure / timeout"
        if value == "skipped":
            return "Skipped"
        if value is None:
            return "Unknown"
        return "Other outcomes"
    counts = Counter(category(row.get("conclusion")) for row in rows)
    known = sum(v for k, v in counts.items() if k != "Unknown")
    daily = []
    for row in rows:
        if row.get("conclusion") is None:
            continue
        daily.append({
            "Day": utc(row["created_at"]).date().isoformat(),
            "Outcome": category(row.get("conclusion")),
            "Runs": 1,
        })
    return {
        "period_days": days,
        "total": len(rows),
        "success": counts["Success"],
        "failure": counts["Failure / timeout"],
        "skipped": counts["Skipped"],
        "other": counts["Other outcomes"],
        "unknown": counts["Unknown"],
        "known": known,
        "success_percent": counts["Success"] / known * 100 if known else None,
        "counts": {k: counts[k] for k in
                   ("Success", "Failure / timeout", "Skipped", "Other outcomes")
                   if counts[k]},
        "daily": daily,
    }
