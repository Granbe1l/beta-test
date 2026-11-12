"""Consistent, descriptive view metrics from retrieved GitHub rows.

These are observed sample counts, not estimates of complete GitHub activity.
The same row selection is used for KPI totals and chart distributions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from src.analytics.metrics import utc


SOURCES = (
    ("issues", "issues", "issue_rows"),
    ("pull_requests", "pull_requests", "pr_rows"),
    ("workflow_runs", "workflow_runs", "ci_rows"),
)


def coverage_counts(reports: list[dict]) -> dict[str, int]:
    """Number of repositories whose selected API source is verified complete."""
    return {source: sum(r.get("status", {}).get(source) == "complete" for r in reports)
            for source, _, _ in SOURCES}


def summary(reports: list[dict], now=None, observation_days=90) -> dict:
    """Counts of *retrieved* items, with source coverage and period attached.

    An absent source is not a confirmed zero. Counts use exactly the retrieved
    rows that power the visuals; no extrapolation from the curated sample.
    """
    now = utc(now or datetime.now(timezone.utc))
    since = now - timedelta(days=observation_days)
    issue_rows = [item for r in reports for item in r.get("issue_rows", [])]
    pr_rows = [item for r in reports for item in r.get("pr_rows", [])]
    ci_rows = [item for r in reports for item in r.get("ci_rows", [])]
    cover = coverage_counts(reports)

    def known(value: int, source: str, rows: list) -> int | None:
        return value if rows or cover[source] else None

    open_issues = sum(item.get("state") == "open" for item in issue_rows)
    aged_issues = sum(
        item.get("state") == "open" and item.get("created_at")
        and (now - utc(item["created_at"])).days >= 30
        for item in issue_rows
    )
    open_changes = sum(item.get("state") == "open" for item in pr_rows)
    draft_changes = sum(item.get("state") == "open" and item.get("draft") for item in pr_rows)
    merged = sum(
        bool(item.get("merged_at")) and since <= utc(item["merged_at"]) <= now
        for item in pr_rows
    )
    completed = [
        item for item in ci_rows
        if item.get("status") == "completed"
        and item.get("created_at") and since <= utc(item["created_at"]) <= now
    ]
    success = sum(item.get("conclusion") == "success" for item in completed)
    failures = sum(item.get("conclusion") in {"failure", "timed_out"} for item in completed)
    known_conclusion = sum(item.get("conclusion") is not None for item in completed)
    return {
        "repositories": len(reports),
        "coverage": cover,
        "open_issues": known(open_issues, "issues", issue_rows),
        "aged_issues": known(aged_issues, "issues", issue_rows),
        "aged_share": aged_issues / open_issues * 100 if open_issues else None,
        "open_changes": known(open_changes, "pull_requests", pr_rows),
        "draft_changes": known(draft_changes, "pull_requests", pr_rows),
        "merged_changes": known(merged, "pull_requests", pr_rows),
        "completed_checks": known(len(completed), "workflow_runs", ci_rows),
        "successful_checks": known(success, "workflow_runs", ci_rows),
        "failed_checks": known(failures, "workflow_runs", ci_rows),
        "check_success_share": success / known_conclusion * 100 if known_conclusion else None,
        "period_days": observation_days,
        "issue_rows": issue_rows,
        "pr_rows": pr_rows,
        "ci_rows": ci_rows,
    }
