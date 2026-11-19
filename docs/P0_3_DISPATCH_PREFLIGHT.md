# P0.3 — independent scheduler decision and late-dispatch safety

> Current policy at baseline `b893c04` (18 November 2026): both watchdogs
> request a four-hour target; the dispatch input still defaults to six hours
> for manual non-forced rescue. The dated six-hour Cloudflare descriptions
> below describe the earlier proposal, not current source configuration.
> Audit remediation additionally requires main-only publication, an unchanged
> committed data baseline on every retry, and existing pinned-50 provenance.
> Legacy promotion workflows refuse cohort replacement; migration needs owner approval.
> These local remediation changes have not been deployed.

Dated 17 November 2026. **Code changes in this PR are GitHub-only.**
Cloudflare Worker code, Wrangler configuration, Cloudflare production/credentials,
curated 50 repository manifest and published data are **not modified**.

## What is actually implemented now

A `dispatch-preflight` job executes inside the existing
`public-snapshot-main` workflow concurrency gate, immediately before the
costly `refresh` job. For a `workflow_dispatch` rescue, it fetches **the
current `main` Git tree** (not the commit SHA from when the request first
entered a delayed queue), reads only the first bytes of the current committed
compressed snapshot, and checks its `generated_at` UTC timestamp.

- **Age at most 6 hours:** leave the costly `refresh` job skipped because
  another collector has already published recently. Preserve the explicit
  `collector-dispatch-preflight` receipt; never pretend a source scan ran.
- **Age greater than 6 hours:** proceed with the existing audited, 50-repository
  collector and its strict publication checks.
- **Native `schedule` or workflow-file `push`:** ALWAYS run the collector
  and require full source artifacts. Thus a successful rescue or a skipped
  dispatch never counts as native 4-hour cron delivery.
- **Explicit operator `workflow_dispatch` input `force_refresh: true`:**
  allow an intentionally requested new collection, including when the last
  snapshot is fresh. The Cloudflare and GitHub watchdog API calls already
  omit inputs and therefore do not set this override.
- **Unfetchable, invalid or future-dated snapshot:** preflight fails and logs
  the failed run instead of guessing freshness, triggering repeated collection,
  or silently declaring a green refresh. Operator can examine the failure
  before using the explicit override if recovery is appropriate.

All source checks, GitHub collector cron
`23 1,5,9,13,17,21 * * *` (UTC), 850 API request bound, 12-hour
checkpoint freshness, strict 28-day source coverage, and 50 separate full-open
Issue inventories remain unchanged. The existing 6-hour Cloudflare rescue,
90-minute dispatch backoff and 120-minute abandoned queue guard are unchanged.
**No new external trigger has been activated in this PR.**

## Risk remaining (do not overclaim)

This preflight makes an *accepted, serialized, delayed* rescue **less likely to
recollect unnecessarily after a fresh publication**. It does NOT provide an
atomic cross-provider lock, prevent two GitHub `workflow_dispatch` requests
from both being accepted, ensure the provider executes pending workflows, or
turn GitHub's best-effort 4-hour native schedule into a guaranteed schedule.
GitHub concurrency may replace a pending entry; the second entry cannot be
treated as an independent guaranteed recovery.

There is also a small interval between preflight reading `main` and starting
the actual collector. Repository workflow-level concurrency limits another
collector using this same group, but an unrelated actor could still publish a
snapshot. This guard is therefore defense in depth, **not exact-once semantics**.

The `dispatch-preflight` artifact captures `should_collect`, reason,
trigger, latest snapshot timestamp and age when relevant. A skipped
`workflow_dispatch` will have a *skipped refresh job*, so any report that
counts a green workflow without a real source artifact as successful ingestion
is invalid.

## Decision required for independent 4-hour refresh

The user's target **approximately four-hour operational freshness** and native
GitHub **on-time cron delivery** are separate measurements.

1. First prove this GitHub-only late-dispatch safety in a PR and a real
   workflow run (preflight for `push` and actual 50/50 collector).
2. Audit the exact four-hour cron slots honestly. Do not erase missed slots
   because a `push` or Cloudflare rescue published a fresh snapshot.
3. If the owner decides an independent 4-hour target is necessary, design
   and separately test a Cloudflare change using the already hourly trigger
   and a **4-hour target / 6-hour emergency fallback**, with source of truth
   `generated_at`, active/pending job guards, backoff, API error fail-closed
   behavior, and queue/race regression tests.
4. That prospective Cloudflare change requires an explicit separate
   production deployment by the account owner with secret/permissions check,
   rollback and dated logs. **Nothing in this PR deploys Cloudflare.**
5. Only declare *operational freshness* passed from actual dispatch -> run
   -> validated 50/50 source artifact -> committed publication observations.
   GitHub native schedule requires separate real, on-slot `event=schedule`
   evidence and cannot be promised by changing its cron expression.

## Evidence and rollback

Tests must cover fresh/stale six-hour boundary, missing/invalid timestamps,
a 53-minute queued rescue that became unnecessary, two accepted requests in
sequence, explicit manual override, and schedule/push preservation. All
existing Python, Cloudflare test-only, snapshot and SQL integrity checks
must remain passing. Merge only after CI and reviewer check.

If new preflight suppresses a needed rescue, inspect its dated receipt,
current main snapshot, and input context first. Revert the reviewed commit to
restore the previous workflow behavior. Keep the currently committed snapshot
and curated cohort intact throughout; do not revert or fabricate dataset
observations to make a workflow appear successful.


## 17 November 2026 — GH-only early 4h target (Cloudflare still 6h)

**Observed incident:** native collector scheduled for 08:23 WIB was not observed
by 10:37 WIB. The GitHub-only watchdog itself ran at 09:37 WIB and
reported `skip / snapshot_fresh` because the last valid snapshot at 05:54
was 3.72h old against its *former* 6h age policy. That is not proof
Cloudflare was unhealthy: its independent rescue still uses 6h.

This separate GitHub-only change makes the existing *best-effort*
GitHub watchdog check at **snapshot age >4 hours** instead of >6h.
It dispatches `public-snapshot.yml` with the explicit GitHub
`workflow_dispatch` input `target_hours: '4'`. The collector's
post-queue preflight interprets **only the accepted targets 4 or 6**:

- GitHub watchdog sends `target_hours='4'`, meaning it may start costly
  data collection after actual age passes 4h and existing pending-run,
  active-run, and 90-minute backoff checks allow it.
- Existing Cloudflare Worker dispatches **without inputs** and therefore
  retains the **default target 6h** and exact original production code,
  hourly cron, token, and configuration.
- Regular native `schedule` and workflow-file `push` still collect,
  preserving their independent source and punctuality audits.
- The initial preflight still fetches newest main snapshot *after*
  a queued rescue is admitted; a newly published fresh snapshot skips
  redundant heavy collection with an explicit auditable receipt.
- Explicit operator `force_refresh:true` still requires a deliberate
  manual choice. Unsupported targets are rejected rather than allowing
  arbitrary 1-hour repeat dispatch spam.

**This is not two contradictory freshness metrics:** the 4h threshold is
the **same-provider early recovery target**, whereas 6h remains the
**independent Cloudflare fallback**. The GitHub watchdog itself depends
on best-effort GitHub scheduled workflow delivery. As a result, neither
this change nor another green push run proves *4h punctuality*. When
Github Action cron delivery is absent, the Cloudflare fallback
continues as-is. Current data remains the same pinned 50 repos and
unchanged 28-day/12-hour correctness gates.

Before accepting this change, require green PR CI, tests for 4/6h
boundary and API errors, a real main collector scan with 50/50 source
artifacts and publication, and a real `workflow_run` watchdog decision.
Cloudflare production must not be redeployed or modified. A subsequent
GH watchdog *scheduled* execution after >4h of snapshot age is useful
operational evidence but not a guarantee for future slots.
