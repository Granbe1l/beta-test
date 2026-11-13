"""Honest source-cohort denominators for the recruiter-facing summary."""
from __future__ import annotations

from src.ui.observed import verified_joint_cohort


def decision_brief_cohort(all_reports: list[dict], visible_reports: list[dict],
                          now=None) -> dict[str, int]:
    """Only global unfiltered tracked repositories belong in denominator."""
    return {
        "tracked": len(all_reports),
        "verified_28d": len(verified_joint_cohort(all_reports, 28, now=now)),
        "in_view": len(visible_reports),
    }
