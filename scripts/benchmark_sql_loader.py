"""P2.1: count actual SQL SELECTs and source rows in the restored real database.

Runner-side timings are NOT end-user browser load times. SQL counts are
deterministic and can be compared to the former per-repo N+1 implementation.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import event
from src.config.settings import Settings
from src.database.store import make_engine, session_factory
from src.analytics.read import load_reports
from src.analytics.snapshot import SNAPSHOT_PATH, read_snapshot


def main():
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    try:
        statements = []
        def count_sql(conn, cursor, statement, params, context, executemany):
            if statement.lstrip().lower().startswith("select"):
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", count_sql)
        try:
            start = perf_counter()
            with session_factory(engine)() as session:
                reports = load_reports(session, stale_hours=settings.stale_hours)
            elapsed = perf_counter() - start
        finally:
            event.remove(engine, "before_cursor_execute", count_sql)

        snapshot, _, meta = read_snapshot(SNAPSHOT_PATH)
        def ids(items):
            return {x["repository"]["full_name"] for x in items}
        assert ids(reports) == ids(snapshot), (
            "SQL loader selected different real repositories from original snapshot")

        rows_sql = {source: sum(len(r[source]) for r in reports)
                    for source in ("issue_rows", "pr_rows", "ci_rows")}
        rows_snapshot = {source: sum(len(r[source]) for r in snapshot)
                         for source in rows_sql}
        assert rows_sql == rows_snapshot, "Batched SQL lost original GitHub rows"
        queries = len(statements)
        assert queries <= 8, (
            f"Unexpected N+1 SQL loader regression: {queries} SELECTs")
        result = {
            "status": "passed",
            "benchmark_kind": "CI runner-side restored SQLite query audit (not browser timing)",
            "snapshot_generated_utc": meta["generated_at"].isoformat(),
            "repositories": len(reports),
            "select_queries": queries,
            "former_loader_query_formula": "1 + 5 * selected_repositories",
            "new_loader_query_formula": "6 queries for up to 500 repositories",
            "load_seconds_runner": round(elapsed, 3),
            "stored_rows_match_snapshot": rows_sql,
            "data_source": "restored real GitHub snapshot, no fabricated project records",
        }
        Path("sql-loader-benchmark.json").write_text(
            json.dumps(result, sort_keys=True, indent=2), encoding="utf-8")
        print("P2.1 SQL BATCH BENCHMARK:", json.dumps(result, sort_keys=True))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
                f.write("\n### P2.1 SQL batch loader (real restored GitHub snapshot)\n\n")
                f.write(
                    f"**PASS** · {queries} SELECTs for {len(reports)} real repositories; "
                    f"{sum(rows_sql.values()):,} original rows; "
                    f"{elapsed:.2f}s on CI runner. "
                    "Timing is not a browser UX or SLA claim.\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
