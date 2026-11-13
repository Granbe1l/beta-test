# Project Delivery Monitor — portfolio case study

## Problem and audience

How can an HR reviewer or IT consultant see whether publicly visible software work is moving, and understand the reliability of the supporting data? This project monitors 75 curated public GitHub repositories. It is a portfolio demonstration, not a delivery-performance or project-quality ranking.

## Workflow

GitHub REST API → incremental, bounded API extraction → persistent SQLite checkpoints → audited compressed public snapshot → Streamlit dashboard.

- GitHub Actions attempts collection every six hours. A refresh in the Streamlit UI reads the stored snapshot; it does not call the API.
- Existing projects stay in the cohort, including projects with no recently observed activity. The sample is not secretly rotated to make graphs rise.
- Newly unvisited and incomplete sources are prioritized within a bounded API budget.
- Adaptive scans try an initial window and, if capped, narrower 28-, 7- and 1-day windows. A completed short-window scan is NOT a complete repository history.
- Audit artifacts report complete, partial, stale, failed and unavailable source states, verified 28-day windows and before/after differences.

## Evidence and interpretation

| Measurement | What it says | What it does not prove |
| --- | --- | --- |
| Recent push | GitHub repository metadata changed | A new feature was delivered |
| Open issue age | Time since an issue was created | A deadline was missed |
| Pull-request merge time | Observed time to merge a proposed code change | Developer productivity |
| CI/CD success share | Successes among completed runs with known results, in one period | Software quality or uptime |
| Daily activity line | Issues/PRs observed in timestamped API records | A complete multiweek trend |
| Two-date snapshot comparison | Open items from the same repositories on both dates | Cause, efficiency or team quality |

Daily charts have separate **exploratory** and **verified source window** scopes. In verified mode, only repositories whose corresponding source covers the requested 7/28-day window are included. If there are no qualifying repositories, the UI shows a clear empty state instead of inventing a graph.

The finding queue shows up to three diverse, evidence-backed review opportunities, with numerical facts, limits, recommended inspection and original GitHub links. Priority labels describe suggested order of inspection—not performance scores.

## Validation

Python, SQLAlchemy/SQLite, Streamlit and Plotly. Automated tests verify API pagination and source separation, checkpoint semantics, 28-day coverage gates, audit reporting, and responsive browser rendering. Browser tests also exercise navigation, CSV export and a side-by-side repository comparison.

## Limitations

GitHub API pagination and recent-update ordering can omit older activity. Some repositories have more complete coverage than others. A GitHub Actions run can succeed without all 75×3 source scans being complete. Screenshots and application tests do not prove scheduled refresh reliability. No private project deadlines, SLAs, code quality or developer performance can be derived from public issues and pull requests.

## How to explain this project at interview

I created a dashboard using public GitHub API records to monitor observable tasks, code changes and automated checks across 75 repositories. The major challenge was ensuring charts stayed honest when API collection was incomplete. I built per-source checkpoints, clear coverage states, a verified/exploratory trend switch, and links from every review finding to source records.

## Next operational evidence gate

Inspect the latest GitHub Actions public-snapshot run and its audit summary. Confirm snapshot publication, compare verified 28-day source counts with the previous audit, and require multiple successful scheduled runs before claiming reliable automated refresh.

## Nontechnical decision-first readout

The first visual activity chart is followed by a **three-column Quick reading**:
- **Recent observed activity:** latest seven-day repository pushes and captured
  Issue/PR events (not proof of feature releases);
- **Where to inspect next:** one evidence-backed finding, the observed
  figure and a direct original-record link;
- **Confidence in the evidence:** number of project-specific Issue, PR and
  automated-check sources whose **entire 28-day** window is validated.

This format deliberately avoids fake deadline/quality scores and keeps the
existing graphs as the primary evidence.

## Collection and independent SQL contribution

The bootstrap scans the exact 28-day analysis period first to reduce
near-duplicate API requests. For CI/CD the **current UTC day is rechecked**
on every run rather than trusting a six-hour-old day-level checkpoint.
Old stored records are retained when a GitHub API window is capped.

The separate read-only SQL analysis in `scripts/sql_insights.py` uses
CTEs, grouped SQL joins and CASE-based source-specific verification flags.
Its source tables are grouped before being joined to avoid cross-source
count multiplication. GitHub Actions tests this query against restored
**real** public GitHub records; the public website still reads a stored
snapshot, not a live SQL query.

## What remains to verify

- A new successful snapshot run must establish **actual** before/after 28-day
  source-coverage changes, not presumed gains from code optimizations.
- A schedule audit must observe at least three genuine successful cron events
  near the six-hour cadence before claiming scheduling reliability.
- A real 3–5 participant test described in
  [the review protocol](REVIEWER_USABILITY_CHECK.md) remains to be
  conducted; automated screenshots do not prove human understanding.
