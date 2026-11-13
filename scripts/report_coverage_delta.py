"""Summarize actual GitHub snapshot coverage changes in GitHub Actions.

Never represent a successful workflow as fully Verified complete sources. Write a
non-sensitive Markdown report showing counts AND verified 28-day coverage.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SOURCES = (
    ("issues", "Issues"),
    ("pull_requests", "Pull requests"),
    ("workflow_runs", "CI/CD checks"),
)
STATUSES = ("complete", "partial", "stale", "failed", "unavailable")


def delta_report(before: dict, after: dict) -> str:
    old = before.get("coverage_summary") or {}
    new = after.get("coverage_summary") or {}
    if not new or any(source not in new for source, _ in SOURCES):
        raise ValueError("Coverage report is missing required source summaries")
    lines = [
        "## Public GitHub snapshot · collection progress",
        "",
        "These are bounded GitHub API scans, **not full repository histories**.",
        "A completed short fallback does not establish verified 28-day coverage.",
        "",
        "| Source | Complete scans | Partial | Stale | Unavailable | Verified 28d |",
        "|:--|--:|--:|--:|--:|--:|",
    ]
    for source, label in SOURCES:
        now = new[source]
        prev = old.get(source) or {}
        total = int(now.get("total_repositories", 0))
        def cell(field):
            value = int(now.get(field, 0))
            prior = int(prev.get(field, 0))
            change = value - prior
            return f"{value}/{total} ({change:+d})" if field in ("complete", "verified_28d") else str(value)
        lines.append(
            f"| {label} | {cell('complete')} | {cell('partial')} | "
            f"{cell('stale')} | {cell('unavailable')} | {cell('verified_28d')} |"
        )
    if "open_backlog" in new:
        current = new["open_backlog"]
        previous = old.get("open_backlog") or {}
        complete = int(current.get("complete", 0))
        prior = int(previous.get("complete", 0))
        total = int(current.get("total_repositories", 0))
        lines += [
            "",
            "### Independent current-open-Issue inventory",
            "",
            f"Fully exhausted open-Issue lists: **{complete}/{total}** "
            f"({complete-prior:+d} since the previous audit). "
            "An incomplete list is a sampled backlog, not zero issues. "
            "This is **not** a 28-day source-event verification.",
        ]
    counts = after.get("counts") or {}
    previous = before.get("counts") or {}
    lines += ["", "### Persisted records", ""]
    for source, label in SOURCES:
        value = int(counts.get(source, 0))
        change = value - int(previous.get(source, 0))
        lines.append(f"- {label}: **{value:,}** records ({change:+,} since previous snapshot)")
    if all(int(new[src].get("verified_28d", 0)) == 0 for src, _ in SOURCES):
        lines += ["", "> No source is yet verified for a full 28-day window. "
                  "The dashboard must label multiweek charts exploratory."]
    lines += ["", "Current curated sample: 50 selected public repositories. "
                  "An unvisited or stale source is **not** proof of inactivity.",
              ""]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: report_coverage_delta.py BEFORE.json AFTER.json")
    before = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    after = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    output = delta_report(before, after)
    print(output, flush=True)
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(output + "\n")


if __name__ == "__main__":
    main()
