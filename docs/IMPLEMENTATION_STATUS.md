# Project Delivery Monitor — implementation and evidence status

Updated: **13 November 2026**. Repository: `Granbe1l/beta-test`.

## What is implemented and verified

| Work | Current status | Evidence |
| --- | --- | --- |
| Six visual Streamlit pages, purple/white theme, Plotly activity charts | Implemented; desktop/mobile browser capture succeeded | `src/ui/dashboard_v2.py`, workflow screenshot run #32 |
| Fixed 75 curated public GitHub repositories | Verified in published real snapshot | data snapshot audit workflow #13 |
| Issues, PR, GitHub Actions collection | Implemented; source completeness **partial** | `src/collectors/sync.py`, source audit #13 |
| 6-hour UTC scheduled snapshot refresh | Implemented; at least one scheduled workflow run succeeded | `public-snapshot.yml`, run #12 (`schedule`) |
| Explicit 7/28-day verified versus exploratory charts | Implemented and regression-tested | `src/ui/trend_panels.py`, `src/ui/observed.py` |
| Evidence-first findings, direct record examples and next checks | Implemented on improvement branch; CI verification required | `src/analytics/findings.py`, `tests/test_visual_insights.py` |
| Read-only SQL CTE audit across all three source tables | Implemented on improvement branch; real snapshot CI verification required | `scripts/sql_insights.py`, `tests/test_sql_insights.py` |
| Continuous unit tests | Baseline main: **107 passing** as of quality-check run #50 | GitHub Actions `Quality checks` |
| Public Streamlit Cloud website | **Not verified** | `docs/PUBLIC_DEPLOYMENT.md` |
| Actual nontechnical user testing | **Not completed** | `docs/REVIEWER_USABILITY_CHECK.md` is a test plan, not test evidence |

## Latest validated data audit (workflow #13)

Captured **2026-11-12 23:48 UTC** (2026-11-13 06:48 WIB):
- Curated repositories: **75**.
- Persisted issue records: **11,310**.
- Persisted pull-request records: **25,676**.
- Persisted GitHub Actions runs: **72,485**.
- Verified full **28-day** source windows: issues **38/75**, PRs **48/75**, CI/CD **32/75**.
- Status `complete` describes a completed **bounded source scan**, never complete GitHub lifetime history.

Source: https://github.com/Granbe1l/beta-test/actions/runs/43328904930

## Remaining work, in priority order

1. **P0 — Coverage and correctness:** continue bounded incremental collection on incomplete/stale source checkpoints; prove verified-source coverage improves without dropping previously stored records. A green workflow does not mean all 225 repository/source combinations are verified.
2. **P0 — Evidence interpretation:** audit the exact 28/90-day period on each claim; retain uncertainty about older, unmodified issues and avoid calling issue age an overdue deadline.
3. **P1 — Nontechnical validation:** run the five-minute recruiter tasks in `docs/REVIEWER_USABILITY_CHECK.md`, record observed errors/confusion, and iterate the wording/visual hierarchy.
4. **P1 — Scheduling reliability:** verify successive actual scheduled collection runs and their published before/after source audit artifacts.
5. **P2 — Public verification:** deploy the read-only Streamlit site as the owner, and run `verify-public-demo.yml` with its real URL.
6. **P2 — SQL demonstration:** show SQL CTE audit output from actual published snapshot; do not claim the Streamlit public app queries a live PostgreSQL server.

## Architecture notes

The default public app loads a checked-in real GitHub JSON snapshot. The collector uses SQLAlchemy/SQLite for persistent checkpoints; PostgreSQL is supported but optional. A separate **real handwritten SQL** analysis performs bounded, source-aware aggregations on those SQL tables. Source examples in the findings are original GitHub links to inspect—not proof of project delay, breached SLAs, or developer quality.

The cohort is selected from **repositories**, not individual high-activity contributors. Public records cannot reveal private client milestones, contract SLAs, or business delivery dates.
