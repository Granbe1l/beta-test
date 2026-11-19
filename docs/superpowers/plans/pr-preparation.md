# PR preparation checkpoint — 19 November 2026

## Decision: CONDITIONAL — candidate ready for authorized PR preparation, not merge

This task prepares a file allowlist, integration assessment and draft PR only. No staging, commit, push, merge, reset, deployment or application/data edit was performed. Existing F1–F12/N1–N2 audit and regression results are reused rather than repeated.

## Baseline verification — selesai

- Branch: `audit-menyeluruh`.
- Local HEAD: `b893c04b14e0ae4d745218ec35ea83b728530f9d`.
- Freshly fetched origin/main: `1a2110ebe5dacce2ee956fc1c6a5a576edd7ecd7`.
- Fetch command: `git -c http.sslVerify=true -c http.sslBackend=schannel fetch origin main`.
- First sandbox attempt could not write `.git/FETCH_HEAD`; the authorized escalated retry succeeded. TLS verification remained enabled with Windows certificate trust. No `sslVerify=false`, insecure download or global Git config change.
- `git rev-list --left-right --count HEAD...origin/main`: **0 local / 6 upstream commits**. All six upstream commits update only `data/github_public_snapshot.json.gz`; no upstream code/workflow/test/documentation changes.
- Upstream commits, newest first: `1a2110e`, `7d42e15`, `2031cca`, `89c7559`, `8d0c2cf`, `b738edd`.
- No overlapping modified paths between upstream changes and the candidate allowlist. No textual conflict is indicated by this path comparison; no actual merge was executed, so this is not a completed merge test.

## Dataset exclusion and integration — selesai with follow-up

- All six LOCAL dataset hashes still match the original audit baseline. No local dataset change will enter the candidate.
- Latest remote snapshot was read directly from Git into memory, not checked out or written: schema 1; same 50 unique repository IDs/names and exact local manifest membership. Capture: `2026-11-18T23:05:38.544558+00:00`; 5,551 Issue / 6,310 PR / 54,095 CI rows. These are stored-record observations, not production-health evidence.
- Existing actual-restore regression used the older local snapshot. Do not claim it validates every row of the newly fetched snapshot. Exact-candidate GitHub CI should test the integration result with current main data.
- **Do not create a candidate patch from an unrestricted `git diff origin/main`: it includes the difference between old local and newer remote data.** Use the explicit allowlist below; no `data/` path belongs in it.
- Safe next integration approach, only after authorization: preserve this uncommitted candidate, prepare an isolated checkout from current main, and carry over only allowlisted code/tests/workflows/docs. Retain main's snapshot and manifests. Inspect the resulting diff and run checks appropriate to changed baseline data. Do not reset/merge this dirty checkout automatically.

## Candidate hygiene — selesai

- Before this report: 43 tracked modifications plus 8 untracked relevant files = 51 candidate files. This report adds one relevant document, for **52 allowlisted files** total.
- Untracked regression tests and checkpoint documents were explicitly inventoried; ordinary git diff alone omits them.
- No `data/`, `.venv/`, log, database, bytecode, `.env`, secrets.toml or temporary file appears in the candidate list. `.venv`, `.env` and Streamlit secrets paths are ignored.
- Candidate text scan found no common GitHub token, AWS access-key-ID or private-key-header pattern. This is a bounded hygiene check, not a claim of comprehensive secret/vulnerability clearance.
- Index was empty on entry and remains empty. `git diff --check` is clean. Existing production code and tests were not edited during preparation.

## Risks and blockers

| Item | Status | Consequence / next step |
|---|---|---|
| New P0/P1 from upstream | No new source change to assess | Upstream is snapshot-only; prior independent code review still applies. |
| Branch behind current main | Integration pending | Six upstream data commits must be preserved. No code-path conflict identified; use allowlist, never replay old local snapshot. |
| Exact PR candidate | Pending | Changes are uncommitted and no PR was created. The allowlist is review material, not an existing commit. |
| Hosted CI / branch protection | Pending merge gate | Obtain required checks for the exact candidate/integration SHA; local logs do not substitute. Repository settings were not inspected. |
| First refresh | Accepted availability risk | Unknown/private metadata blocks export; old cache entries need bounded revalidation. A partial first run must not trigger weakened validation or automatic cohort changes. |
| PostgreSQL | Conditional deployment prerequisite | Existing INTEGER installations need reviewed BIGINT migration; fresh DDL/SQLite tests do not migrate production. |
| Operational proof | Pending, separate from PR | No native schedule, Cloudflare rescue, live publication, hosting or current vulnerability scan was performed. |

## Draft PR

**Title:** Fix collector integrity and guard public snapshot publication

**Description:**

The collector could reuse clipped CI coverage, ingest records under a changed repository identity, or publish against an outdated data baseline. This change preserves the pinned 50-repository cohort, validates the committed main data baseline on every publication retry, and retains accurate partial/error provenance. It also corrects external ID capacity, freshness propagation, Worker main-branch guards, scheduler observation and API pagination/retry behavior.

Repositories with private, internal or unknown visibility now stop collection and public export until explicit public revalidation, including after restoring an older snapshot on a new runner. Historical records and cohort membership are retained. Quality CI evaluates stored evidence reproducibly at its original capture instant; publication separately requires current operational freshness. Dataset files, metric definitions and UI design are unchanged.

**Validation:** Python 3.12 local full regression: 550 passed; Cloudflare/Node: 19 passed; real-snapshot SQLite restore and SQL/KPI parity passed; all six Streamlit routes rendered with network blocked. Independent review identified an ephemeral-restore quarantine bypass, reproduced and corrected before the final green suite. No production rollout was performed. These results precede integration with the six newer upstream snapshot commits; hosted CI must validate the final candidate.

**Rollout notes:** Fail-closed visibility can delay refresh during metadata outages. Legacy cache revalidation may require additional bounded API work. Existing PostgreSQL needs a separately reviewed migration. A green reproducible audit is historical evidence, not a live-data or scheduler-reliability claim.

## GitHub CI checklist

- [ ] Exact PR commit includes all intended tracked and untracked files; no actual dataset, logs, secrets or .venv artifacts.
- [ ] PR integration tree preserves latest main snapshot; no unintended binary/data diff.
- [ ] Quality checks: Python 3.12 install/runtime receipt, compile, full pytest and Cloudflare Node tests pass on Ubuntu.
- [ ] Quality checks: actual-snapshot comparison audit, restore, SQL/KPI parity, SQL loader benchmark and reviewer evidence audit pass. Reviewer evidence uses `--reproducible` and labels capture time explicitly.
- [ ] UI screenshot workflow runs on the PR because `src/analytics/findings.py` changes; inspect its desktop/mobile artifacts. PR must not publish the gallery.
- [ ] N1 private/unknown/restore-cycle regressions, N2 historical/current separation and stale publication baseline retries are included in hosted test results.
- [ ] If vulnerability evidence is required, run the existing dependency-security workflow by an authorized action. Its path filter covers requirements/security-workflow changes, so **this candidate does not automatically trigger it**. Do not treat absence as a pass.
- [ ] Confirm repository-required reviews/checks and resolve any exact-commit failures before merge.
- [ ] Do not execute public refresh or Cloudflare deployment merely to prepare the PR. Their operational verification remains separately authorized.

## File allowlist

Paths below are the complete reviewed candidate inventory, including this checkpoint. `M` means tracked modification; `?` means untracked/new. It is not a staging command.

| Status | File |
|---|---|
| M | `.github/workflows/ci.yml` |
| M | `.github/workflows/promote-targets.yml` |
| M | `.github/workflows/promote-verified.yml` |
| M | `.github/workflows/public-snapshot.yml` |
| M | `.github/workflows/schedule-audit.yml` |
| M | `.github/workflows/snapshot-watchdog.yml` |
| M | `README.md` |
| M | `docs/GITHUB_ONLY_REFRESH_PLAYBOOK.md` |
| M | `docs/P0_3_DISPATCH_PREFLIGHT.md` |
| M | `docs/REPRODUCIBILITY.md` |
| M | `docs/SQL_DATABASE_USAGE.md` |
| ? | `docs/superpowers/plans/2026-11-18-audit-remediation.md` |
| ? | `docs/superpowers/plans/2026-11-18-final-review.md` |
| ? | `docs/superpowers/plans/2026-11-18-remediation-results.md` |
| ? | `docs/superpowers/plans/pr-preparation.md` |
| ? | `docs/superpowers/plans/pre-merge-review.md` |
| M | `external_refresh/cloudflare/README.md` |
| M | `external_refresh/cloudflare/worker.mjs` |
| M | `external_refresh/cloudflare/worker.test.mjs` |
| M | `scripts/audit_reviewer_evidence.py` |
| M | `scripts/curate_verified_50.py` |
| M | `scripts/promote_verified_candidates.py` |
| M | `scripts/snapshot_watchdog.py` |
| M | `scripts/sql_insights.py` |
| M | `scripts/verify_collection.py` |
| M | `scripts/verify_kpi_integrity.py` |
| M | `src/analytics/findings.py` |
| M | `src/analytics/inspector_presenter.py` |
| M | `src/analytics/read.py` |
| M | `src/analytics/snapshot.py` |
| M | `src/collectors/client.py` |
| M | `src/collectors/sync.py` |
| M | `src/database/models.py` |
| M | `src/discovery/selection.py` |
| M | `tests/test_client.py` |
| M | `tests/test_collector_dispatch_preflight.py` |
| M | `tests/test_curated_50_transition.py` |
| M | `tests/test_discovery.py` |
| M | `tests/test_integration.py` |
| ? | `tests/test_large_github_ids.py` |
| M | `tests/test_open_inventory_capacity.py` |
| M | `tests/test_public_repo_inspector.py` |
| ? | `tests/test_publication_baseline.py` |
| ? | `tests/test_reproducible_evidence.py` |
| M | `tests/test_safe_candidate_promotion.py` |
| M | `tests/test_scale75.py` |
| M | `tests/test_schedule_postrun_audit.py` |
| M | `tests/test_sql_insights.py` |
| M | `tests/test_sync.py` |
| M | `tests/test_verified_maintenance_order.py` |
| ? | `tests/test_visibility_quarantine.py` |
| M | `tests/test_windowed_ci.py` |

## Stop checkpoint

Preparation completed. Remote baseline comparison and file hygiene are **selesai**; exact candidate commit, integration CI and production evidence remain **tertunda**. Stop here as requested. No stage/commit/push/merge/deploy was performed, and no full audit or valid test suite was repeated.
