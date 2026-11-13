"""Plain-language decision brief assembled only from observed source data.

Not a delivery score, employee ranking, SLA signal, or prediction.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.analytics.activity import sample_activity
from src.analytics.findings import portfolio_findings
from src.ui.observed import analysis_window_coverage


TITLES = {
    "ci": "Automated checks worth inspecting",
    "issue-aging": "Older open tasks worth reviewing",
    "closure-change": "Recorded closures changed across periods",
    "merge-duration": "Merged changes have measurable turnaround time",
}


def executive_brief(reports: list[dict], *, findings=None, now=None) -> dict:
    """One readable signal, one inspectable record, and source confidence.

    An empty or incomplete source must never turn into a fabricated zero
    or a confirmed project problem.
    """
    now = now or datetime.now(timezone.utc)
    n = len(reports)
    if not n:
        return {"repositories": 0, "activity": None, "coverage_28d": None,
                "finding": None, "next_check": None, "source_url": None,
                "source_label": None, "type": None}
    activity = sample_activity(reports, now=now, days=7)
    coverage = analysis_window_coverage(reports, days=28, now=now)
    candidates = list(findings if findings is not None else
                      portfolio_findings(reports, max_findings=3))
    item = candidates[0] if candidates else None
    example = (item.get("examples") or [None])[0] if item else None
    return {
        "repositories": n,
        "activity": {
            "recent_pushes": activity["pushed_recently"],
            "opened_issues": activity["new_issues"],
            "closed_issues": activity["closed_issues"],
            "opened_prs": activity["new_prs"],
            "merged_prs": activity["merged_prs"],
            "scope": "retrieved source records · 7 days",
        },
        "coverage_28d": coverage,
        "finding": {
            "title": TITLES.get(item["type"], "A source-backed review opportunity"),
            "metric_label": item.get("metric_label", "Observed evidence"),
            "metric_value": item.get("metric_value") or "See evidence",
            "scope": item["scope"],
            "priority": item.get("review_priority", "Explore context"),
        } if item else None,
        "next_check": item.get("review") if item else None,
        "why_review": (item.get("review_plan") or {}).get("trigger") if item else None,
        "review_steps": (item.get("review_plan") or {}).get("steps") if item else None,
        "not_proven": (item.get("review_plan") or {}).get("not_proven") if item else None,
        "source_url": (example or {}).get("url") if example else (
            item.get("url") if item else None),
        "source_label": (example or {}).get("label", "Inspect GitHub evidence"),
        "type": item["type"] if item else None,
    }
