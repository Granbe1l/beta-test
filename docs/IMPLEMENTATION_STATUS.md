# Project Delivery Monitor — current implementation and remaining evidence

Updated: **13 November 2026**. Repository: `Granbe1l/beta-test`. The
repository has **75 curated public GitHub projects**. Changes must pass PR
quality checks before merging to `main`.

## Implemented

| Capability | State and verification |
| --- | --- |
| Six visual Streamlit screens, purple/white theme, real-data Plotly charts | Implemented; browser desktop/mobile screenshots succeeded in main run [43338398246](https://github.com/Granbe1l/beta-test/actions/runs/43338398246) |
| 75 retained public GitHub repositories | Verified in snapshot audit [43328904930](https://github.com/Granbe1l/beta-test/actions/runs/43328904930) |
| Issues / PR / GitHub Actions collector, SQLAlchemy and SQLite | Implemented; records are real but **per-source coverage is partial** |
| Efficient 28-day bootstrap and 7/1-day capped fallback | Implemented on the current improvement branch; no fabricated backfill |
| Current-UTC-day CI verification | Implemented and regression-tested; previous current-day checkpoint cannot certify newly elapsed hours |
| Verified/exploratory 7/28-day activity lines | Implemented; denominators are source-specific |
| Source-linked inspection findings and examples | Implemented with real GitHub Issue, PR and CI run URLs |
| Nontechnical three-part executive readout | Implemented: activity, source-linked recommended inspection, confidence |
| SQL CTE analysis and source verification flags | Implemented; real snapshot SQL audit passed on main [43338398122](https://github.com/Granbe1l/beta-test/actions/runs/43338398122) |
| Six-hour scheduled refresh | Workflow configured for `27 */6 * * *` UTC; run timings can be delayed |
| Measured schedule-reliability check | Implemented: only actual cron events count, with three successful successive runs needed to verify reliability |
| Automated tests, snapshot benchmark and screenshot capture | Implemented; see [GitHub Actions](https://github.com/Granbe1l/beta-test/actions) for the latest passing test count |
| Public hosted Streamlit URL | **Not verified** |
| Real nontechnical participant usability testing | **Not conducted**. Test procedure exists in `docs/REVIEWER_USABILITY_CHECK.md` |

## Latest audited source coverage

The latest published audited snapshot evaluated in this review was generated
**2026-11-12 23:48 UTC** (**2026-11-13 06:48 WIB**):

| Source | Persisted observations | Verified complete 28-day windows |
| --- | ---: | ---: |
| GitHub Issues | 11,310 | 38 / 75 |
| Pull requests | 25,676 | 48 / 75 |
| GitHub Actions runs | 72,485 | 32 / 75 |

These are **actual** audit figures from [snapshot run
43328904930](https://github.com/Granbe1l/beta-test/actions/runs/43328904930),
not target values. Changes to data collection **do not establish better
coverage until a subsequent real run and before/after audit prove it**.

`complete` only means the particular bounded endpoint scan finished;
it does not prove total project backlog, private milestones, software
quality, SLA adherence, or employee productivity. Older unmodified issues
can be absent from recent-update API sampling.

## Work that is not yet proven

1. **Data completeness:** recheck the actual per-source 28-day counts after
   the next validated collection, and retain full source audit artifacts.
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
