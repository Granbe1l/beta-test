"""Evidence-grounded, non-prescriptive review decisions for public GitHub activity.

Review thresholds are _inspection triggers_, never software-quality, delivery,
SLA or developer scores. Every suggested check has an actual original GitHub
URL or explicitly discloses that only a repository landing page is available.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.analytics.metrics import utc

TRIGGERS = {
    "issue-aging": (
        "At least 5 currently observed open Issues and 40% aged 30+ days; "
        "a large age share can merit review, but age is not a due date."
    ),
    "ci": (
        "At least 10 completed checks with known outcomes and fewer than "
        "80% successes in the verified observation period; not a service SLA."
    ),
    "merge-duration": (
        "At least 5 merged code changes with a verified observation window; "
        "a merge-time median is descriptive, not a performance target."
    ),
    "closure-change": (
        "At least 5 closures in the earlier 28-day window and an absolute "
        "change of at least 20% across verified adjacent periods."
    ),
}
RISKS = {
    "issue-aging": (
        "Older open Issues may be planned work, duplicates, or unprioritized "
        "reports. Age alone cannot establish that a project is late."
    ),
    "ci": (
        "A failed automated check does not prove the software release "
        "failed, and repeated workflow runs are not independent defects."
    ),
    "merge-duration": (
        "Different PR complexity, size, author schedules and reviews are "
        "unmeasured here; do not attribute merge time to team productivity."
    ),
    "closure-change": (
        "Recorded Issue closures cannot establish throughput, a release "
        "deadline, or customer outcomes without external context."
    ),
}


def review_decision(finding: dict) -> dict:
    """Build a repeatable evidence -> check -> decision workflow.

    Steps are actionable because a real record, period, observation and
    qualification are all surfaced. Never fabricate ownership or impact.
    """
    kind = finding.get("type")
    examples = finding.get("examples") or []
    source = (examples[0].get("url") if examples else finding.get("url"))
    label = (examples[0].get("label") if examples
             else "Repository source listing; no individual example available")
    trigger = TRIGGERS.get(kind, "Evidence-backed inspection suggested.")
    limitation = RISKS.get(
        kind, "This source observation alone does not establish a defect.")
    check = {
        "issue-aging": (
            "Read the oldest retrieved open Issue: check its status, labels, "
            "maintainer discussion, and whether work is still expected."
        ),
        "ci": (
            "Open the recorded failed workflow run; inspect the workflow "
            "name, branch, logs and nearby reruns for the same failure."
        ),
        "merge-duration": (
            "Review the longest observed merged PR and its creation/merge "
            "times, change scope and review discussion."
        ),
        "closure-change": (
            "Open a retrieved closed Issue from the two compared periods; "
            "verify its actual closed date and why it was closed."
        ),
    }.get(kind, "Open the supporting GitHub record and confirm its context.")
    next_step = {
        "issue-aging": (
            "If the Issue still requires work, note a follow-up for its "
            "maintainers. Otherwise record that age alone is not actionable."
        ),
        "ci": (
            "If the failure is reproducible on the same workflow, record "
            "the affected check and source link; otherwise do not flag a "
            "confirmed build problem."
        ),
        "merge-duration": (
            "If review discussion explains timing, describe that context. "
            "Otherwise keep the result as a descriptive duration only."
        ),
        "closure-change": (
            "If closure reasons differ between periods, note the distinction. "
            "Otherwise report only the observed two-window counts."
        ),
    }.get(kind, "Document what is confirmed and what remains unknown.")
    return {
        "trigger": trigger,
        "steps": [
            "1. Check the measured scope: " +
            finding.get("metric_context", finding.get("evidence", "")) +
            ". " + finding.get("evidence_scope", "Observed source records") + ".",
            "2. Inspect GitHub evidence: " + label + ". " + check,
            "3. Record a bounded decision: " + next_step,
        ],
        "first_record_url": source,
        "first_record_label": label,
        "example_available": bool(examples),
        "not_proven": limitation,
    }


def evidence_action(finding: dict) -> dict:
    """Choose the actionable source link without overstating its specificity.

    Original GitHub records are preferred when the retrieved snapshot actually
    contains an eligible example. Otherwise the repository source listing is
    an honest discovery starting point, not a record-level verification.
    """
    plan = finding.get("review_plan") or review_decision(finding)
    url = plan.get("first_record_url") or finding.get("url")
    if not url:
        return {
            "url": None, "button": None,
            "disclosure": "No source URL is available for this finding.",
            "record_level": False,
        }
    record_level = bool(plan.get("example_available"))
    return {
        "url": url,
        "button": ("Open example GitHub record" if record_level
                   else "Open GitHub source listing"),
        "disclosure": (
            "Example from retrieved data; inspect the record before drawing a conclusion."
            if record_level else
            "No matching individual record example in the snapshot; "
            "this listing is only a starting point."
        ),
        "record_level": record_level,
    }


def _safe_csv_cell(value) -> str:
    """Keep untrusted GitHub names and titles from becoming CSV formulas."""
    text = str(value if value is not None else "")
    stripped = text.lstrip()
    if stripped.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def review_csv(findings: list[dict]) -> bytes:
    """UTF-8 CSV of exactly the displayed evidence-linked inspection queue."""
    import csv
    import io
    output = io.StringIO(newline="")
    fieldnames = [
        "Repository", "Review priority", "Finding", "Measured value",
        "Observed denominator", "Verification scope", "Reason to inspect",
        "GitHub link (record or listing)", "Record-level example available",
        "Review step 1", "Review step 2",
        "Review step 3", "What cannot be concluded",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in findings:
        plan = item.get("review_plan") or review_decision(item)
        values = [
            item.get("scope"), item.get("review_priority"), item.get("headline"),
            item.get("metric_value"), item.get("metric_context"),
            item.get("evidence_scope"), plan["trigger"],
            plan.get("first_record_url") or item.get("url"),
            "yes" if plan.get("example_available") else "no",
            *plan["steps"], plan["not_proven"],
        ]
        writer.writerow(dict(zip(fieldnames, map(_safe_csv_cell, values))))
    return output.getvalue().encode("utf-8-sig")
