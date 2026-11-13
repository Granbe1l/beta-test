# SQL database usage — Project Delivery Monitor

**Short answer:** yes, the data-ingestion pipeline uses a relational SQL database.
The default is **SQLite**, accessed through Python's **SQLAlchemy ORM**.
**PostgreSQL** is supported when DATABASE_URL is configured, but is not
necessary for the public Streamlit demonstration.

## Actual architecture

1. GitHub REST API responses are normalized in Python.
2. SQLAlchemy inserts or updates persistent records in these SQL tables:
   - repositories: the fixed, selected public repository cohort
   - issues: observed GitHub issues
   - pull_requests: observed PRs
   - workflow_runs: observed GitHub Actions checks
   - sync_checkpoints: per-repository/source status, coverage and resume state
   - sync_logs: collection attempts
   - selection_runs and selection_candidates: auditable sample selection
3. The collector exports a timestamped compressed JSON snapshot to
   data/github_public_snapshot.json.gz.
4. In the default publicly hosted demo, Streamlit reads that snapshot and
   computes metrics with Python/Pandas. It does **not** query a live SQL
   service on every page view.
5. If DATABASE_URL is explicitly supplied, the app can read the SQL
   database instead of the snapshot.

## SQL examples corresponding to stored tables

The following are **illustrative SELECT queries**, not a claim that the
dashboard executes these exact raw SQL statements. Most existing database
operations are written using SQLAlchemy's Python ORM.

**Count the observed open issues by selected repository:**

```sql
SELECT r.full_name,
       COUNT(i.id) AS observed_open_issues
FROM repositories AS r
LEFT JOIN issues AS i
  ON i.repo_id = r.id
 AND i.state = 'open'
WHERE r.selected = TRUE
GROUP BY r.id, r.full_name
ORDER BY observed_open_issues DESC;
```

**Inspect the actual collection state and coverage of every source:**

```sql
SELECT r.full_name,
       sc.source,
       sc.status,
       sc.coverage_start,
       sc.last_success_at
FROM repositories AS r
JOIN sync_checkpoints AS sc
  ON sc.repo_id = r.id
WHERE r.selected = TRUE
ORDER BY r.full_name, sc.source;
```

These counts are **observed records**; they do not imply the GitHub issue
history is complete. A responsible analysis checks the associated
sync_checkpoints row and the chosen 7/28/90-day verification window.

## How to describe this accurately on a CV

> GitHub REST API data pipeline using Python, SQLAlchemy and SQLite;
> reproducible source checkpoints; analysis and visualization using
> Pandas, Plotly and Streamlit; optional PostgreSQL database backend.

Do not describe this project as one with extensive handwritten SQL
queries, SQL-native dashboards, or a live PostgreSQL deployment unless
those additional capabilities have actually been implemented and verified.
