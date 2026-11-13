# Project Delivery Monitor — current implementation and remaining evidence

Updated: **13 November 2026**. Repository: `Granbe1l/beta-test`. The
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
| Six-hour scheduled refresh | Workflow configured for `27 */6 * * *` UTC; run timings can be delayed |
| Measured schedule-reliability check | Implemented: only actual cron events count, with three successful successive runs needed to verify reliability |
| Automated tests, snapshot benchmark and screenshot capture | Implemented; see [GitHub Actions](https://github.com/Granbe1l/beta-test/actions) for the latest passing test count |
| Public hosted Streamlit URL | **Not verified** |
| Real nontechnical participant usability testing | **Not conducted**. Test procedure exists in `docs/REVIEWER_USABILITY_CHECK.md` |

## Latest audited source coverage

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
   near the intended six-hour cadence. Green push/PR runs are not evidence
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
Actions attempts refresh every six hours, but the dashboard reads a stored
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
