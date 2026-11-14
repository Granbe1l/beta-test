"""Evidence-first, purely derived summaries for sampled public GitHub inspections.

These functions never infer health, deadlines, 28-day coverage or complete
backlog sizes from a single page of recent public API records.
"""
from __future__ import annotations

from collections import Counter

FAILURES = frozenset({"failure", "timed_out", "startup_failure", "action_required"})
CI_ORDER = ("Succeeded", "Failed / timed out", "Cancelled", "Skipped / neutral",
            "Pending", "Other")
PR_ORDER = ("Open", "Draft", "Merged", "Closed without merge")


def ci_breakdown(data: dict) -> list[dict]:
    if data.get("ci_error"):
        return []
    outcomes = Counter()
    for item in data.get("sample_runs") or []:
        status = item.get("status")
        conclusion = item.get("conclusion")
        if status != "completed":
            label = "Pending"
        elif conclusion == "success":
            label = "Succeeded"
        elif conclusion in FAILURES:
            label = "Failed / timed out"
        elif conclusion == "cancelled":
            label = "Cancelled"
        elif conclusion in {"skipped", "neutral"}:
            label = "Skipped / neutral"
        else:
            label = "Other"
        outcomes[label] += 1
    return [{"label": label, "count": outcomes[label]} for label in CI_ORDER
            if outcomes[label]]


def pr_breakdown(data: dict) -> list[dict]:
    if data.get("prs_error"):
        return []
    outcomes = Counter()
    for item in data.get("sample_prs") or []:
        if item.get("merged_at"):
            label = "Merged"
        elif item.get("state") == "open":
            label = "Draft" if item.get("draft") else "Open"
        else:
            label = "Closed without merge"
        outcomes[label] += 1
    return [{"label": label, "count": outcomes[label]} for label in PR_ORDER
            if outcomes[label]]


def preview_review_plan(data: dict) -> list[dict]:
    """Rank *inspection steps*, not project/developer performance risks."""
    checks = []
    for source, key in (
        ("Issues", "issues_error"),
        ("Pull requests", "prs_error"),
        ("CI/CD", "ci_error"),
    ):
        if data.get(key):
            checks.append({
                "order": 0, "tag": "Evidence gap",
                "title": "Check unavailable " + source + " data",
                "explanation": (
                    source + " API observations are unavailable (" +
                    str(data[key]) + "). Do not interpret missing records as "
                    "zero activity; retry when the API permits."),
                "url": None,
            })
    if not data.get("ci_error") and data.get("sample_ci_failed", 0):
        completed = data.get("sample_ci_completed", 0)
        failed = data["sample_ci_failed"]
        checks.append({
            "order": 1, "tag": "Review next",
            "title": "Inspect unsuccessful automated checks",
            "explanation": (
                f"{failed} of {completed} observed completed CI runs with known "
                "outcomes failed or timed out. Read the most recent run logs "
                "and determine whether any failure is still relevant."),
            "url": data.get("last_failed_run_url"),
        })
    if not data.get("issues_error") and data.get("sample_old_issues", 0):
        old = data["sample_old_issues"]
        checks.append({
            "order": 2, "tag": "Follow up",
            "title": "Review older open Issues",
            "explanation": (
                f"{old} open Issues in the recently updated sample were created "
                "at least 30 days ago. Check their current relevance and "
                "owners; age alone cannot prove a missed deadline."),
            "url": data.get("old_issue_url"),
        })
    if not checks:
        checks.append({
            "order": 3, "tag": "No sample signal",
            "title": "Check activity and source completeness",
            "explanation": (
                "No review trigger met these limited sample rules. This "
                "does not prove that the repository has no delivery issues."),
            "url": None,
        })
    checks.sort(key=lambda row: (row["order"], row["title"]))
    return checks[:4]


def inspection_summary(data: dict) -> dict:
    """Ground all UI numerators and denominators in exactly fetched records."""
    ci = ci_breakdown(data)
    prs = pr_breakdown(data)
    source_gaps = sum(bool(data.get(key)) for key in
                      ("issues_error", "prs_error", "ci_error"))
    return {
        "ci": ci,
        "prs": prs,
        "ci_observed": len(data.get("sample_runs") or []),
        "pr_observed": len(data.get("sample_prs") or []),
        "issue_observed": len(data.get("sample_issues") or []),
        "source_gaps": source_gaps,
        "review_plan": preview_review_plan(data),
        "external": True,
        "verified_28d": False,
        "limitations": (
            "One bounded, newest-first API page per source; the sample is "
            "not a full 28-day history, the entire open backlog, or a "
            "project-health or employee-performance assessment."
        ),
    }
