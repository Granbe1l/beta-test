"""Transparent recent-activity signals for the curated GitHub repository sample.

Last push is metadata, not proof of a feature release. Issue/PR events come
only from collected records; they can be incomplete, and absence is not zero.
No guessed commit history or synthetic period-over-period trend is generated.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from src.analytics.metrics import utc


def within_window(value, now, days=7):
    stamp = utc(value)
    if not stamp:
        return False
    now = utc(now)
    return now - timedelta(days=days) <= stamp <= now + timedelta(minutes=5)


def recent_activity(report, now=None, days=7):
    """Auditable events that have happened, not inferred project milestones."""
    now = utc(now or datetime.now(timezone.utc))
    repo = report.get("repository") or {}
    issues = report.get("issue_rows") or []
    prs = report.get("pr_rows") or []
    opened_issues = sum(within_window(x.get("created_at"), now, days) for x in issues)
    closed_issues = sum(within_window(x.get("closed_at"), now, days) for x in issues)
    opened_prs = sum(within_window(x.get("created_at"), now, days) for x in prs)
    merged_prs = sum(within_window(x.get("merged_at"), now, days) for x in prs)
    pushed = within_window(repo.get("pushed_at"), now, days)
    event_activity = any((opened_issues, closed_issues, opened_prs, merged_prs))
    return {
        "pushed_recently": pushed,
        "recent_issue_or_pr_event": event_activity,
        "new_issues": opened_issues,
        "closed_issues": closed_issues,
        "new_prs": opened_prs,
        "merged_prs": merged_prs,
        "pushed_at": utc(repo.get("pushed_at")),
    }


def sample_activity(reports, now=None, days=7):
    now = utc(now or datetime.now(timezone.utc))
    items = [(r, recent_activity(r, now, days)) for r in reports]
    return {
        "repositories": len(items),
        "pushed_recently": sum(x["pushed_recently"] for _, x in items),
        "with_issue_or_pr_events": sum(x["recent_issue_or_pr_event"] for _, x in items),
        "new_issues": sum(x["new_issues"] for _, x in items),
        "closed_issues": sum(x["closed_issues"] for _, x in items),
        "new_prs": sum(x["new_prs"] for _, x in items),
        "merged_prs": sum(x["merged_prs"] for _, x in items),
        "items": items,
        "days": days,
    }


def activity_label(report, now=None, days=7):
    """Status is descriptive and never labels a repo as finished."""
    a = recent_activity(report, now, days)
    if a["pushed_recently"] and a["recent_issue_or_pr_event"]:
        return "Recent code + collaboration"
    if a["pushed_recently"]:
        return "Recent code push"
    if a["recent_issue_or_pr_event"]:
        return "Recent issue/PR activity"
    return "No recent signal in collected data"


def weekly_activity(reports, now=None, weeks=8):
    """Counts true observed event timestamps; not counts of daily snapshots."""
    now = utc(now or datetime.now(timezone.utc))
    since = now - timedelta(weeks=weeks)
    first = (since.date() - timedelta(days=since.weekday()))
    weeks_list = []
    week = first
    while week <= now.date():
        weeks_list.append(week.isoformat())
        week += timedelta(days=7)
    result = {week: {"Issues opened": 0, "Issues closed": 0,
                     "PRs opened": 0, "PRs merged": 0} for week in weeks_list}

    def mark(value, metric):
        stamp = utc(value)
        if stamp and since <= stamp <= now:
            key = (stamp.date() - timedelta(days=stamp.weekday())).isoformat()
            if key in result:
                result[key][metric] += 1

    for report in reports:
        for issue in report.get("issue_rows", []):
            mark(issue.get("created_at"), "Issues opened")
            mark(issue.get("closed_at"), "Issues closed")
        for pr in report.get("pr_rows", []):
            mark(pr.get("created_at"), "PRs opened")
            mark(pr.get("merged_at"), "PRs merged")

    return [{"Week": week, **result[week]} for week in weeks_list]
