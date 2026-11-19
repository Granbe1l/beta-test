# Audit F1–F12 implementation plan

> Execute with superpowers:executing-plans and test-driven-development, in priority order.

**Goal:** Correct the audited defects while preserving the pinned 50-repository cohort and actual datasets.
**Architecture:** Keep the existing collector, SQL, snapshot and UI boundaries. Fail closed at publication and identity boundaries; preserve diagnostic provenance.
**Tech stack:** Python 3.12, pytest, SQLAlchemy, Streamlit, Node test runner.
**Spec:** Approved F1–F12 audit and execution instructions in this chat, 18 November 2026.

## Constraints and rulings

- Work on `audit-menyeluruh`; no commits, push, merge or deployment.
- Never modify actual data files or production Cloudflare.
- Cohort remains pinned. F1 will block legacy replacement of the pinned cohort rather than introduce a new cohort policy.
- User already authorized execution: proceed without a second plan-approval gate.
- Use existing checkout as explicitly requested; do not create a different branch/worktree.
- All tests use temporary copies/in-memory fixtures; local environment and logs remain under ignored `.venv`.

## Sequential tasks

Each code task: write regression, observe relevant failure, implement root fix, run focused tests and relevant regression before continuing. Record commands/results below.

- [x] Environment: verify Python 3.12, isolated `.venv`, install declared requirements, run baseline suite.
- [x] F1 / P1: `scripts/promote_verified_candidates.py`, promotion workflows; test pinned membership rejects promotion before API/database mutations. Keep independent candidate audits usable.
- [x] F2 / P1: public snapshot workflow and publication guard helper; test non-main rejection, queued baseline admission, and changed snapshot/manifest before publication in temporary Git repos. Refuse stale publication rather than overwrite it.
- [x] F3 / P2: external GitHub identifiers in database models; test PostgreSQL DDL capacity and SQLite real large-ID roundtrip. No automatic production schema migration.
- [x] F4 / P2: CI interval caching; reproduce earlier-start reuse, preserve full-day/shard bounds and existing resume semantics.
- [x] F5 / P2: metadata identity mismatch; assert collection and open inventory cannot continue for wrong identity, preserve transient-error behavior.
- [x] F6 / P2: preserve CI transport errors versus page caps and discovery probe errors; test status and retained progress.
- [x] F7 / P2: Worker main-only run history; test unrelated-branch active/backoff cases with main equivalents.
- [x] F8 / P2: inspector completed known-outcome denominator; test neutral/skipped/cancelled/pending mixture and presenter.
- [x] F9 / P2: configured freshness through SQL and snapshot integrity gate; test four/twelve-hour policies against identical records.
- [x] F10 / P2: observe main rescue completions without treating them as native cron proof; test event eligibility and slot accounting.
- [x] F11 / P3: reconcile current scheduler docs and explicit venv commands; review current versus historical statements.
- [x] F12 / P3: client permanent 403, invalid wrapped response, short page continuation; regression without live API calls.
- [x] Final: full Python/Node suite, real snapshot restore to temporary SQLite, SQL/KPI parity, Streamlit tests, independent review, verify actual dataset hashes unchanged.

## Review focus

- All publishing paths must respect pinned membership and main-only policy.
- Concurrent publication must never silently replace a changed baseline.
- Wrong repository identity must not reach secondary open-inventory collection.
- Cached clipped intervals must not certify unobserved time.
- Freshness parameters and outcome denominators must agree across layers.

## Execution ledger

- Baseline: clean `audit-menyeluruh`, SHA `b893c04b14e0ae4d745218ec35ea83b728530f9d`.
- Python 3.12.4 found outside PATH; `.venv` created. Pip requires Windows trust store (`--use-feature=truststore`); TLS verification retained.
- F1 RED: pinned promotion regression reached snapshot read and failed. GREEN: promotion now refuses before data/API access; both legacy workflows are read-only diagnostic failures. Candidate audit workflows remain usable. Focused promotion/curation: 11 passed.
- F2 RED: no baseline gate existed (five new regressions failed). GREEN: main-only workflow admission, latest-main checkout, committed data-tree capture, and data-tree verification inside every publication retry before reset/replay. Added exact old-HEAD/new-origin-main case.
- Workflow execution regression uses disposable Git repositories, real Git and Python, with remote fetch/push simulated. Changes arriving on attempts 1, 2, and 3 abort before the corresponding push.
- Baseline full suite initially stalled in Windows sandbox at asyncio socketpair during AppTest. Interrupted without claiming a pass. Outside sandbox the full suite passed 496 tests; Git Bash also requires that environment. No app workaround or TLS bypass introduced.
- Independent review: F1 accepted; F2 exposed missing archive/receipt recovery after removing the historical cutover publisher. Three additional regressions observed RED. Fixed by requiring committed cutover provenance and `curate_verified_50.py --validate-only` in normal refresh. Missing provenance or legacy 75-repository input now stops without reconstruction/migration.
- Post-review focused regression: 72 passed. Expanded full suite: **501 passed in 57.45s**, command `.venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider -o faulthandler_timeout=60`; log `.venv/f1-f2-final-tests.log`. Cloudflare existing suite: 17 passed, 0 failed (Node 16.18.0 experimental-runner warning).
- Review minor deferred: retired promotion CLI still parses proof/obsolete environment options before refusing. It cannot mutate data; simplifying its diagnostic-only CLI is optional and outside the prioritized root fixes.
- All six actual data-file SHA-256 hashes remain identical to `.venv/dataset-before.json`. No real repository commits or remote writes. Fixture Git commits are restricted to pytest temporary repositories.
- Checkpoint before F3: F1/F2 complete; independent important finding fixed RED→GREEN, full suite green, `git diff --check` clean. F3–F12 have not been modified at this checkpoint.
- F3: external-ID PostgreSQL DDL regression RED (INTEGER), GREEN (BIGINT), SQLite retains INTEGER semantics. Large actual-scale ID roundtrip plus collector/integration/snapshot/SQL/KPI regression: 21 passed. Existing PostgreSQL migration is deliberately not automatic; documented as an owner-reviewed deployment prerequisite, not executed or claimed tested against a live server.
- F4: expanded first-day regression RED (09:00 record omitted), GREEN with per-bucket `_bounds` provenance. Legacy earliest cached day is conservatively re-read; current day always refreshed. Added clipped shard and legacy-cache cases; existing reuse tests now explicitly provide full-day bounds. Focused cache/maintenance regression: 18 passed.
- F5: reused-slug regression RED (collection reached wrong source), GREEN with identity quarantine, failed checkpoint diagnostics and exclusion from independent open inventory/observations. Transient metadata failures retain existing behavior. Collector/integration/inventory regression: 22 passed.
- F6: first-error and partial-progress HTTP404 cases RED (page-cap misclassification), discovery probe RED (run falsely complete); GREEN preserving sanitized exception and completed progress, marking zero-progress failure and propagating selection probe errors. Combined collector/discovery/integration regression: 40 passed.
- Latest checkpoint revalidation (no repeated audit): F1–F6 focused regression **71 passed in 16.36s**; log `.venv/f1-f6-checkpoint-tests.log`. Files for F3: models/SQL usage/tests; F4: sync/windowed CI tests; F5: sync/sync tests; F6: sync/discovery and matching tests. No regressions found.
- F7 complete: Worker branch-history RED (`skip_active` for candidate), GREEN main-scoped commit/run queries and main-only guard history; unknown branch RED→GREEN fail-closed. `worker.mjs`, `worker.test.mjs`; **19 Node tests passed**, `.venv/f7-green.log`. Four-hour threshold, hourly cron and backoffs unchanged; source only, no deployment. Next F8: correct denominator wording without changing the metric.
- F8 complete: mixed outcome regression RED (undisclosed exclusions), GREEN by explicitly labelling the existing inspector denominator as excluding skipped/neutral. No counts, formulas or main-cohort metric definitions changed. `inspector_presenter.py`, `test_public_repo_inspector.py`; **41 tests passed** (inspector/presenter/export/metrics). Next F9 freshness configuration propagation.
- F9 complete: six freshness regressions RED (unsupported SQL policy and snapshot/database disagreement), GREEN with configured stale_hours passed through SQL CLI and integrity entrypoint to all three readers. Files: scripts/sql_insights.py, scripts/verify_kpi_integrity.py, tests/test_sql_insights.py. SQL/KPI/snapshot: 17 passed. Default policy unchanged; next F10 observer eligibility.
- F10 complete: actual observer predicate RED for main rescue and non-main schedule, GREEN with main-only schedule/dispatch eligibility. Native-only counting and missing-slot tests retained. Files: schedule-audit.yml, test_schedule_postrun_audit.py. 40 scheduler/source-gate tests passed. No new periodic schedule or production execution; next F11 docs.
- F11 complete: corrected current four-hour watchdog/source status, preserved historical P0.3 proposal with supersession note, documented default dispatch skipping/explicit force and venv activation. Files: README, REPRODUCIBILITY, GITHUB_ONLY_REFRESH_PLAYBOOK, P0_3_DISPATCH_PREFLIGHT, Cloudflare README, workflow descriptions and watchdog comments. Documentation-only review against existing constants; no behavior change or production claim. Next F12 client TDD.
- F12 complete: eight failing regressions reproduced permanent-403 retries, malformed Actions envelopes and short-page truncation. GREEN with rate-limit-specific 403 retry, mandatory valid wrapper/total_count, and next-link-driven continuation. Files: src/collectors/client.py, tests/test_client.py. 66 focused client/collector/discovery/inspector tests passed. Next final independent review and full regression; no live API calls.

- Final review found additional real F4/F5/F6 paths; all reproduced RED before changes. F4 now refuses every legacy cache entry without explicit interval bounds (one-time extra bounded API work; no inferred coverage). F5 checks backlog-only candidates and retains known identity quarantine through transient metadata failures until positive ID revalidation. F6 retains adaptive retry errors and real partial HTTP pages, and labels request-budget reserve separately. Six new regressions RED -> GREEN; focused client/CI/sync/inventory suite: 63 passed. Files: sync.py, client.py, test_sync.py, test_windowed_ci.py. No second review required; full regression follows.
- First final full regression before review corrections: 533 passed in 69.86s (.venv/final-regression.log). Node 16 direct runner `node external_refresh/cloudflare/worker.test.mjs`: 19 passed (.venv/final-node-direct.log); `node --test` only reported the file on this runtime and is not used as case-count evidence.
- Real snapshot restored to disposable SQLite: 50 repositories, 5,463 Issues, 6,177 PRs, 52,072 CI runs; second restore refused duplication. Exact row IDs and SQL/KPI parity passed at generation time and 2026-11-18T11:37:09Z. Batched loader: 6 SELECTs. At generation: 50/50 joint 28d and full-open. At current probe: 50/50 joint 28d but only 33/50 fresh full-open inventories. All six data hashes unchanged. Log .venv/final-restore.log. No live source re-download or scheduler operational proof.

- Final verification after all review fixes: **539 passed in 62.68s**, process exit 0, `.venv/final-reviewed-regression.log`. Includes publication retry fixtures, scheduler/source proof, SQL/KPI, restore and Streamlit fixture AppTests. Cloudflare direct Node runner **19 passed**, `.venv/final-node-direct.log` (unchanged since that run).
- Additional actual snapshot AppTest: all six routes rendered, network requests prohibited; **1 passed in 6.78s, explicit process exit 0**, `.venv/final-real-snapshot-apptest-exit.log`. Initial PowerShell wrapper treated Streamlit stderr warnings as an error despite passing tests; explicit exit-code verification resolved it. Deprecation warnings remain; no UI redesign made.
- Final pinned-cohort validation: `curate_verified_50.py --validate-only` passed; 50 unique names/IDs, exact manifest names, all six initial SHA-256 hashes unchanged. `pip check` clean; `git diff --check` clean. HEAD remains b893c04b14e0ae4d745218ec35ea83b728530f9d on audit-menyeluruh. No commit, push, merge, deployment or production Cloudflare changes.
- Ruling: F8 corrects the inspector label rather than changing its denominator because the owner forbids metric-definition changes. Cost: inspector and main cohort retain different documented outcome populations.
- Ruling: Legacy CI cache without interval provenance is re-read rather than inferred complete. Cost: extra bounded API calls on the first upgraded refresh, possibly partial coverage until later retries; validation remains strict.
- Ruling: Existing PostgreSQL deployments require a separately approved migration; only fresh-schema BIGINT DDL and SQLite roundtrip were verified. Cost: an old INTEGER schema remains incompatible until migrated.
- Final: minor (deferred): retired promotion CLI parses legacy proof/options before refusing; no mutation is possible.
- Final: minor (deferred): Streamlit emits use_container_width deprecation warnings; current AppTests pass, future compatibility needs a separately scoped update.
- Operational boundary: production rescue/cron reliability is NOT established by local tests. Historical production receipts are not evidence for this uncommitted branch. Cloudflare ages snapshot commits while GitHub preflight ages generated_at; retain that distinction. Optional hosting/PostgreSQL runtime were not exercised. A manual/rescue dispatch never proves native cron reliability.
- Handoff: F1-F12 local code/documentation fixes complete; no implementation remains from the accepted findings. Before merge: review diff, prepare PostgreSQL migration only if deployed, plan bounded cache revalidation/API capacity, and obtain dated production native/rescue runs plus source-audit/publication artifacts after separately authorized rollout. No automatic rollout here. Detailed status and files: docs/superpowers/plans/2026-11-18-remediation-results.md. Temporary scripts/logs stay in ignored .venv; disposable restore DB was removed by TemporaryDirectory. Do not commit .venv.
