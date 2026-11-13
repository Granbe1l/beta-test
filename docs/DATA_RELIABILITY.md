# Public GitHub data reliability — design and proof

## P0 objective

Keep exactly 75 curated repositories, collect real public GitHub records,
show source coverage by date window, and never report a no-work refresh as
successful. A bounded scan is not full GitHub lifetime history.

## Open-source references (architecture, not copied code)

- [CHAOSS GrimoireLab](https://github.com/chaoss/grimoirelab) and
  [GrimoireLab Perceval](https://github.com/chaoss/grimoirelab-perceval):
  incremental retrieval, source-specific state, idempotent records, and
  rate-limit-aware collection. This project uses a smaller SQLite version.
- [GrimoireLab Core](https://github.com/chaoss/grimoirelab-core):
  scheduling and resuming incremental source collection. This project
  rotates unfinished repositories without changing its fixed sample.
- [OSS Insight](https://github.com/pingcap/ossinsight):
  distinguishes historical GitHub event datasets from recent public
  events. GH Archive is a possible later historical supplement, not a
  substitute for repository Issues, PR and Actions data.
- [GitHub scheduled workflow troubleshooting](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows):
  scheduled jobs can be delayed or dropped, so a code test is not proof
  a real scheduled job ran.

These references supplied design patterns only. No third-party source code
or additional data have been copied into the project.

## Bounded collection

- Keep the 75 curated repository identities fixed for comparable cohorts.
- Prioritize never-scanned and incomplete repositories; save source-specific
  checkpoints in the compressed public snapshot between runs.
- Retrieve Issues/PRs using GitHub REST with a bounded page cap and honest
  fallback intervals: initial, 28, 7, then 1 day when necessary.
- For GitHub Actions, the REST API supports a server-side created date
  range. Partition recent scans by up-to-seven-day UTC intervals; when
  a week exceeds six pages, retry one day at a time. Aggregate by GitHub
  run ID to avoid duplicates. One incomplete interval makes the overall
  window partial, not complete.
- Limit requests per scheduled run. Missing/partial sources are never
  fabricated as zero event data.

## Publication evidence gate

The six-hour UTC cron and manual dispatch remain. A pipeline-workflow-only
push trigger permits testing actual data collection after changing that
workflow, without executing ingestion on every UI/code commit.

The workflow restores previous real data, audits its BEFORE coverage,
queries the GitHub API, audits AFTER coverage, uploads audit artifacts,
then checks consistency BEFORE publishing to main.

The gate requires:
- 75 unique, curated repository identities;
- nondecreasing persisted record counts;
- consistent per-source coverage denominators, all summing to 75;
- 28-day verified source counts no greater than complete bounded scans;
- at least one newly successful source checkpoint OR new persisted record.

A no-work attempt or lost source records causes failure without replacing
the previous published snapshot. A partially covered source remains
labelled partial, even when the overall workflow has succeeded.

## Proof and remaining limitations

Inspect GitHub Actions run event, logs, before/after JSON artifacts,
and the actual snapshot publication commit. Screenshots and green pytest
alone cannot prove a successful six-hour scheduled ingestion. Multiple
scheduled runs are needed before claiming operational reliability.

Very busy Issues/PRs may still reach the REST page cap even within
one day. Future improvements could use date-bucketed GitHub Search,
GraphQL cursor workers, or a separate GH Archive warehouse; these have
more API and maintenance cost. Data from such alternatives are NOT
presented as already collected.


## Date-window checkpoints and ongoing verification

CI/CD scans now record verified UTC creation-date buckets, plus the time
when each bucket was last scanned, in the source checkpoint JSON.
This information survives across GitHub Actions runners through the
compressed snapshot even when the full scan remains partial.

A complete weekly range certifies its dates. When a week is capped,
each calendar day is checked; a capped day remains unverified. Previously verified **closed** UTC calendar days may be reused for at
most 24 hours when recent, and older completed creation-date buckets can
be reused to save GitHub requests. The **current UTC day is always
rechecked through the current run time**, even if its last checkpoint was
verified a few hours ago. Source completeness requires the actual
requested interval to be fully covered.

The collector prioritizes stale previously-complete sources, keeps
partials in the fair rotation, and rotates Issues/PR/CI ordering across
six-hour slots. Existing SQLite/PostgreSQL installations receive an
additive JSON checkpoint-column migration.

Real 75-repository load/analysis benchmarks appear in GitHub Actions
summaries, and screenshot browser checks are triggered after successfully
published source refreshes. These checks do not prove exact six-hour
punctuality, 100% lifetime data completeness, or public app uptime.

## Current collection efficiency and independent schedule evidence

The initial bounded Issues/PR scan starts at the **exact 28-day analysis
window** rather than fetching a near-duplicate 30-day window first.
An explicit long history reconciliation still attempts the configured
backfill, with 28-, 7- and 1-day fallbacks when capped. This reduces
wasted REST pages but cannot guarantee 75/75 source completion.

Scheduled reliability is assessed by `scripts/schedule_reliability.py`.
It examines the most recent **three actual `schedule` events** on main
and their observed spacing. Workflow `push`/`workflow_dispatch`
successes are explicitly excluded, and missing history returns an
insufficient-evidence status rather than a positive reliability claim.
A green data pipeline and a fully verified 28-day dataset are separate
states.


## P0 integrity: current open backlog is a separate source

GitHub's REST `/repos/{owner}/{repo}/issues?since=...` uses the *last
updated* timestamp. It cannot establish the **entire current open backlog**
because an Issue created years ago may still be open without a recent
update.

The collector therefore has an independent `open_backlog` source. It
scans `state=open`, `sort=created`, `direction=asc` **without**
a `since` filter, excludes PR entries, and stores all retrieved genuine
Issue IDs. It only sets `open_backlog.status=complete` when the GitHub
pagination is exhausted. A capped query is saved as a **partial observed
inventory**, never represented as 100% coverage. An absent/stale scan is
not a zero-open-Issues claim.

All regular Issue/PR/CI event collection runs first. The backlog
collector uses **leftover GitHub API budget** and checks at most eight
visited repositories per refresh, rotating with the main collector's
repository order. It must not claim complete open inventory for
repositories where pages are still capped.

When a fully exhausted open-Issue scan does not return a historically
stored open item, the local record is marked
`not_confirmed_open` with **no invented closed_at timestamp**. A future
recent-update scan can supply the actual authoritative state and closing
timestamp. The original source URL/ID is never removed.

Snapshot history now stores `collection_basis`: legacy observed,
updated-event sample, or verified open-inventory. Only observations using
the same basis may be compared as net open-work change. A new complete
backlog scan may increase the displayed *observed* count because data
collection improved; such a change is **not** evidence of new work or a
missed deadline.

The validated 2026-11-13 08:27 WIB refresh showed verified full 28-day
windows of **40/75 Issues, 50/75 PRs and 35/75 CI sources**. These
numbers do not establish full backlog coverage. Later open-inventory
completeness must be measured from real audits; it cannot be inferred
from new code or test fixtures.

## P1 operational freshness of scheduled GitHub refresh

A successful `push` or `workflow_dispatch` run shows that GitHub
collection can execute. It does **not** prove that the six-hour cron
fires consistently. `scripts/schedule_reliability.py` requires all
of the following independent observations:

- At least **three actual `schedule` events** on `main`, each completed
  successfully, evaluated from the refresh workflow's real Actions history.
- Their consecutive observed start-time intervals must be between **3
  and 9 hours**, allowing real GitHub scheduler delay.
- **The newest scheduled event must be within 9 hours** of the audit time.
  Three successful events months ago never establish current health.

Results now include the most recent scheduled-run timestamp and age.
`verified_recent_cycles`, `stale_schedule`, `needs_review` and
`insufficient_history` must not be treated as equivalent. On every
actual refresh, the machine-readable `schedule-reliability.json` is
included with the snapshot source-audit artifact (when the GitHub
Actions history API can be reached).

The last verified public snapshot can be usable even when schedule
reliability is insufficient. Similarly, a recent snapshot can result
from a push/manual run. Neither establishes reliable 24/7 operation.
The current **three-cycle runtime claim remains unverified** until
three qualifying scheduled runs actually occur.
