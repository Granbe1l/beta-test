"""Audit actual open-Issue inventory gaps without changing any checkpoint.

Reads the published GitHub collector's authoritative snapshot-audit.json.
A complete 28-day event source is never a full open-Issue list.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

STATUS_ORDER = {"unavailable": 0, "failed": 1, "partial": 2, "stale": 3}


def triage_inventory(audit: dict) -> dict:
    reports = audit.get("repositories") or []
    if not isinstance(reports, list):
        raise ValueError("Expected repository audit rows")
    entries = []
    for report in reports:
        if not isinstance(report, dict) or not report.get("name"):
            raise ValueError("Invalid repository audit row")
        status = report.get("open_backlog_status") or "unavailable"
        if status == "complete":
            continue
        detail = (report.get("source_details") or {}).get("open_backlog") or {}
        if status == "stale":
            reason = "previously exhausted list is older than freshness cutoff"
        elif status == "unavailable":
            reason = "no verifiable full-open inventory checkpoint"
        elif status == "partial":
            reason = "bounded REST/Search pagination was not fully exhausted"
        elif status == "failed":
            reason = "collection failed; inspect sanitized checkpoint error"
        else:
            reason = "unknown checkpoint state; requires investigation"
        entries.append({
            "repository": report["name"],
            "inventory_status": status,
            "reason": reason,
            "last_verified_utc": detail.get("last_success_at"),
            "pages_fetched_last_attempt": detail.get("pages_fetched"),
            "records_fetched_last_attempt": detail.get("records_fetched"),
            "last_error": detail.get("last_error"),
            # This is deliberately not called Verified 28d: status alone
            # does not prove the window duration or checkpoint freshness.
            "three_source_statuses_complete": all(
                ((report.get("source_details") or {}).get(source) or {})
                .get("status") == "complete"
                for source in ("issues", "pull_requests", "workflow_runs")
            ),
        })
    entries.sort(key=lambda item: (
        STATUS_ORDER.get(item["inventory_status"], 4),
        item["repository"].casefold(),
    ))
    count = len(reports)
    complete_count = count - len(entries)
    return {
        "total_selected_repositories": count,
        "fresh_full_open_inventories": complete_count,
        "not_fresh_or_not_verified": len(entries),
        "all_full_open_inventories_current": count > 0 and not entries,
        "source": "actual collector snapshot-audit.json",
        "note": (
            "Full-open inventory requires exhausted current open-Issue pages "
            "and a fresh checkpoint. A 28-day event-history scan, repository "
            "open_issues_count, or incomplete Search response is not proof."
        ),
        "gaps": entries,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        raise SystemExit(
            "Usage: python scripts/triage_open_inventory.py snapshot-audit.json"
        )
    audit = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    report = triage_inventory(audit)
    Path("open-inventory-triage.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print("OPEN INVENTORY TRIAGE:", json.dumps(report, sort_keys=True))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write("\n### Complete open-Issue inventory · independent audit\n\n")
            handle.write(
                f"Currently verified fresh inventories: "
                f"**{report['fresh_full_open_inventories']}/"
                f"{report['total_selected_repositories']}**. "
                "Only exhausted API scans with fresh checkpoints count.\n\n"
            )
            if report["gaps"]:
                handle.write("| Repository | Status | Last verified UTC | Reason |\n")
                handle.write("|---|---|---|---|\n")
                for gap in report["gaps"]:
                    name = gap["repository"].replace("|", " / ")
                    reason = gap["reason"].replace("|", " / ")
                    handle.write(
                        f"| {name} | {gap['inventory_status']} | "
                        f"{gap['last_verified_utc'] or '—'} | {reason} |\n"
                    )
                handle.write("\n")
            else:
                handle.write(
                    "All selected inventories are fresh **at this audit time**; "
                    "future cycles must maintain the same proof.\n\n"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
