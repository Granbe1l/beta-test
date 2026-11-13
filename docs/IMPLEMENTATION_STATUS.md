# Project Delivery Monitor — current implementation and remaining evidence

Updated: **14 November 2026**. Repository: `Granbe1l/beta-test`. The
repository has **75 curated public GitHub projects**. Changes must pass PR
quality checks before merging to `main`.

## Implemented

| Capability | State and verification |
| --- | --- |
| Six visual Streamlit screens, purple/white theme, real-data Plotly charts | Implemented; browser desktop/mobile screenshots succeeded in main run [43338398246](https://github.com/Granbe1l/beta-test/actions/runs/43338398246) |
| 75 retained public GitHub repositories | Verified in snapshot audit [43342299579](https://github.com/Granbe1l/beta-test/actions/runs/43342299579) |
| Issues / PR / GitHub Actions collector, SQLAlchemy and SQLite | Implemented; records are real but **per-source coverage is partial** |
| Efficient 28-day bootstrap and 7/1-day capped fallback | Implemented on main; latest observed coverage improved modestly |
| Current-UTC-day CI verification | Implemented and regression-tested; previous current-day checkpoint cannot certify newly elapsed hours |
| Verified/exploratory 7/28-day activity lines | Implemented; denominators are source-specific |
| Source-linked inspection findings and examples | Implemented with real GitHub Issue, PR and CI run URLs |
| Separate oldest-first current open-Issue inventory | Implemented and regression-tested; scheduled refresh will use leftover API budget. A partial inventory never claims full backlog coverage |
| Observation-method comparability | Legacy, updated-event sample and verified open-inventory snapshots are tagged; incomparable periods must not show false growth |
| Per-repository source coverage diagnosis | Implemented; distinguishes page caps, stale scans and short fallback windows in workflow audit |
| Nontechnical three-part executive readout | Implemented: activity, source-linked recommended inspection, confidence |
| SQL CTE analysis and source verification flags | Implemented; real snapshot SQL audit passed on main [43338398122](https://github.com/Granbe1l/beta-test/actions/runs/43338398122) |
| Four-hour scheduled refresh (beta PR) | Workflow configured for `17 1,5,9,13,17,21 * * *` UTC; scheduling remains best-effort |
| Measured schedule-reliability check | Implemented: only actual cron events count, with three successful successive runs needed to verify reliability |
| Automated tests, snapshot benchmark and screenshot capture | Implemented; see [GitHub Actions](https://github.com/Granbe1l/beta-test/actions) for the latest passing test count |
| Public hosted Streamlit URL | **Not verified** |
| Real nontechnical participant usability testing | **Not conducted**. Test procedure exists in `docs/REVIEWER_USABILITY_CHECK.md` |

## Historical audited source coverage

**Historical numbers below are from 13 November at 02:10 UTC, not the current 75-repo verified intersection.** For current beta refresh cadence and proof gates, see [refresh stability](REFRESH_STABILITY.md) and the latest `data/verified_cohort_change_receipt.json`.

The latest published audited snapshot evaluated in this review was generated
**2026-11-13 02:10 UTC** (**2026-11-13 09:10 WIB**):

| Source | Persisted observations | Verified complete 28-day windows |
| --- | ---: | ---: |
| GitHub Issues | 12,557 | 43 / 75 |
| Pull requests | 26,549 | 53 / 75 |
| GitHub Actions runs | 94,573 | 38 / 75 |

These are **actual** audit figures from [snapshot run
43347576175](https://github.com/Granbe1l/beta-test/actions/runs/43347576175),
not target values. Changes to data collection **do not establish better
coverage until a subsequent real run and before/after audit prove it**.

`complete` only means the particular bounded endpoint scan finished;
it does not prove total project backlog, private milestones, software
quality, SLA adherence, or employee productivity. Older unmodified issues
can be absent from recent-update API sampling.

## Work that is not yet proven

1. **Data completeness:** actual 28-day coverage remains partial at
   43/75 Issues, 53/75 PR and 38/75 CI in the latest audited refresh.
   Recheck the new independent open-inventory source after its first
   scheduled run and retain full source audit artifacts.
   Very busy repositories may remain capped.
2. **Scheduling:** accumulate at least three successful `schedule` events
   near the intended four-hour cadence. Green push/PR runs are not evidence
   of actual scheduled delivery.
3. **Human comprehension:** conduct the five-minute anonymous user tasks.
   Automated screenshots and textual checks cannot substitute for people.
4. **Public URL:** owner may deploy `streamlit_app.py` and then run the
   dedicated public website verifier; do not claim a deployed app yet.
5. **Manual coverage review:** audit headline copy/period and denominator
   against several repository-level original GitHub records.

## Preferred technical explanation for interviews

GitHub REST API → bounded, source-aware collector → SQLAlchemy/SQLite
checkpoint persistence and upserts → audited compressed GitHub snapshot →
Streamlit/Plotly visual evidence. Additional handwritten SQL CTE queries
summarize observed Issues/PR/CI while avoiding join multiplication. GitHub
Actions attempts refresh every four hours, but the dashboard reads a stored
snapshot and does not request fresh records on every page visit.

The app describes **observable open-source engineering activity**. It is
*not* a monitoring system for private client delivery deadlines. This
boundary is explicit in the new HRD executive summary.

## CV-ready verified cohort without waiting

The app has separate, **strict same-project** cohort filters for complete
7-day and 28-day history across all three Issues, PR and CI source types.
The period describes **existing historical data**; a 28-day countdown is
not required. Partial sources remain accessible as exploratory data,
and neither exploratory nor source-specific cohorts should be described
as "all 75 verified".

`python scripts/cv_evidence.py` emits a reproducible receipt from the
real committed snapshot, including the matching 7/28-day cohort sizes,
the source-specific verified denominators, and the stored record counts
with timestamp. The sample can therefore be shown to recruiters with
honest qualifiers **before full 75/75 coverage**.

The independent historical open-Issue inventory remains separately
tracked. Passing tests and successful refreshes cannot substitute for
a genuine audit of its remaining incomplete repositories. Read
[CV evidence wording](CV_EVIDENCE.md) for ATS-safe descriptions.

## Current P0 verified-first implementation and audit gates

The latest 13 November snapshot includes **35/75** repositories with
all three Issues/PR/CI sources verified for the **same** 28-day period.
The dashboard now defaults to this verified 28-day cohort (7-day
verified fallback if needed), while all tracked projects remain available
as explicitly exploratory data. The candidate discovery and 28-day
verification process is read-only, and **does not silently replace or
delete existing repositories**. See [P0 verified-first protocol](P0_VERIFIED_FIRST.md).

From the latest actual API refresh, **7/75** independently exhausted
current open-Issue inventories; one additional source was partial and
67 had no completed standalone inventory scan. This is NOT the
same denominator as 43/75 Issues with complete 28-day recent events.
The next backlog audit prioritizes verified cohort repositories and
uses a capped created-time search sharding fallback on oversized lists.

P0.3 now exposes a sample-specific age share separately from
\`aged_percent\`, which requires a complete current open inventory.
Historical net backlog changes require two independently verified
full inventories for identical repositories; incomplete observed
PR backlogs are not charted as confirmed changes.

The independent candidate and backlog Search API improvements need
fresh real workflow audits after merge before changes in coverage
can be asserted. Do not claim the verified cohort rose, candidate
replacements succeeded, or all old Issues were collected without
a real new artifact.

## P0 integrity follow-up

GitHub Issues REST `since` filters **last-updated records**, not the full
set of outstanding Issues. The new source `open_backlog` independently
queries `state=open`, oldest first, **without `since`** and excludes PR
objects returned by the Issues API. An exhausted paginated scan can be
marked complete at collection time; capped scans remain partial. The
extra work uses only available REST request budget after primary source
collection. No fabricated closed timestamp is generated for items that
disappear from a complete open inventory; their status is marked
`not_confirmed_open` pending a normal updated-event fetch.

A separate `collection_basis` is persisted with open-work
observations. Cross-period charts must not interpret a jump from
`sampled_updated_events` to `verified_open_inventory` as newly created
work. No score increase is claimed until the new collector and source
audit pass on actual scheduled data.

## P0 completion evidence — 13 November 2026

- **P0.1 Verified-first:** all six Streamlit pages default to matching
  28-day Issue/PR/CI source coverage. Latest published **matching cohort
  35 of the 75** curated public repositories. The remaining tracked
  repositories are retained as opt-in exploratory evidence; they were not
  deleted or silently counted as inactive.
- **Replacement candidates:** the independent [second live candidate audit
  43357638162](https://github.com/Granbe1l/beta-test/actions/runs/43357638162)
  found 32 and tested 8 candidates with GitHub REST API, verifying
  **3**. Two category/size matched substitution proposals were
  generated, but **no swaps were applied**. Candidate checks now rotate
  daily with their own budget. A matching language or star tier alone is
  insufficient to remove a materially different original project.
- **P0.2 full-open Issue inventory:** the first real refresh
  [43347576175](https://github.com/Granbe1l/beta-test/actions/runs/43347576175)
  verified **7 complete** full-open inventories, recorded one
  oversized partial inventory and left 67 unvisited. Created-date
  Search shards are bounded by a separate request limit and never certify
  a truncated response.
- **P0.3 integrity:** an additional CI gate compares restored real
  SQLite SQL counts, original compressed-snapshot records and Python
  Streamlit metrics, including per-repository IDs, source completeness,
  old open Issues, 28-day PR/CI totals and verified backlog flags.
  Mismatches must fail CI rather than become impressive portfolio numbers.

**Remaining evidence:** 75/75 matching three-source history has not been
verified. Project selection is curated, not a statistically random sample.
Real-user HRD comprehension and the public hosted Streamlit URL are
also not independently established.

## P1 implementation and operational evidence

- **P1.1**: findings contain a quantified trigger, source URL or
  explicit listing fallback, a structured three-step inspection,
  clear limitations and a CSV reviewer export.
  [PR #10](https://github.com/Granbe1l/beta-test/pull/10) passed
  code, SQL/real-snapshot and rendered desktop/mobile browser tests.
- **P1.2**: all six pages expose a collapsed, one-minute glossary,
  navigation tooltips and an explicit explanation of Verified
  versus Exploratory data.
  [PR #11](https://github.com/Granbe1l/beta-test/pull/11) passed
  automated and browser rendering checks.
  **The real 3–5-participant usability evaluation has not happened.**
  The form in `docs/REVIEWER_RESULT_FORM.csv` is blank on purpose.
- **P1.3**: scheduled-run audit now requires both plausible spacing
  among three actual `schedule`-triggered successful runs **and a
  recent latest run**. A machine-readable proof is saved with the
  source audit. A push/manual run cannot substitute for a cron run.
  The last audit established only **two** actual scheduled successes,
  so reliability **must remain unverified** until real schedule history
  satisfies the gate.

The main application is CV-usable without reporting 100% source
coverage, guaranteed four-hour runtime, or invented HRD testing.


## P1.3 follow-up: avoid auditing an unfinished schedule

The GitHub Actions workflow `public-snapshot.yml` previously queried its
own `schedule` history **before** the current refresh had completed. Its
most recent `schedule` run could therefore still be `in_progress`, which
cannot honestly count as a successful refresh. Testing or rescheduling
manually does not correct that evidence problem.

The independent read-only workflow
[`schedule-audit.yml`](../.github/workflows/schedule-audit.yml) now runs
on `workflow_run: completed` for the actual ingestion workflow. It filters
the trigger to **real schedule events** and writes a dated
`schedule-reliability.json` GitHub Actions artifact. The standalone
one-time baseline (`push`/manual audit) is an inspection, **not a fabricated
scheduled cycle**. The auditor still requires three successive successful
real `schedule` runs, plausible 3–6.5 hour intervals, and a recent last run
before reporting `verified_recent_cycles`.

**What this fixes:** false-negative self-auditing of an unfinished run;
machine-readable evidence linked to an actual completed GitHub event.

**What this does not fix:** GitHub's best-effort cron scheduling itself.
GitHub states a scheduled workflow can be delayed or dropped under high
load, including at the top of the hour. The current cron is already off
the hour (`17 1,5,9,13,17,21 * * *` UTC). Shifting the minute has no proven ability
to repair missing events, and the audit must not be relaxed to make gaps
pass.

**If four-hour operational freshness is business-critical:** introduce
an independent managed scheduler (for example a GCP Cloud Scheduler job)
that sends an authenticated `workflow_dispatch` to this existing ingestion
workflow using a least-privilege credential held as a secret in the
scheduler, with retry/backoff and duplicate-run protection. Owner
authorization/configuration is required. Record separate
`scheduled_native` and `external_dispatch` trigger methods, compare
actual publish times to the four-hour freshness SLO, and only describe
reliability once sufficient **real** external scheduled runs have
succeeded. External dispatches must NEVER be relabeled as GitHub
`schedule` events.

For CV use prior to such operational evidence, say *"configured four-hour
GitHub Actions refresh with verified collection and source-level audits"*,
not *"guaranteed automatic refresh every four hours"*.
