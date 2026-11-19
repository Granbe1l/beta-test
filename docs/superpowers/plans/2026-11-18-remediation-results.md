# F1–F12 remediation results — 18 November 2026

Branch: `audit-menyeluruh`. Uncommitted changes against `b893c04b14e0ae4d745218ec35ea83b728530f9d`.
All statuses below mean locally fixed and tested, not deployed. The execution ledger contains the RED/GREEN checkpoints and review corrections.

| Finding | Priority | Status | Result and changed files |
|---|---|---|---|
| F1 | P1 | fixed | Pinned-cohort promotion refuses before mutation. `scripts/promote_verified_candidates.py`, `promote-targets.yml`, `promote-verified.yml`, promotion tests. |
| F2 | P1 | fixed | Main-only baseline capture; committed data tree checked on every publication retry; stale HEAD/new origin-main rejected; cutover provenance mandatory. `public-snapshot.yml`, `scripts/verify_collection.py`, `scripts/curate_verified_50.py`, publication/preflight/transition tests. |
| F3 | P2 | fixed* | External GitHub IDs use PostgreSQL BIGINT with SQLite INTEGER variant. `src/database/models.py`, `tests/test_large_github_ids.py`, `docs/SQL_DATABASE_USAGE.md`. *Existing PostgreSQL schema migration is not executed or validated against a live server.* |
| F4 | P2 | fixed | Cache records actual interval bounds; unproven legacy intervals are re-read. `src/collectors/sync.py`, `tests/test_windowed_ci.py`. |
| F5 | P2 | fixed | Identity mismatch blocks source and independent backlog collection; persistent quarantine requires positive ID revalidation. `sync.py`, `tests/test_sync.py`. |
| F6 | P2 | fixed | Transport/probe failures and budget exhaustion remain distinct from page caps; partial HTTP pages and adaptive progress survive. `sync.py`, `client.py`, `src/discovery/selection.py`, collector/discovery tests. |
| F7 | P2 | fixed | Worker commit/run history scoped to main; malformed branch provenance fails closed. `external_refresh/cloudflare/worker.mjs`, `worker.test.mjs`. |
| F8 | P2 | fixed | Inspector states skipped/neutral exclusions; metric formulas unchanged. `src/analytics/inspector_presenter.py`, inspector tests. |
| F9 | P2 | fixed | Same configured freshness reaches snapshot, database and SQL. `scripts/sql_insights.py`, `scripts/verify_kpi_integrity.py`, SQL tests. |
| F10 | P2 | fixed | Main rescue completion triggers schedule observation; rescues still excluded from native cron proof. `schedule-audit.yml`, postrun observer tests. |
| F11 | P3 | fixed | Current four-hour watchdog, historical policy caveats, explicit venv activation and deliberate force-refresh instructions. `README.md`, `docs/REPRODUCIBILITY.md`, `docs/GITHUB_ONLY_REFRESH_PLAYBOOK.md`, `docs/P0_3_DISPATCH_PREFLIGHT.md`, Cloudflare README; workflow/watchdog comments. |
| F12 | P3 | fixed | Permanent 403 stops immediately; actual rate limits retry; invalid Actions envelopes fail; short page follows next link. `src/collectors/client.py`, `tests/test_client.py`. |

## Verification

| Check | Observed result |
|---|---|
| Final Python 3.12.4 regression | 539 passed in 62.68s, exit 0; `.venv/final-reviewed-regression.log` |
| Cloudflare / Node 16.18.0 | 19 passed; direct `node external_refresh/cloudflare/worker.test.mjs`; `.venv/final-node-direct.log` |
| Actual snapshot restore | Disposable SQLite: 50 repos, 5,463 Issues, 6,177 PRs, 52,072 CI runs; exact source IDs preserved; second restore prevents duplication |
| SQL/KPI parity | Passed at snapshot generation and 2026-11-18 11:37:09 UTC; batched loader uses 6 SELECTs; `.venv/final-restore.log` |
| Actual snapshot Streamlit | All six routes rendered with network prohibited; 1 test passed in 6.78s, exit 0; `.venv/final-real-snapshot-apptest-exit.log` |
| Dataset / cohort | 50 unique IDs/names, exact manifest membership; archive/receipt validate-only passed; all six original SHA-256 hashes unchanged |
| Environment / diff | `pip check` and `git diff --check` passed; no actual data diff |

The full Python suite covers SQL/KPI, fixture restore, AppTest, publication retries, scheduler and source-audit gates. No live API calls were needed. Git commits and simulated remote operations in publication tests belong only to disposable fixture repositories. Logs/probes are ignored under `.venv`; the real-snapshot temporary database was removed after use.

## Targeted P0 assessment

- Cohort, stored source identity, archive and snapshot consistency: local checks passed without changing data.
- At generation time (2026-11-17 23:59:21 UTC): 50/50 joint Verified 28-day sources and 50/50 fresh full-open inventories.
- At the current probe (18 November 18:37:09 WIB): 50/50 joint Verified 28-day sources, **33/50 fresh full-open inventories**. These are dated readings of stored evidence, not a guarantee of current coverage or a new GitHub crawl.
- Publication: stale baseline and changes on retries 1/2/3 reject in executed workflow fixtures. No actual publication was attempted.
- GitHub Actions/scheduler: local admission, slot accounting and source-proof tests pass. Native four-hour punctuality remains operationally unverified.
- Cloudflare: main guards, four-hour threshold and dispatch behavior pass locally. Hourly cron is unchanged. No deployment or current production log validation occurred. Commit age in Worker and generated_at age in preflight remain different clocks.

## Remaining risks and before-merge recommendations

1. Review the complete uncommitted diff. Keep the production rollout separate and explicitly authorized.
2. If PostgreSQL is deployed, design/review the existing-schema BIGINT migration before rollout; fresh DDL tests do not migrate a live database.
3. Budget the first upgraded collector for conservative legacy cache revalidation. It can take extra bounded calls and temporarily remain partial; do not weaken publication checks.
4. After an authorized rollout, collect actual native schedule slots, rescue invocation/dispatch and resulting collector/source audit/publication receipts. A manual success cannot substitute for native cron evidence. Recheck fresh full-open denominators before a portfolio demo.
5. Deferred minor items: retired promotion CLI still parses obsolete inputs before safe refusal; Streamlit emits existing width-API deprecation warnings. No UI redesign or optional refactor was included.

No commit, push, merge, deployment, cohort/metric-definition change or production Cloudflare action was performed.
