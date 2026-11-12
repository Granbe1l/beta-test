"""Evidence gate: do not publish a supposedly fresh snapshot without new data.

Batches may not improve ALL source-completeness ratios in one run. A healthy
refresh must, however, move at least one successful checkpoint forward or
persist newly observed GitHub records. A zero-work or regressed dataset
fails the workflow, leaving the previous main-branch snapshot unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys

SOURCES = ("issues", "pull_requests", "workflow_runs")


def timestamp(value):
    if not value:
        return None
    if isinstance(value, datetime):
        x = value
    else:
        x = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x.astimezone(timezone.utc)


def verify_progress(before: dict, after: dict, expected_repositories=75) -> dict:
    rows = after.get("repositories") or []
    if len(rows) != expected_repositories:
        raise ValueError(
            f"Expected {expected_repositories} selected repositories; got {len(rows)}")
    repo_ids = [r["name"] for r in rows]
    if len(set(repo_ids)) != len(repo_ids):
        raise ValueError("Duplicate repository entries in snapshot audit")

    counts_before = before.get("counts") or {}
    counts_after = after.get("counts") or {}
    delta = {}
    for source in SOURCES:
        newer = int(counts_after[source])
        older = int(counts_before.get(source, 0))
        if newer < older:
            raise ValueError(
                f"{source} record count regressed: {older} -> {newer}")
        delta[source] = newer - older

        coverage = (after.get("coverage_summary") or {}).get(source) or {}
        states = sum(int(coverage.get(label, 0)) for label in
                     ("complete", "partial", "stale", "failed", "unavailable"))
        if int(coverage.get("total_repositories", -1)) != expected_repositories:
            raise ValueError(f"{source}: invalid coverage denominator")
        if states != expected_repositories:
            raise ValueError(
                f"{source}: coverage statuses sum to {states}, expected {expected_repositories}")
        verified = int(coverage.get("verified_28d", -1))
        if verified < 0 or verified > int(coverage.get("complete", 0)):
            raise ValueError(f"{source}: inconsistent verified 28-day count")

    original = {row["name"]: row for row in before.get("repositories") or []}
    progressed = {source: 0 for source in SOURCES}
    for row in rows:
        previous = original.get(row["name"]) or {}
        before_times = previous.get("last_success_at") or {}
        after_times = row.get("last_success_at") or {}
        for source in SOURCES:
            earlier = timestamp(before_times.get(source))
            later = timestamp(after_times.get(source))
            if later and (earlier is None or later > earlier):
                progressed[source] += 1

    if not sum(progressed.values()) and not sum(delta.values()):
        raise RuntimeError(
            "Ingestion made no verified checkpoint progress and stored no new "
            "records; retaining the previous published snapshot")

    return {"repositories": len(rows),
            "fresh_successful_scans": progressed,
            "new_records": delta,
            "newly_verified_28d": {
                source: int(after["coverage_summary"][source]["verified_28d"])
                      - int((before.get("coverage_summary") or {})
                            .get(source, {}).get("verified_28d", 0))
                for source in SOURCES}}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: verify_collection.py BEFORE.json AFTER.json")
    before = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    after = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    result = verify_progress(before, after)
    print("COLLECTION VALIDATION:", json.dumps(result, sort_keys=True), flush=True)
    summary_path = __import__("os").environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n### Verified collection progress\n\n")
            f.write("| Source | Freshly successful scans | New records | 28d coverage change |\n")
            f.write("|:--|--:|--:|--:|\n")
            for source in SOURCES:
                f.write(f"| {source} | {result['fresh_successful_scans'][source]} | "
                        f"{result['new_records'][source]:+,} | "
                        f"{result['newly_verified_28d'][source]:+d} |\n")


if __name__ == "__main__":
    main()
