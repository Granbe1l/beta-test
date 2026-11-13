"""Read-only SQL audit of observed GitHub data in SQLite or PostgreSQL.

This is a real SQL query against the collector's tables, independent from
the public Streamlit snapshot renderer. It never estimates missing history.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys

# Allow `python scripts/sql_insights.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.orm import Session

from src.analytics.metrics import utc


QUERY = text("""
WITH issue_stats AS (
    SELECT repo_id, COUNT(*) AS issue_rows,
           SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) AS open_issues,
           SUM(CASE WHEN state = 'open' AND created_at <= :age_cutoff
                    THEN 1 ELSE 0 END) AS aged_open_issues
    FROM issues GROUP BY repo_id
),
pr_stats AS (
    SELECT repo_id, COUNT(*) AS pr_rows,
           SUM(CASE WHEN merged_at BETWEEN :window_start AND :now
                    THEN 1 ELSE 0 END) AS merged_28d
    FROM pull_requests GROUP BY repo_id
),
ci_stats AS (
    SELECT repo_id, COUNT(*) AS ci_rows,
           SUM(CASE WHEN status = 'completed' AND conclusion = 'success'
                         AND created_at BETWEEN :window_start AND :now
                    THEN 1 ELSE 0 END) AS successful_28d,
           SUM(CASE WHEN status = 'completed'
                         AND conclusion IN ('failure', 'timed_out')
                         AND created_at BETWEEN :window_start AND :now
                    THEN 1 ELSE 0 END) AS failed_28d
    FROM workflow_runs GROUP BY repo_id
)
SELECT r.full_name AS repository,
       COALESCE(i.issue_rows, 0) AS retrieved_issue_rows,
       COALESCE(i.open_issues, 0) AS observed_open_issues,
       COALESCE(i.aged_open_issues, 0) AS observed_aged_open_issues,
       COALESCE(p.pr_rows, 0) AS retrieved_pr_rows,
       COALESCE(p.merged_28d, 0) AS observed_merged_28d,
       COALESCE(c.ci_rows, 0) AS retrieved_ci_rows,
       COALESCE(c.successful_28d, 0) AS observed_successful_checks_28d,
       COALESCE(c.failed_28d, 0) AS observed_failed_checks_28d,
       CASE WHEN ic.status = 'complete'
             AND ic.coverage_start <= :window_start
             AND ic.last_success_at >= :fresh_cutoff
            THEN 1 ELSE 0 END AS issues_verified_28d,
       CASE WHEN pc.status = 'complete'
             AND pc.coverage_start <= :window_start
             AND pc.last_success_at >= :fresh_cutoff
            THEN 1 ELSE 0 END AS prs_verified_28d,
       CASE WHEN cc.status = 'complete'
             AND cc.coverage_start <= :window_start
             AND cc.last_success_at >= :fresh_cutoff
            THEN 1 ELSE 0 END AS ci_verified_28d
FROM repositories r
LEFT JOIN issue_stats i ON i.repo_id = r.id
LEFT JOIN pr_stats p ON p.repo_id = r.id
LEFT JOIN ci_stats c ON c.repo_id = r.id
LEFT JOIN sync_checkpoints ic ON ic.repo_id = r.id AND ic.source = 'issues'
LEFT JOIN sync_checkpoints pc ON pc.repo_id = r.id AND pc.source = 'pull_requests'
LEFT JOIN sync_checkpoints cc ON cc.repo_id = r.id AND cc.source = 'workflow_runs'
WHERE r.selected = TRUE
ORDER BY observed_aged_open_issues DESC, r.full_name
""").bindparams(
    bindparam("age_cutoff", type_=DateTime(timezone=True)),
    bindparam("window_start", type_=DateTime(timezone=True)),
    bindparam("now", type_=DateTime(timezone=True)),
    bindparam("fresh_cutoff", type_=DateTime(timezone=True)),
)


def sql_delivery_signals(session: Session, *, now=None) -> list[dict]:
    """Group each source before JOINs to avoid issue × PR × CI double counts."""
    now = utc(now or datetime.now(timezone.utc))
    params = {
        "now": now,
        "window_start": now - timedelta(days=28),
        "age_cutoff": now - timedelta(days=30),
        "fresh_cutoff": now - timedelta(hours=12),
    }
    return [dict(row) for row in session.execute(QUERY, params).mappings().all()]


def main():
    from src.config.settings import Settings
    from src.database.store import make_engine, session_factory
    engine = make_engine(Settings.from_env().database_url)
    try:
        with session_factory(engine)() as session:
            rows = sql_delivery_signals(session)
        if not rows:
            raise SystemExit("No curated repository records: restore the real snapshot first")
        result = {
            "repository_count": len(rows),
            "verified_28d": {
                key: sum(row[key] for row in rows)
                for key in ("issues_verified_28d", "prs_verified_28d", "ci_verified_28d")
            },
            "top_observed_aged_issue_repositories": rows[:5],
            "limitation": (
                "Observed record counts are not full backlog or client delivery status. "
                "Check each source's verified_28d flag before interpreting 28-day values."
            ),
        }
        print("SQL DELIVERY AUDIT:", json.dumps(result, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
