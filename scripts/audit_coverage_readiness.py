"""Strict, timestamp-aware completeness accounting for the full 75-repo cohort.

The collector's raw status 'complete' can mean only a narrow adaptive 1/7d
window. Furthermore a 28d-verified source can become stale after 12 hours.
This report must use the SAME exact freshness and window checks as the
Streamlit Verified 28-day filter. Never reclassify missing data as zero.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

SOURCES = ("issues", "pull_requests", "workflow_runs")


def parsed(value):
    if not value:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def strict_readiness(audit: dict, *, now=None, days=28, stale_hours=12):
    now = parsed(now) or datetime.now(timezone.utc)
    begin = now - timedelta(days=days)
    fresh = now - timedelta(hours=stale_hours)
    all_rows = []
    counts = Counter()
    for row in audit.get("repositories") or []:
        name = row.get("name")
        if not name:
            continue
        blockers = []
        for source in SOURCES:
            status = (row.get("status") or {}).get(source, "unavailable")
            checkpoint = (row.get("source_details") or {}).get(source) or {}
            since = parsed(checkpoint.get("coverage_start"))
            success = parsed(checkpoint.get("last_success_at"))
            if status == "complete" and since and since <= begin and success and success >= fresh:
                counts[(source, "verified_28d")] += 1
                continue
            if status in ("failed", "unavailable"):
                reason, action = "unavailable_or_failed", "Inspect actual API/permission/error first"
            elif status == "partial":
                reason = "api_page_cap_or_partial"
                action = ("Resume capped CI calendar/UTC-hour shards" if source == "workflow_runs"
                          else "Revisit paged Issue/PR event history without asserting full history")
            elif not success or success < fresh:
                reason, action = "stale_checkpoint", "Refresh original source scan before claiming current coverage"
            elif not since or since > begin:
                reason, action = "complete_short_window_only", "Attempt fully bounded 28d history, preserve partial source state"
            else:
                reason, action = "unknown_source_state", "Inspect checkpoint provenance"
            counts[(source, reason)] += 1
            blockers.append({
                "source": source,
                "reason": reason,
                "source_status": status,
                "last_success_at": success.isoformat() if success else None,
                "coverage_start": since.isoformat() if since else None,
                "source_pages_last_attempt": checkpoint.get("pages_fetched"),
                "last_error": checkpoint.get("last_error"),
                "next_action": action,
            })
        all_rows.append({"repository": name, "verified_joint_28d": not blockers,
                         "unverified_sources": blockers})
    return {
        "as_of_utc": now.isoformat(),
        "tracked": len(all_rows),
        "verified_joint_28d": sum(x["verified_joint_28d"] for x in all_rows),
        "not_joint_verified": sum(not x["verified_joint_28d"] for x in all_rows),
        "source_verified_28d": {k: counts[(k, "verified_28d")] for k in SOURCES},
        "source_gaps_by_reason": {
            source: {
                reason: value for (k, reason), value in sorted(counts.items())
                if k == source and reason != "verified_28d"
            } for source in SOURCES
        },
        "window_days": days,
        "stale_hours": stale_hours,
        "per_repository": all_rows,
        "provenance": "Actual collector checkpoint status+coverage_start+last_success_at, not guessed health",
        "caveat": "Independent full-open Issue inventory is separate; source completeness never proves quality, productivity or deadlines.",
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: audit_coverage_readiness.py snapshot-audit.json")
    source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = strict_readiness(source)
    target = Path("coverage-readiness.json")
    target.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print("STRICT VERIFIED COHORT:", json.dumps({
        key: value for key, value in output.items() if key != "per_repository"
    }, sort_keys=True), flush=True)
    step = os.environ.get("GITHUB_STEP_SUMMARY")
    if step:
        with open(step, "a", encoding="utf-8") as f:
            f.write("\n### Actual source-specific Verified 28-day audit\n\n")
            f.write(f"**{output['verified_joint_28d']}/{output['tracked']}** "
                    "repositories qualify for all three 28-day source windows "
                    f"within {output['stale_hours']}h freshness.\n\n")
            f.write("| Source | Verified 28d | Missing/partial/stale |\n")
            f.write("|---|---:|---:|\n")
            for name in SOURCES:
                total = output["source_verified_28d"][name]
                f.write(f"| {name} | {total} | {output['tracked']-total} |\n")
            f.write("\nDetailed per-repository blockers and next checks are in "
                    "the **coverage-readiness.json** artifact; a no-activity "
                    "repo is not declared inactive.\n")


if __name__ == "__main__":
    main()
