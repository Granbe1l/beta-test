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
each calendar day is checked; a capped day remains unverified. Recent
verified days are reused only for 24 hours, and older completed
creation-date buckets can be reused to save GitHub requests. Source
completeness requires the requested interval to be fully covered.

The collector prioritizes stale previously-complete sources, keeps
partials in the fair rotation, and rotates Issues/PR/CI ordering across
six-hour slots. Existing SQLite/PostgreSQL installations receive an
additive JSON checkpoint-column migration.

Real 75-repository load/analysis benchmarks appear in GitHub Actions
summaries, and screenshot browser checks are triggered after successfully
published source refreshes. These checks do not prove exact six-hour
punctuality, 100% lifetime data completeness, or public app uptime.
