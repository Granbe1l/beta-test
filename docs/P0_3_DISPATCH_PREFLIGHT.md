# P0.3 — independent scheduler decision and late-dispatch safety

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
