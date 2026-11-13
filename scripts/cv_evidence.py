"""A reproducible CV evidence receipt from the REAL published GitHub snapshot.

Never equate tracked repository count with fully verified period coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.metrics import utc
from src.analytics.snapshot import read_snapshot
from src.ui.observed import evidence_readiness


def cv_receipt(reports: list[dict], *, generated_at, now=None) -> dict:
    now = utc(now or datetime.now(timezone.utc))
    generated_at = utc(generated_at)
    coverage = evidence_readiness(reports, now=now)
    observations = {
        "issue_records": sum(len(r.get("issue_rows") or []) for r in reports),
        "pull_request_records": sum(len(r.get("pr_rows") or []) for r in reports),
        "workflow_run_records": sum(len(r.get("ci_rows") or []) for r in reports),
    }
    return {
        "snapshot_created_utc": generated_at.isoformat(),
        "tracked_repositories": len(reports),
        "stored_observations": observations,
        "verified_source_windows": {
            "7d": coverage["verified_7d"],
            "28d": coverage["verified_28d"],
        },
        "matching_all_three_sources": {
            "7d": coverage["joint_verified_7d"],
            "28d": coverage["joint_verified_28d"],
        },
        "independently_verified_full_open_backlogs":
            coverage["full_open_backlog"],
        "fresh_under_12h": now - generated_at <= __import__(
            "datetime").timedelta(hours=12),
        "scope": (
            "Stored records are observations in a fixed public GitHub "
            "sample, not complete project histories or client delivery "
            "deadlines. Verified cohort denominators are per-period."
        ),
        "suggested_cv_line": (
            f"Developed a Python, SQL and Streamlit engineering-activity "
            f"monitor across {len(reports)} curated public GitHub projects, "
            f"integrating GitHub REST API data, scheduled snapshot updates, "
            f"source-aware Issue/PR/CI analysis and evidence-linked reviews."
        ),
    }


def main():
    reports, _, meta = read_snapshot()
    result = cv_receipt(reports, generated_at=meta["generated_at"])
    print("CV EVIDENCE RECEIPT:", json.dumps(result, sort_keys=True))
    summary = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n### CV-safe project evidence (real stored snapshot)\n\n")
            file.write(
                f"Snapshot: `{result['snapshot_created_utc']}`. "
                f"{result['tracked_repositories']} tracked repositories. "
                "Tracked does not mean all sources are verified.\n\n"
            )
            file.write("| Source | 7d verified | 28d verified |\n|:--|--:|--:|\n")
            for source in ("issues", "pull_requests", "workflow_runs"):
                file.write(
                    f"| {source} | {result['verified_source_windows']['7d'][source]} | "
                    f"{result['verified_source_windows']['28d'][source]} |\n"
                )
            file.write(
                f"\nMatched three-source cohorts: "
                f"**{result['matching_all_three_sources']['7d']}** "
                f"(7d), **{result['matching_all_three_sources']['28d']}** (28d). "
                "Missing source windows cannot be treated as zero.\n"
            )


if __name__ == "__main__":
    main()
