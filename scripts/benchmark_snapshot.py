"""Measure real current-snapshot load and core analytic calculation cost.

This is a server-side performance smoke test, not an invented end-user load
time or Lighthouse score. CI prints results and GitHub job summary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
import json
import os
import resource
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.snapshot import SNAPSHOT_PATH, read_snapshot
from src.ui.observed import summary, analysis_window_coverage
from src.analytics.trends import daily_event_series
from src.analytics.findings import portfolio_findings


def benchmark():
    start = perf_counter()
    reports, selection, meta = read_snapshot(SNAPSHOT_PATH)
    load_seconds = perf_counter() - start
    start = perf_counter()
    totals = summary(reports)
    eligible = analysis_window_coverage(reports, 28)
    daily = daily_event_series(reports, days=28)
    findings = portfolio_findings([r for r in reports if r["coverage_ok"]])
    analytics_seconds = perf_counter() - start
    # The pre-transition 75-repo snapshot is accepted only during this PR.
    # Once a curated_50 selection is published, 50 is mandatory.
    from src.config.settings import Settings
    expected = Settings.from_env().max_repos
    legacy = (len(reports) == 75 and expected == 50 and
              (selection or {}).get("parameters", {}).get("purpose") != "curated_verified_50")
    if (len(reports) != expected and not legacy) or len(daily) != 28:
        raise ValueError(f"Benchmark expects {expected} curated repositories and 28 daily rows")
    # Linux GitHub Actions resource maxrss uses KiB. The metric is process
    # maximum RSS, not a measurement of total Streamlit browser memory.
    rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    return {
        "snapshot_created_utc": meta["generated_at"].isoformat(),
        "repos": len(reports),
        "stored_issue_rows": len(totals["issue_rows"]),
        "stored_pr_rows": len(totals["pr_rows"]),
        "stored_ci_rows": len(totals["ci_rows"]),
        "eligible_28_days": eligible,
        "snapshot_load_seconds": round(load_seconds, 3),
        "analysis_seconds": round(analytics_seconds, 3),
        "peak_process_rss_mb": rss_mb,
        "evidence_findings": len(findings),
    }


if __name__ == "__main__":
    data = benchmark()
    print("SNAPSHOT PERFORMANCE:", json.dumps(data, sort_keys=True), flush=True)
    output = os.environ.get("GITHUB_STEP_SUMMARY")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write("\n### Real snapshot performance (runner only)\n\n")
            for key, value in data.items():
                f.write(f"- {key}: **{value}**\n")
