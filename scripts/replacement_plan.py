"""Generate a NON-MUTATING replacement proposal from verified candidate evidence.

Do not delete historical repositories, rewrite the curated selection, or
impute an unverified metric. A proposed swap is not an approved promotion.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.metrics import utc
from src.analytics.snapshot import read_snapshot
from src.ui.observed import verified_joint_cohort
from scripts.audit_candidate_pool import MIN_ROWS, SOURCES


def size_tier_from_stars(stars):
    stars = int(stars or 0)
    return "small" if stars < 500 else "medium" if stars < 5000 else "large"


def proposed_swaps(reports, audit: dict, *, now=None) -> dict:
    now = utc(now or datetime.now(timezone.utc))
    created = utc(audit.get("generated_at_utc"))
    fresh = bool(created and timedelta(0) <= now-created <= timedelta(hours=12))
    verified_ids = {r["repository"]["id"] for r in
                    verified_joint_cohort(reports, days=28, now=now)}
    originals = [
        r["repository"] for r in reports
        if r["repository"]["id"] not in verified_ids
    ]
    original_ids = {r["repository"]["id"] for r in reports}
    used = set()
    proposals = []
    rejected = []
    for candidate in audit.get("results") or []:
        rid = candidate.get("github_id")
        source_records = candidate.get("sources") or {}
        eligible = (
            fresh and candidate.get("verdict") == "verified_candidate"
            and isinstance(rid, int) and rid not in original_ids
            and isinstance(candidate.get("url"), str)
            and candidate["url"].startswith("https://github.com/")
            and all(
                (source_records.get(s) or {}).get("status") == "verified_28d"
                and (source_records[s].get("records") or 0) >= MIN_ROWS[s]
                for s in SOURCES
            )
        )
        if not eligible:
            rejected.append({
                "name": candidate.get("full_name"),
                "reason": "candidate_not_currently_verified",
            })
            continue
        # Preserve category AND project-size diversity. For an unequal match,
        # a human must review selection bias rather than changing the sample.
        matches = [
            row for row in originals
            if row["id"] not in used
            and row.get("category") == candidate.get("category")
            and size_tier_from_stars(row.get("stars")) ==
                candidate.get("size_tier")
        ]
        if not matches:
            rejected.append({
                "name": candidate.get("full_name"),
                "reason": "no_matching_category_and_size",
            })
            continue
        old = sorted(matches, key=lambda row: row["full_name"])[0]
        used.add(old["id"])
        proposals.append({
            "exclude_from_future_active_cohort_only": old["full_name"],
            "retain_original_github_id": old["id"],
            "candidate_name": candidate["full_name"],
            "candidate_github_id": rid,
            "category": old.get("category"),
            "size_tier": size_tier_from_stars(old.get("stars")),
            "reason": "verified 28-day Issues/PR/CI sources; category and size matched",
            "approved": False,
        })
    return {
        "generated_at_utc": now.isoformat(),
        "candidate_evidence_generated_utc": (
            created.isoformat() if created else None),
        "candidate_evidence_fresh": fresh,
        "tracked_original_repositories_unchanged": len(reports),
        "verified_originals_28d": len(verified_ids),
        "proposed_unapproved_swaps": proposals,
        "rejected_candidates": rejected,
        "changes_applied": 0,
        "warning": (
            "The proposed swap list does not update the database, tracked "
            "sample or historic GitHub records. No candidate is promoted "
            "unless an independently reviewed selection change is explicitly "
            "approved and later validated in a new full audit."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: replacement_plan.py candidate-verified-audit.json")
    audit = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reports, _, _ = read_snapshot()
    output = proposed_swaps(reports, audit)
    path = Path("candidate-replacement-plan.json")
    path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print("REPLACEMENT PLAN:", json.dumps({
        "tracked": output["tracked_original_repositories_unchanged"],
        "verified": output["verified_originals_28d"],
        "proposals": len(output["proposed_unapproved_swaps"]),
        "rejected": len(output["rejected_candidates"]),
        "changes_applied": 0,
        "path": str(path),
    }))


if __name__ == "__main__":
    main()
