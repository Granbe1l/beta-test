# Verified 28-day refresh stability (beta)

Updated 14 November 2026. This is a plan and auditable implementation, not
proof that 50/50 is stable or that GitHub Actions always fires on time.

## Acceptance criteria

- Keep exactly 50 reviewed, jointly Verified-at-selection repository identities. Existing archived
  evidence is not silently deleted. The 28-day Issues/PR/CI source intersection
  is the only `Verified 28d` count; shorter 1/7-day fallbacks never qualify.
- Keep the honest 12-hour freshness cutoff. A stale checkpoint can be
  refreshed to become Verified again, but must **not** be displayed as current
  while stale. Never relabel a partial scan as complete.
- Production snapshot cron: `23 1,5,9,13,17,21 * * *` (UTC), **every 4 hours**.
  Candidate audits are manual-only during the fixed 50-project maintenance period.
  The single recurring collector has more API headroom, but GitHub may still
  delay, skip, or overlap queued jobs. No time-of-day promise is made.
- GitHub's repository `GITHUB_TOKEN` typically has 1,000 REST requests/hour.
  Keep the bounded **850 API attempts** per primary run; candidate scans
  have a separate 850-attempt cap but run only when explicitly requested. Measure actual requests, 403/429 responses, run duration,
  and source completeness rather than assuming all 50 can be refreshed.
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
   before/after coverage-readiness JSON and 50 tracked IDs.
2. Record Verified 28-day joint cohort, individual source denominators,
   current open-Issue inventory, and timestamp for every run.
3. Flag regressions and prioritize their specific causes: staleness,
   pagination caps, API throttling, or errors; preserve truthful partial
   status and prior records.
4. Verify the GitHub-hosted Streamlit page reads the latest published
   snapshot and matches its timestamp and reported denominators.
5. Only say `50/50 stable` after actual consecutive scheduled-run evidence
   demonstrates it. A successful cron job alone proves neither coverage
   stability nor completeness of the lifetime backlog.

## Rollback

The original 6-hour cron was `27 */6 * * *`. If API utilization, scheduled
overlap, or update failures worsen, revert both cron entries and the
maintenance prioritization as a single reviewed change. Never roll back the
snapshot itself without preserving the current curated 50-repository data and audit.

## Missing schedule events: 14 November 2026 (dated observation)

At the audit around 17:35 WIB, the scheduled collection at 08:27 WIB had
completed successfully, but neither the expected 12:17 nor 16:17 WIB cron
trigger appeared in GitHub Actions' available workflow-run history. The
09:39 WIB `push`-triggered collection subsequently published a real 50/50
28-day Verified snapshot and 50/50 independently complete open-Issue
inventories. That push success does **not** count as an on-time cron cycle.
The hourly watchdog's last observed scheduled run was at 10:32 WIB; its
log skipped dispatch because the committed snapshot was only 0.88 hours old.
The precise reason for missing cron events is not proven. GitHub's official
documentation warns that scheduled events can be delayed or dropped.

Mitigation change: shift both cron expressions by six minutes to prompt
schedule re-registration while preserving the four-hour collection cadence;
also let a successful **main push** Quality Checks completion invoke the
existing conditional watchdog (which still dispatches only if the committed
snapshot is >8 hours old, no collector is underway, and the 90-minute
backoff has elapsed). This extra trigger is **not** a replacement for a
reliable independent scheduler, and neither the code change nor a manually
triggered refresh counts as three successful scheduled runs.

Source: https://docs.github.com/en/actions/how-tos/troubleshoot-workflows

## Backlog catch-up capacity after missed cron slots

The live 17:46 WIB run on 14 November retained all 50 Verified 28-day
source windows, but its independent open-Issue inventory queue held 33
pending repositories. The production cap of 25, not API exhaustion,
left eight stale with 573 unused requests. Permit up to 50 inventory
attempts on the production workflow only; retain the global 850-attempt
limit, per-repository paging/Search caps, source-first order and strict
freshness flags. This repairs capacity, **not** missing cron history;
verify a new real run before claiming 50/50 fresh open inventories.

## Verified catch-up after missing scheduled slots (17:54 WIB, 14 November 2026)

[The actual post-change collector](https://github.com/Granbe1l/beta-test/actions/runs/43587299217) reported 8 remaining full-open inventory gaps prior to maintenance and exhausted all eight: **50/50 fresh full-open Issue inventories** and independently **50/50 jointly Verified 28-day Issues, PR and CI sources**, with 633 API attempts remaining under the 850 limit. The run passed validation and published the snapshot. This proves that bounded catch-up capacity worked for one real run, not that every future refresh is timely. Three consecutive actual scheduled runs are still needed for schedule-reliability proof.
