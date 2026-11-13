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
**2026-11-13 01:27 UTC** (**2026-11-13 08:27 WIB**):

| Source | Persisted observations | Verified complete 28-day windows |
| --- | ---: | ---: |
| GitHub Issues | 11,652 | 40 / 75 |
| Pull requests | 26,450 | 50 / 75 |
| GitHub Actions runs | 87,122 | 35 / 75 |

These are **actual** audit figures from [snapshot run
43328904930](https://github.com/Granbe1l/beta-test/actions/runs/43328904930),
not target values. Changes to data collection **do not establish better
coverage until a subsequent real run and before/after audit prove it**.

`complete` only means the particular bounded endpoint scan finished;
it does not prove total project backlog, private milestones, software
quality, SLA adherence, or employee productivity. Older unmodified issues
can be absent from recent-update API sampling.

## Work that is not yet proven

1. **Data completeness:** actual 28-day coverage remains partial at
   40/75 Issues, 50/75 PR and 35/75 CI in the latest audited refresh.
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
