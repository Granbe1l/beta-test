"""Actionable, source-specific coverage gaps from an ACTUAL GitHub audit.

Reports gaps and paging reasons. No extrapolation or fictional completeness.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCES = ("issues", "pull_requests", "workflow_runs")


def _dt(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def coverage_gaps(audit: dict, *, now=None, limit=12) -> dict:
    now = _dt(now) if isinstance(now, str) else (now or datetime.now(timezone.utc))
    now = _dt(now.isoformat())
    cutoff = now - timedelta(days=28)
    entries = []
    for row in audit.get("repositories") or []:
        repo = row.get("name")
        if not repo:
            continue
        details = row.get("source_details") or {}
        for source in SOURCES:
            status = (row.get("status") or {}).get(source, "unavailable")
            info = details.get(source) or {}
            started = _dt(info.get("coverage_start"))
            if status == "complete" and started is not None and started <= cutoff:
                continue
            if status in {"failed", "unavailable"}:
                reason, urgency = "unavailable_or_failed", 0
            elif status == "partial":
                reason, urgency = "api_page_cap_or_partial", 1
            elif status == "stale":
                reason, urgency = "stale_checkpoint", 2
            elif status == "complete":
                reason, urgency = "complete_short_fallback_only", 3
            else:
                reason, urgency = "unknown_source_state", 4
            entries.append({
                "repository": repo, "source": source,
                "status": status, "reason": reason,
                "coverage_start": started.isoformat() if started else None,
                "fetched_pages": info.get("pages_fetched"),
                "last_error": info.get("last_error"),
                "_urgency": urgency,
            })
    entries.sort(key=lambda e: (e["_urgency"], e["repository"], e["source"]))
    for entry in entries:
        entry.pop("_urgency")
    summary = audit.get("coverage_summary") or {}
    return {
        "repository_count": len(audit.get("repositories") or []),
        "actual_verified_28d": {
            source: (summary.get(source) or {}).get("verified_28d")
            for source in SOURCES
        },
        "gap_count": len(entries),
        "top_gaps": entries[:max(0, limit)],
        "note": (
            "A bounded endpoint scan may be complete for a short fallback "
            "while missing the full last 28 days. The independent open "
            "backlog scan is not a replacement for 28-day source coverage."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: coverage_triage.py SNAPSHOT-AUDIT.json")
    audit = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    report = coverage_gaps(audit)
    print("SOURCE COVERAGE TRIAGE:", json.dumps(report, sort_keys=True))
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as file:
            file.write("\n### Highest-priority uncovered source windows\n\n")
            file.write(f"Total source gaps: **{report['gap_count']}**. "
                       "No count is inferred from missing records.\n\n")
            file.write("| Repository | Source | Gap reason | Pages in last attempt |\n")
            file.write("|:--|:--|:--|--:|\n")
            for item in report["top_gaps"]:
                file.write(f"| `{item['repository']}` | {item['source']} | "
                           f"{item['reason']} | {item['fetched_pages'] or '—'} |\n")
            file.write("\n")


if __name__ == "__main__":
    main()
