# Verified 28-day refresh stability (beta)

Updated 14 November 2026. This is a plan and auditable implementation, not
proof that 50/75 is stable or that GitHub Actions always fires on time.

## Acceptance criteria

- Keep exactly 75 actively curated repository identities. Existing archived
  evidence is not silently deleted. The 28-day Issues/PR/CI source intersection
  is the only `Verified 28d` count; shorter 1/7-day fallbacks never qualify.
- Keep the honest 12-hour freshness cutoff. A stale checkpoint can be
  refreshed to become Verified again, but must **not** be displayed as current
  while stale. Never relabel a partial scan as complete.
- Production snapshot cron: `17 1,5,9,13,17,21 * * *` (UTC), **every 4 hours**.
  Candidate source-audit cron: `23 3,15 * * *` (UTC), every 12 hours.
  The schedules are staggered to reduce API competition, but GitHub may still
  delay, skip, or overlap queued jobs. No time-of-day promise is made.
- GitHub's repository `GITHUB_TOKEN` typically has 1,000 REST requests/hour.
  Keep the bounded **850 API attempts** per primary run; candidate scans
  have a separate 850-attempt cap and run less often to avoid per-hour competition. Measure actual requests, 403/429 responses, run duration,
  and source completeness rather than assuming all 75 can be refreshed.
- Collector first renews three-source, full-28d repository checkpoints that
  will expire within four hours or are already stale; next it attempts
  repositories with two fully covered sources; then healthy Verified and
  exploratory repositories. Optional historical Issue/PR repair may **not**
  preempt urgent existing Verified maintenance.
- The existing watchdog still monitors committed snapshot age separately.
  A newly created snapshot does **not** imply all three sources were refreshed.

## Evidence before declaring reliable

1. Merge and observe at least **three actual successful scheduled runs**
   (not manually dispatched or triggered by a code push), with published
   before/after coverage-readiness JSON and 75 tracked IDs.
2. Record Verified 28-day joint cohort, individual source denominators,
   current open-Issue inventory, and timestamp for every run.
3. Flag regressions and prioritize their specific causes: staleness,
   pagination caps, API throttling, or errors; preserve truthful partial
   status and prior records.
4. Verify the GitHub-hosted Streamlit page reads the latest published
   snapshot and matches its timestamp and reported denominators.
5. Only say `>=50/75 stable` after actual consecutive scheduled-run evidence
   demonstrates it. A successful cron job alone proves neither coverage
   stability nor completeness of the lifetime backlog.

## Rollback

The original 6-hour cron was `27 */6 * * *`. If API utilization, scheduled
overlap, or update failures worsen, revert both cron entries and the
maintenance prioritization as a single reviewed change. Never roll back the
snapshot itself without preserving the current 75-repository data and audit.
