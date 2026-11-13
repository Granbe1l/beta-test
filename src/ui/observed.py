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



def qualified_reports(reports: list[dict], source: str, days: int = 28, now=None) -> list[dict]:
    """Reports with a current, complete source scan covering the full window.

    Source-specific membership prevents Issue readiness being treated as
    evidence of PR or workflow readiness. A short adaptive fallback (1/7
    days) cannot qualify for a 28-day chart. Never infer missing events.
    """
    if source not in {entry[0] for entry in SOURCES}:
        raise ValueError(f"Unsupported source: {source}")
    if days < 1:
        raise ValueError("days must be positive")
    threshold = utc(now or datetime.now(timezone.utc)) - timedelta(days=days)
    selected = []
    for r in reports:
        if r.get("status", {}).get(source) != "complete":
            continue
        checkpoint = (r.get("coverage") or {}).get(source) or {}
        coverage_start = utc(checkpoint.get("coverage_start"))
        if coverage_start is not None and coverage_start <= threshold:
            selected.append(r)
    return selected


def analysis_window_coverage(reports: list[dict], days: int = 28, now=None) -> dict[str, int]:
    """Verified completed scans covering the WHOLE requested recent time window.

    A completed 1- or 7-day adaptive scan does not qualify for a 28-day
    trend, even when its checkpoint status is 'complete'.
    """
    now = utc(now or datetime.now(timezone.utc))
    threshold = now - timedelta(days=days)
    counts = {}
    for source, _, _ in SOURCES:
        count = 0
        for r in reports:
            if r.get("status", {}).get(source) != "complete":
                continue
            cp = (r.get("coverage") or {}).get(source) or {}
            since = utc(cp.get("coverage_start"))
            if since is not None and since <= threshold:
                count += 1
        counts[source] = count
    return counts



def verified_joint_cohort(reports: list[dict], days: int = 7, now=None) -> list[dict]:
    """Exactly the same repositories with all three sources verified.

    An individual source's verified subset can be larger. Requiring an
    intersection avoids claiming comparable cross-source activity from
    repositories whose CI, Issue, or PR history is missing.
    """
    if days < 1:
        raise ValueError("days must be positive")
    qualifying_ids = [
        {id(report) for report in qualified_reports(reports, source, days, now)}
        for source, _, _ in SOURCES
    ]
    common = set.intersection(*qualifying_ids) if qualifying_ids else set()
    return [report for report in reports if id(report) in common]


def evidence_readiness(reports: list[dict], now=None) -> dict:
    """Source denominators and strict matched cohorts for CV-safe summaries.

    Does not replace source-specific analysis. The tracked 75 remain
    tracked even when a verified subset is smaller.
    """
    return {
        "tracked": len(reports),
        "verified_7d": analysis_window_coverage(reports, days=7, now=now),
        "verified_28d": analysis_window_coverage(reports, days=28, now=now),
        "joint_verified_7d": len(verified_joint_cohort(reports, 7, now)),
        "joint_verified_28d": len(verified_joint_cohort(reports, 28, now)),
        "full_open_backlog": sum(
            r.get("open_backlog_status") == "complete" for r in reports
        ),
        "scope_notice": (
            "Only the verified cohort qualifies for cross-source trend "
            "analysis. Incomplete source data are available for clearly "
            "labelled exploratory inspection, not a claim of zero activity."
        ),
    }



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
