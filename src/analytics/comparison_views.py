"""Evidence-gated side-by-side repository metrics, with honest sample fallbacks.

No inferred missing records: 0 is reported only for a source whose entire
requested event window was verified, while retrieved sample sizes are always
explicitly exploratory and not comparable performance outcomes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median

from src.analytics.metrics import utc


def _source_window_verified(report: dict, source: str, days: int, now) -> bool:
    if report.get("status", {}).get(source) != "complete":
        return False
    cp = (report.get("coverage") or {}).get(source) or {}
    start = utc(cp.get("coverage_start"))
    return start is not None and start <= now - timedelta(days=days)


def _period_events(rows: list[dict], key: str, days: int, now) -> list[dict]:
    cutoff = now - timedelta(days=days)
    selected = []
    for row in rows:
        timestamp = utc(row.get(key))
        if timestamp is not None and cutoff <= timestamp <= now:
            selected.append(row)
    return selected


def comparison_rows(reports: list[dict], *, days: int = 28, now=None) -> list[dict]:
    """Count event outcomes only when the matching source window is verified."""
    if days not in (7, 28, 90):
        raise ValueError("Comparison window must be 7, 28 or 90 days")
    now = utc(now or datetime.now(timezone.utc))
    results = []
    for report in reports:
        name = report["repository"]["full_name"]
        issues = report.get("issue_rows") or []
        prs = report.get("pr_rows") or []
        ci = report.get("ci_rows") or []
        iv = _source_window_verified(report, "issues", days, now)
        pv = _source_window_verified(report, "pull_requests", days, now)
        cv = _source_window_verified(report, "workflow_runs", days, now)
        closed = _period_events(issues, "closed_at", days, now) if iv else []
        merged = _period_events(prs, "merged_at", days, now) if pv else []
        completed = [v for v in _period_events(ci, "created_at", days, now)
                     if v.get("status") == "completed"] if cv else []
        durations = [
            max((utc(p["merged_at"]) - utc(p["created_at"])).total_seconds()
                / 86400, 0)
            for p in merged if p.get("created_at")
        ]
        known_checks = [v for v in completed if v.get("conclusion") is not None]
        backlog_verified = report.get("open_backlog_status") == "complete"
        i = report.get("issues") or {}
        aged_total = i.get("aged_denominator") if backlog_verified else None
        aged = i.get("aged_open") if backlog_verified else None
        results.append({
            "Repository": name,
            "Category": report["repository"].get("category") or "Other",
            "Event coverage": f"{int(iv)+int(pv)+int(cv)}/3 sources · {days}d",
            f"Issues closed · {days}d": len(closed) if iv else None,
            f"PRs merged · {days}d": len(merged) if pv else None,
            f"Completed CI checks · {days}d": len(completed) if cv else None,
            f"Median PR merge days · {days}d": (
                round(median(durations), 2) if pv and len(durations) >= 5 else None
            ),
            "Open issues aged 30+ (%) · full inventory": (
                round(aged / aged_total * 100, 1)
                if backlog_verified and aged_total is not None
                and aged is not None and aged_total >= 5 else None
            ),
            "Issue records retrieved · exploratory": len(issues),
            "PR records retrieved · exploratory": len(prs),
            "CI records retrieved · exploratory": len(ci),
            "Full open inventory": "verified" if backlog_verified else "not verified",
        })
    return results


def metric_options(days: int) -> list[str]:
    return [
        f"PRs merged · {days}d",
        f"Issues closed · {days}d",
        f"Completed CI checks · {days}d",
        f"Median PR merge days · {days}d",
        "Open issues aged 30+ (%) · full inventory",
        "Issue records retrieved · exploratory",
        "PR records retrieved · exploratory",
        "CI records retrieved · exploratory",
    ]


def preferred_metric(rows: list[dict], days: int) -> str:
    """Pick a meaningful eligible measured category before sample-only fallback."""
    options = metric_options(days)
    for metric in options:
        values = [r[metric] for r in rows if r.get(metric) is not None]
        # Two verified values and at least one measured event give a visible
        # chart. Zero remains a real verified result, but alone uninformative.
        if len(values) >= 2 and any(v > 0 for v in values):
            return metric
    return options[0]


def metric_disclosure(rows: list[dict], metric: str, days: int) -> str:
    verified_count = sum(r.get(metric) is not None for r in rows)
    if "exploratory" in metric:
        return (
            f"Exploratory retrieved-record sizes for {verified_count}/{len(rows)} "
            "repositories. API caps and differing project sizes mean these "
            "are not comparable productivity or health rankings."
        )
    if "full inventory" in metric:
        return (
            f"{verified_count}/{len(rows)} repositories have at least five "
            "open Issues in independently verified full-open inventories. "
            "Age is not lateness or deadline risk."
        )
    return (
        f"{verified_count}/{len(rows)} repositories qualify for the full "
        f"{days}-day source window and minimum sample rule. Missing records "
        "are excluded, not assumed to be zero activity. "
        "Differences do not rank project quality or developer productivity."
    )
