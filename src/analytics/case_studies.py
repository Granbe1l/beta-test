"""Three auditable public engineering *review cases*, not business outcome claims.

The case studies derive exclusively from the curated, jointly Verified 28-day
GitHub snapshot. Every selected individual link must match an actual stored
record. If a category is unavailable, it is omitted rather than fabricated.
"""
from __future__ import annotations

from src.analytics.findings import findings_for_repo
from src.ui.observed import verified_joint_cohort

_CASES = {
    "issue-aging": (
        "Older open work",
        "Confirm the oldest open Issue still needs action: inspect its labels, "
        "discussion and current relevance.",
        "Only if maintainers' public discussion confirms action is needed, "
        "document a follow-up for that Issue; otherwise record no confirmed delay.",
    ),
    "ci": (
        "Automated check results",
        "Open the failed Actions run, inspect its workflow, branch, logs, "
        "and nearby reruns before considering a follow-up.",
        "Only if the logs establish a repeatable failing check, document "
        "its workflow and GitHub link; do not infer a failed release.",
    ),
    "merge-duration": (
        "Time to merge code changes",
        "Inspect the selected merged PR's scope, creation/merge times "
        "and review discussion.",
        "Describe an observed bottleneck only if the actual PR discussion "
        "supports it; otherwise report descriptive merge time only.",
    ),
}
_SOURCE = {"issue-aging": "issue_rows", "ci": "ci_rows", "merge-duration": "pr_rows"}


def build_case_studies(reports: list[dict], *, limit: int = 3) -> list[dict]:
    """Return up to three source-proven, type-diverse walk-throughs.

    Only cases backed by an original stored record are shown. No business
    impact, maintainer decision, customer outcome or confirmed defect is inferred.
    """
    if limit < 1:
        return []
    eligible = verified_joint_cohort(reports, days=28)
    by_name = {r["repository"]["full_name"]: r for r in eligible}
    # Collect ALL qualifying candidate findings, not just the single
    # portfolio-leading finding of each type; otherwise several examples
    # might point to one large repo despite alternatives in the dataset.
    pool = [f for r in eligible for f in findings_for_repo(r)
            if f.get("type") in _CASES]
    priority = {"Review first": 0, "Review next": 1, "Explore context": 2}
    pool.sort(key=lambda f: (
        priority.get(f.get("review_priority"), 3), f.get("scope", "")))
    cases = []
    used_repos = set()
    for kind, (title, next_check, conditional_decision) in _CASES.items():
        candidates = [f for f in pool if f["type"] == kind]
        for finding in candidates:
            name = finding["scope"]
            source = by_name.get(name)
            if source is None or name in used_repos:
                continue
            # An aged Issue share is meaningful only with a verified
            # independent complete current open-Issue inventory.
            if kind == "issue-aging" and source.get("open_backlog_status") != "complete":
                continue
            examples = finding.get("examples") or []
            if not examples:
                continue
            original = examples[0]
            link = original["url"]
            if not any(row.get("url") == link
                       for row in source.get(_SOURCE[kind]) or []):
                continue
            plan = finding.get("review_plan") or {}
            cases.append({
            "kind": kind,
            "title": title,
            "repository": name,
            "record_title": original["label"],
            "record_url": link,
            "record_reason": original["reason"],
            "metric_label": finding["metric_label"],
            "metric_value": finding["metric_value"],
            "metric_context": finding["metric_context"],
            "evidence_scope": finding["evidence_scope"],
            "trigger": plan.get("trigger") or "Source-backed review threshold",
            "next_check": next_check,
            "conditional_decision": conditional_decision,
            "not_proven": plan.get("not_proven") or "An observation is not a delivery verdict.",
            "status": "Review example — not a confirmed issue or action taken",
            })
            used_repos.add(name)
            break
        if len(cases) >= limit:
            break
    return cases
