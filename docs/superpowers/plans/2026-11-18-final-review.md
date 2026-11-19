# Final independent audit — completed 19 November 2026

## Scope and baseline

- User requested review beyond F1–F12: integration, next refresh, data/Verified/KPI, security, six pages and Data Analyst/nontechnical/technical goals.
- Existing baseline evidence: 539 Python tests, 19 Node tests, actual snapshot SQLite restore/KPI parity and six-route AppTest. Reuse these results unless relevant code changes or a new hypothesis warrants another run.
- Branch audit-menyeluruh; baseline b893c04b14e0ae4d745218ec35ea83b728530f9d; F1–F12 remain uncommitted.
- No actual dataset/cohort/metric changes, commits, push, merge or deployment. Only proven P0/P1 bugs may be fixed with TDD; policy/high-risk changes require owner decision.
- Superpowers systematic-debugging, requesting-code-review and verification-before-completion applied. Fresh-context independent reviewer checks collector/security/workflows; primary checks dated freshness and goal/SQL/UI consistency.

## Checkpoint 1

- Read prior results and execution ledger, diff summary and skill instructions.
- Do not treat 33/50 full-open versus 50/50 three-source Verified as a defect without tracing independent checkpoints and timestamps.
- Next: derive the exact 17 exclusions at the original 2026-11-18T11:37:09.745112Z audit instant, inspect integration boundaries, collect independent findings and focused reproducers.

## Decision

**CONDITIONAL for merge**, not approval to deploy. No additional proven P0/P1 blocker was found in the bounded independent review. Conditions and verification boundaries below remain mandatory; absence of a finding is not proof that every execution is safe.

## Checkpoint 2 — resumed 19 November 2026

- Freshness explanation is settled, not re-audited: `.venv/final-review-freshness.json` records the original 18 November 11:37:09 UTC boundary. Seventeen independent inventories were 16.5471 hours old, three-source scans were 11.6393–11.7235 hours old; aged full-backlog percentages were null for all 17. This is correct separation, not a denominator defect. The historical 50/50 is not a current-status claim.
- Independent review was interrupted by a usage limit, then resumed in the same reviewer context. The earlier F4/F5/F6 review findings are already fixed and tested; they are not new findings here.
- New conditional P2: metadata refresh validates repository ID but not public visibility. A private-capable token can collect a selected repository after it becomes private. Reproduced with synthetic rows in in-memory SQLite; `.venv/final-audit-private-visibility.py`. Current public-snapshot uses its repository-scoped github.token, so third-party-private exposure is not established for the actual published cohort. No secrets or actual private records were used. No fix under the owner's P0/P1-only authorization.
- New operational P2 risk (not a false-data bug): CI runs `scripts/audit_reviewer_evidence.py`, whose `audit()` raises if the current 28-day verified cohort is empty. An unchanged snapshot at generated_at +24h reproduces that failure. `.venv/test_final_review_boundaries.py`: 1 passed, confirming the expected assertion. A delayed refresh can therefore block a code-only quality check. Whether to separate reproducibility from current freshness is a policy decision, not an automatic relaxation.
- Cross-writer review: snapshot publisher stages only its gzip after data-tree baseline checks; gallery publisher stages only docs/gallery files. Code/gallery-only changes do not invalidate the data-tree guard, while changed data does. Retired promotion jobs cannot publish. Optional PostgreSQL workflow has no Git snapshot publisher. No new overwrite path established.
- Next: finish independent reviewer report, check final hashes/diff and publish bounded merge decision. Existing 539/19 tests and six-page AppTest remain applicable; no production code changed in this review.

## Checkpoint 3 — final independent result

The resumed fresh-context reviewer completed collector/API, security and cross-workflow checks. Primary independently ran the private-visibility reproducer and verified the CI age-boundary test. No new P0/P1 was established, so no application/workflow fix was made under this audit's restricted authorization.

### New findings and constraints

| ID | Priority / category | Evidence and impact | Root cause / disposition |
|---|---|---|---|
| N1 | P2, proven conditional defect | `src/collectors/sync.py:471` (`refresh_repo_metadata`), matching-ID check; `scripts/build_public_snapshot.py` exports selected reports. Synthetic metadata with matching ID and private=True yields three complete source statuses and stores a synthetic private title. Probe `.venv/final-audit-private-visibility.py` exits 0. | Discovery rejects private projects initially, but refresh never rechecks visibility. A private-capable PAT/local or optional PostgreSQL collector can ingest newly private content. Actual disclosure and reachability with current public workflow token are **not** established. Deferred: explicitly quarantine private visibility without removing cohort members/history; verify no source calls/export of newly private records, and public recovery behavior. Do not broaden production token permissions before addressing this. |
| N2 | P2, proven operational coupling; policy decision | `.github/workflows/ci.yml:69` invokes reviewer evidence audit; `scripts/audit_reviewer_evidence.py:24` rejects empty current verified cohort. A real stored snapshot evaluated at generation +24h is all stale and raises the expected error. `.venv/test_final_review_boundaries.py`: **1 passed**, confirms boundary. | Reproducibility/quality checks depend on current data freshness. A delayed refresh can fail a code-only PR despite unchanged correct calculations. Not a false-data defect or F1–F12 regression. Keep strict validation; owner must choose whether freshness remains a blocking gate or separate reproducibility and operational checks. Do not change timestamps/data merely to pass. |

No new P0/P1 or P3 defect was substantiated. Previously documented PostgreSQL migration, first-refresh cache pressure, Streamlit deprecation and retired CLI parsing remain existing limitations, not newly counted findings.

### Integration and purpose assessment

| Area | Evidence / bounded conclusion |
|---|---|
| Collector/API | F1–F12 diff retains bounded calls, pagination and truthful partial states; earlier reviewer corrections have regression coverage. N1 is the additional visibility boundary. Legacy cache revalidation can consume extra quota; no justification to loosen coverage. |
| Dataset / Verified | Pinned 50 and six dataset hashes unchanged. Event history and full-open inventory remain separate. Historical 33/50 versus 50/50 explanation accepted; no policy or denominator change. |
| SQL/KPI / restore | Prior actual snapshot SQLite restore and exact ID/count/KPI parity retained as valid evidence; no SQL/metric code changed in this final audit. Fresh PostgreSQL DDL is tested, existing live migration is not. |
| Snapshot / workflow writers | Publication checks main data baseline before every retry. Gallery replay writes docs/gallery only; no new cross-writer data overwrite path established. Promotion jobs refuse writes; candidate audits and optional PG sync do not publish the snapshot. |
| Refresh / scheduler / Cloudflare | Local guards and source-proof tests remain valid. Four-hour rescue is a threshold under hourly scheduling, not a completion SLA. Missing native slots, cloud credentials, actual dispatches and production publication require dated operational receipts. N2 can block CI during stale-data periods. |
| Security | Read-only collector API and UI escaping/URL restrictions inspected alongside prior security tests. N1 limits the public-data guarantee with privileged tokens. No live vulnerability-database scan was run; pip compatibility is not a CVE clearance. No new dependencies or credential inspection were needed. |
| Six-page Streamlit | Prior actual-snapshot six-route AppTest passed with network blocked; application/UI unchanged in this audit. This proves rendering, not human comprehension, mobile/browser behavior in every environment or public hosting. |
| Data Analyst purpose | Cohort selection bias, source-specific eligibility, nulls instead of false zeros, SQL lineage and linked findings support a descriptive analytics portfolio. Data does not establish delivery deadlines, customer outcomes, SLA, quality scores or causal conclusions. |
| HR/nontechnical purpose | README and reader guide define Issues/PR/CI/Verified and distinguish observed activity from employee performance. Six-page navigation and direct evidence help review; no human usability study exists, so ease of understanding is not empirically certified. The project name can still be misconstrued as client-delivery tracking; preserve explicit scope wording in demonstrations/CV. |
| Technical users / documentation | Checkpoints, source links and local tests support reproducibility. Dependency ranges are not a lockfile, PostgreSQL is optional, and historical production evidence must remain dated. Avoid presenting local fixes as already deployed. |

### Verification record (no redundant full regression)

- Reused unchanged-code evidence: **539 Python tests**, **19 Cloudflare/Node tests**, real-snapshot restore/SQL parity and **six real-snapshot Streamlit routes**. Read the existing logs again; did not rerun these expensive checks without a code change.
- New focused evidence: one CI-age boundary test passed in 2.04s; independent private-visibility probe reproduced in-memory and was rerun once by primary to verify the reviewer's claim. Both use original read-only snapshot or synthetic fixtures, never altered production data.
- Final guard checks: six of six original dataset SHA-256 hashes unchanged; branch audit-menyeluruh and HEAD b893c04b14e0ae4d745218ec35ea83b728530f9d retained; git diff --check clean.
- Only this final-review document and ignored `.venv` probe/evidence files were added during final audit; existing remediation changes remain uncommitted. No commit, push, merge, deployment or actual Cloudflare action.

### Merge decision and blockers

**CONDITIONAL**: local remediation has no newly demonstrated P0/P1 blocker, but merge readiness is conditional on accepting/documenting the P2 boundaries and reviewing actual PR checks. If current evidence CI fails because data is stale, that is an operational merge blocker until an authorized real refresh or an owner-approved CI policy decision—not permission to weaken validation.

1. Keep the public publisher on its current scoped token; private-capable/PAT collection requires N1 resolution before being advertised or used as public-only ingestion.
2. Require actual PR quality checks. Do not substitute historical 539/19 passes for a current hosted CI result, or manufacture freshness to bypass N2.
3. Before deploying to existing PostgreSQL, review/execute its BIGINT migration separately. Before first refreshed collection, account for bounded legacy cache revalidation.
4. Rollout remains separately authorized. Afterwards obtain actual native slot, rescue dispatch, collector source/inventory and published snapshot receipts before claiming operational reliability.

No further authorized P0/P1 implementation remains. Production reliability, current remote CI status, public hosting, live PostgreSQL and latest dependency vulnerabilities are **not verified** in this local audit.

## N1/N2 remediation — authorized follow-up, 19 November 2026

- Scope updated by owner: implement N1 visibility quarantine and N2 reproducible quality versus operational freshness, TDD then independent review/full regression. No audit F1–F12 restart.
- N1 RED: 6 tests reproduced collection of private/internal metadata, missing persistent quarantine and no positive recovery. After collection fix, 3 remaining export tests still RED, proving missing export boundary separately. GREEN: 23 visibility/sync/snapshot/inventory tests passed.
- N1 implementation: additive `public_visibility` SyncCheckpoint (no schema migration or metric formula change); private/internal suspends all normal/backlog source calls. Unknown metadata cannot release existing quarantine. Explicit public response releases visibility state. Report carries checkpoint to central snapshot exporter, which rejects the entire export before touching files, preserving 50 members and local history. Actual datasets untouched.
- N2 next: evaluate reproducible reviewer evidence at the stored capture instant with explicit labelled output; keep current-time operational validation separate and failing on stale evidence. No timestamp editing, Verified override, or default dashboard clock change.

- N2 RED: API lacked reproducible mode and workflow separation (2 tests failed). GREEN: 15 targeted evidence/findings/case-study/CV tests passed. CI passes --reproducible, evaluates original capture instant consistently through findings and executive summary, and labels receipt historical/non-operational. Publisher explicitly passes --require-fresh at wall-clock time; snapshot staleness and current verified cohort remain enforced. No SQL/KPI formula, stored timestamps, dashboard default clock or Verified statuses are overridden.
- Initial full regression before reviewer correction: 547 passed in 66.72s; Node 19 passed. Independent reviewer found N1 quarantine could disappear when ephemeral runner restores preceding public snapshot. Two fresh-run unknown-visibility tests reproduced RED.
- Review correction: every collection run now requires positive public visibility, not merely absence of previous quarantine. Metadata absence/error records failed public_visibility and blocks export, including after restoring an older complete visibility checkpoint. Existing synthetic sync clients now provide explicit public metadata, and maintenance mocks represent successful metadata validation; assertions were retained. This deliberately supersedes permissive transient-metadata handling because rejected snapshots cannot persist quarantine to the next runner. Cost: metadata outages delay refresh while history/cohort remain intact.
- Expanded restore-cycle regression verifies private -> rejected export -> fresh SQLite restored from older public snapshot -> metadata outage -> no source calls / no export. Focused N1/N2: 11 passed. Final full regression after this correction still pending.


## N1/N2 final checkpoint ? 19 November 2026

This section supersedes the earlier deferral of N1/N2. Both are now **fixed locally** under the owner's follow-up authorization.

| Item | Final evidence |
|---|---|
| N1 | Private/internal/unknown visibility suspends collection and export; positive public proof required every run. Original history/cohort retained. Persistent and ephemeral restore paths tested. |
| N2 | Reproducible audit evaluates unchanged evidence at original generated_at, consistently propagated through eligibility/findings; receipt explicitly denies operational freshness. Operational publisher uses current time, rejects stale snapshot and empty qualified cohort. No timestamp rewrite or Verified override. |
| Independent review | One new N1 ephemeral-restore bypass found, reproduced RED, then fixed with strict per-run public proof and failed visibility marker on unknown metadata. Full suite after correction green; no second review substituted for testing. No additional N2 finding. |
| Full Python regression | **550 passed in 64.81s, exit 0**, `.venv/n1-n2-final-full.log`. Includes publication retry/stale-HEAD fixtures, scheduler/P0 guards, SQL/KPI, restore and AppTests. |
| Cloudflare / Node | **19 passed, exit 0**, `.venv/n1-n2-node.log`; Worker unchanged by N1/N2. |
| Real snapshot restore / SQL | **Passed**, `.venv/n1-n2-restore.log`: 50 repositories; 5,463 Issues / 6,177 PRs / 52,072 CI runs; exact IDs and SQL/KPI flags/counts preserved; repeat restore idempotent; loader 6 SELECTs. |
| Real snapshot Streamlit | All six routes passed with network requests prohibited; exit 0, `.venv/n1-n2-real-apptest.log`. |
| CLI integration | In ignored .venv working directory: --reproducible exit 0; --require-fresh exit 1 with explicit stale-snapshot assertion, as expected for unchanged aged data. No public files written. |
| Dataset / branch | All six original hashes unchanged, no actual data diff; audit-menyeluruh / b893c04b14e0ae4d745218ec35ea83b728530f9d retained. git diff --check clean. |

At the new read-only probe instant **19 November 2026 03:16:44 WIB** (2026-11-18T20:16:44Z), the unchanged snapshot correctly yields **0/50 currently joint Verified and 0/50 fresh full-open inventories**. Historical capture-time evaluation remains 50/50 for both. This is expected expiry, not data loss, a metric change, or proof of the remote production state. The current operational gate correctly refuses publication of that stale local evidence.

Files changed for N1/N2 only:
- `src/collectors/sync.py`: public-visibility proof/quarantine, including independent backlog candidates.
- `src/analytics/read.py`: carry additive visibility checkpoint, preserving metric calculations and batched SQL queries.
- `src/analytics/snapshot.py`: reject quarantined public export before touching output.
- `src/analytics/findings.py`: optional explicit evaluation clock; default UI behavior and formulas retained.
- `scripts/audit_reviewer_evidence.py`: labelled reproducible/current modes and strict current freshness check.
- `.github/workflows/ci.yml`, `.github/workflows/public-snapshot.yml`: separate mode invocations.
- `tests/test_visibility_quarantine.py`, `tests/test_reproducible_evidence.py`: new regressions; existing sync/integration/scale75/inventory/maintenance fixtures now provide valid public metadata without removing assertions.
- `docs/REPRODUCIBILITY.md` and this checkpoint: mode/visibility contracts and evidence.

**Merge status: CONDITIONAL on actual hosted CI and normal diff review; N1/N2 local implementation and verification are complete.** No demonstrated local P0/P1 blocker remains. This is not production rollout approval. The stale local dataset is not changed merely to pass a freshness gate; refresh must be an authorized real collection. Existing PostgreSQL BIGINT migration, real native/rescue schedule receipts, hosting and current dependency vulnerability evidence remain separate unverified prerequisites where applicable.

Tradeoff explicitly accepted within N1's authorized fix: transient/unknown metadata now blocks refresh rather than allowing collection with an old public checkpoint. A known private member blocks the entire export, not automatic membership removal. Changing that cohort remains an owner decision.

No commit, push, merge, deploy, actual dataset rewrite or Cloudflare production modification. Probe scripts/logs/receipts remain in ignored .venv; disposable restore databases were removed. No further N1/N2 work is pending locally.
