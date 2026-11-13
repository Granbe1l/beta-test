"""P0 integrity gate: real snapshot rows, Python KPIs and SQL must agree.

This is a strict cross-check of *stored observations*, not proof of complete
GitHub history. Missing pages are never estimated, and a complete 28-day
activity window does not establish a full current open-Issue backlog.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.metrics import utc
from src.ui.observed import analysis_window_coverage, verified_joint_cohort

SOURCES = ("issues", "pull_requests", "workflow_runs")
ROW_KEYS = {"issues": "issue_rows", "pull_requests": "pr_rows",
            "workflow_runs": "ci_rows"}
SQL_ROWS = {"issues": "retrieved_issue_rows",
            "pull_requests": "retrieved_pr_rows",
            "workflow_runs": "retrieved_ci_rows"}
SQL_FLAGS = {"issues": "issues_verified_28d",
             "pull_requests": "prs_verified_28d",
             "workflow_runs": "ci_verified_28d"}


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def audit_consistency(reports: list[dict], sql_rows: list[dict], *, now) -> dict:
    """Verify exact identity, source counts and eligibility, repo by repo."""
    now = utc(now)
    threshold = now - timedelta(days=28)
    by_name = {r["repository"]["full_name"]: r for r in reports}
    by_sql = {r["repository"]: r for r in sql_rows}
    _assert(len(by_name) == len(reports), "Repeated repository in snapshot")
    _assert(len(by_sql) == len(sql_rows), "Repeated repository in SQL output")
    _assert(by_name.keys() == by_sql.keys(),
            "Snapshot and selected SQL repository identity differ")

    for name, report in by_name.items():
        sql = by_sql[name]
        for source in SOURCES:
            rows = report.get(ROW_KEYS[source]) or []
            _assert(len(rows) == sql[SQL_ROWS[source]],
                    f"{name}: {source} stored record count differs from SQL")
            checkpoint = (report.get("coverage") or {}).get(source) or {}
            start = utc(checkpoint.get("coverage_start"))
            expected = bool(report.get("status", {}).get(source) == "complete"
                            and start is not None and start <= threshold)
            _assert(int(expected) == int(sql[SQL_FLAGS[source]]),
                    f"{name}: {source} 28-day coverage not consistent")
        issues = report.get("issue_rows") or []
        open_count = sum(i.get("state") == "open" for i in issues)
        old_count = sum(
            i.get("state") == "open" and i.get("created_at")
            and utc(i["created_at"]) <= now - timedelta(days=30)
            for i in issues
        )
        _assert(sql["observed_open_issues"] == open_count,
                f"{name}: observed open Issue count differs")
        _assert(sql["observed_aged_open_issues"] == old_count,
                f"{name}: aged open Issue count differs")
        metrics = report.get("issues") or {}
        _assert(metrics.get("observed_open_partial") == open_count,
                f"{name}: Python observed Issue count differs")
        _assert(metrics.get("sample_aged_open") == old_count,
                f"{name}: Python age sample differs")
        backlog_verified = report.get("open_backlog_status") == "complete"
        _assert(bool(sql["open_inventory_verified"]) == backlog_verified,
                f"{name}: SQL open-backlog completeness differs")
        _assert(bool(metrics.get("full_open_backlog_verified")) ==
                backlog_verified, f"{name}: Python open-backlog flag differs")
        if not backlog_verified:
            _assert(metrics.get("aged_percent") is None
                    and metrics.get("aged_denominator") is None,
                    f"{name}: unverified backlog has a purported full ratio")
        else:
            _assert(metrics.get("aged_denominator") == open_count,
                    f"{name}: full backlog denominator disagrees")
        prs = report.get("pr_rows") or []
        merged = sum(
            bool(p.get("merged_at"))
            and threshold <= utc(p["merged_at"]) <= now for p in prs
        )
        _assert(merged == sql["observed_merged_28d"],
                f"{name}: merged PR numerator disagrees")
        ci = report.get("ci_rows") or []
        for label, outcomes in (
            ("observed_successful_checks_28d", {"success"}),
            ("observed_failed_checks_28d", {"failure", "timed_out"}),
        ):
            n = sum(
                row.get("status") == "completed"
                and row.get("conclusion") in outcomes
                and row.get("created_at")
                and threshold <= utc(row["created_at"]) <= now
                for row in ci
            )
            _assert(n == sql[label],
                    f"{name}: CI {label} disagrees with stored events")

    by_source = analysis_window_coverage(reports, days=28, now=now)
    sql_by_source = {
        source: sum(int(row[SQL_FLAGS[source]]) for row in sql_rows)
        for source in SOURCES
    }
    _assert(by_source == sql_by_source,
            "Verified 28-day cohort differs between SQL and Streamlit")
    joined = verified_joint_cohort(reports, days=28, now=now)
    return {
        "status": "passed",
        "repositories": len(reports),
        "verified_28d": by_source,
        "joint_verified_28d": len(joined),
        "full_open_backlog": sum(
            r.get("open_backlog_status") == "complete" for r in reports),
        "record_counts": {
            source: sum(len(r.get(ROW_KEYS[source]) or []) for r in reports)
            for source in SOURCES},
        "limitation": (
            "Consistency of original stored observations is verified; "
            "this does not prove incomplete GitHub REST sources complete."
        ),
    }


def main():
    from src.config.settings import Settings
    from src.database.store import make_engine, session_factory
    from src.analytics.read import load_reports
    from src.analytics.snapshot import read_snapshot
    from scripts.sql_insights import sql_delivery_signals

    now = datetime.now(timezone.utc)
    snapshot, _, meta = read_snapshot(now=now)
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    try:
        with session_factory(engine)() as session:
            sql = sql_delivery_signals(session, now=now)
            persisted = load_reports(session, now=now,
                                     stale_hours=settings.stale_hours)
        check = audit_consistency(snapshot, sql, now=now)
        _assert([r["repository"]["full_name"] for r in snapshot] ==
                [r["repository"]["full_name"] for r in persisted],
                "Snapshot/SQL restored selected set is not identical")
        for s, d in zip(snapshot, persisted):
            for source in SOURCES:
                _assert(len(s.get(ROW_KEYS[source]) or []) ==
                        len(d.get(ROW_KEYS[source]) or []),
                        "Restored SQL source lost or duplicated records")
            _assert(s.get("open_backlog_status") ==
                    d.get("open_backlog_status"),
                    "Stored snapshot and database backlog status disagree")
        print("P0 CROSS-SOURCE INTEGRITY:", json.dumps(
            check, sort_keys=True))
        path = os.getenv("GITHUB_STEP_SUMMARY")
        if path:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n### P0 cross-source integrity (real restored snapshot)\n\n")
                f.write(
                    f"**PASSED** · {check['repositories']} original public repos; "
                    f"{check['joint_verified_28d']} matching three-source "
                    "28-day projects. Snapshot / SQL counts match. "
                    "Missing source windows are not filled with synthetic data.\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
