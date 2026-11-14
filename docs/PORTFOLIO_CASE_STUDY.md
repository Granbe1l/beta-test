# Project Delivery Monitor — portfolio case study

## Problem and audience

How can an HR reviewer or IT consultant see whether publicly visible software work is moving, and understand the reliability of the supporting data? This project monitors 50 vetted public GitHub repositories. It is a portfolio demonstration, not a delivery-performance or project-quality ranking.

## Workflow

GitHub REST API → incremental, bounded API extraction → persistent SQLite checkpoints → audited compressed public snapshot → Streamlit dashboard.

- GitHub Actions attempts collection every four hours. A refresh in the Streamlit UI reads the stored snapshot; it does not call the API.
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

The finding queue shows up to three diverse, evidence-backed review opportunities, with numerical facts, limits, recommended inspection and original GitHub links. Priority labels describe suggested order of inspection—not performance scores. Distinct source-backed inspection case studies on the Key findings page are conditional: they do not claim a real team has taken the suggested action.

## Validation

Python, SQLAlchemy/SQLite, Streamlit and Plotly. Automated tests verify API pagination and source separation, checkpoint semantics, 28-day coverage gates, audit reporting, and responsive browser rendering. Browser tests also exercise navigation, CSV export and a side-by-side repository comparison.

## Limitations

GitHub API pagination and recent-update ordering can omit older activity. Some repositories have more complete coverage than others. A GitHub Actions run can succeed without all 50×3 source scans being complete. Screenshots and application tests do not prove scheduled refresh reliability. No private project deadlines, SLAs, code quality or developer performance can be derived from public issues and pull requests.

## How to explain this project at interview

I created a dashboard using public GitHub API records to monitor observable tasks, code changes and automated checks across 50 repositories. The major challenge was ensuring charts stayed honest when API collection was incomplete. I built per-source checkpoints, clear coverage states, a verified/exploratory trend switch, and links from every review finding to source records.

## Next operational evidence gate

Inspect the latest GitHub Actions public-snapshot run and its audit summary. Confirm snapshot publication, compare verified 28-day source counts with the previous audit, and require multiple successful scheduled runs before claiming reliable automated refresh.

## Nontechnical decision-first readout

The Dashboard opens with a **two-column Quick reading**, before the main
observed activity chart:
- **Activity and next inspection (left):** seven-day public push/Issue/PR
  signals, one measurable finding and a direct GitHub source action.
- **Data confidence (right):** how many repositories qualify for verified
  28-day Issue, PR and Actions windows, independently from complete
  current-open Issue inventories.

The main Issues/PR trend remains visible, while three detailed evidence
cards are available in the clearly labelled expandable section. The
**Key findings** page additionally provides three distinct, conditional,
record-level walkthroughs from the real stored snapshot:
[dated original GitHub examples](EVIDENCE_CASE_STUDIES.md).
No client deadline, code-quality or productivity verdict is inferred.

## Collection and independent SQL contribution

The bootstrap scans the exact 28-day analysis period first to reduce
near-duplicate API requests. For CI/CD the **current UTC day is rechecked**
on every run rather than trusting a four-hour-old day-level checkpoint.
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
  near the four-hour cadence before claiming scheduling reliability.
- A real 3–5 participant test described in
  [the review protocol](REVIEWER_USABILITY_CHECK.md) remains to be
  conducted; automated screenshots do not prove human understanding.


### Distinguishing historical open work from recent activity

A complete 28-day **updated-event scan** is not a complete repository
backlog. We use a separate oldest-first `state=open` GitHub Issues
source and explicitly report whether the pages were exhausted. It
improves discoverability of old untouched open Issues while retaining
a precise distinction between verified and partial inventories.

To keep comparisons defensible, every SQL observation now stores its
`collection_basis`. Switching from an incomplete updated-record sample
to an independently verified full open inventory must **not** be
mistaken for a sudden growth in the volume of project work. The
comparison logic only pairs observations using the same collection
method and matched repository cohort.

## P1: Evidence → inspection → bounded decision

The dashboard does **not** rank developer productivity or project health.
Each review opportunity is now a compact, checkable three-step brief:

1. **Why inspect:** a real measured numerator, denominator and source
   window must pass the documented inspection trigger.
2. **Where to inspect:** an original GitHub Issue, pull request or workflow
   run is linked where the stored snapshot includes one; otherwise the
   app explicitly labels the repository listing as a starting point.
3. **What decision is allowed:** the reviewer examines maintainer context,
   check logs, change size or closure reasons before writing a finding.
   No deadline breach, software defect or employee performance is inferred
   merely from an older Issue, changed closure count or failed CI run.

The Key findings page has **Export evidence review plan (CSV)**. It uses
the exact displayed findings and includes GitHub links, source-confidence
labels, checks, and caveats. Exported user-controlled repository text is
escaped against spreadsheet formula injection. Review steps and links are
testable in automated unit and populated browser captures.

**This is an inspection queue, not a validated business outcome.** Real
nontechnical participant testing is still pending; CI and screenshots
cannot establish what a human HR reviewer understands.


## P2: reproducible performance, navigation and evidence UX

The improvements below were validated against the same public GitHub
snapshot, without fabricating an HR-user test or inventing end-user latency.

| Stage | Observable improvement | Acceptance evidence |
| --- | --- | --- |
| P2.1 Performance | Batch SQL SELECTs per source; retain the latest 30 per-repository observations; decode compressed snapshot date fields in one JSON pass | 376 previous per-repository SELECTs vs **6** on the prior 75-repository cohort; CI checked stored Issue/PR/CI row parity ([PR #15](https://github.com/Granbe1l/beta-test/pull/15)) |
| P2.2 Filters and navigation | Keep repository choice across pages, reset pagination when matching rows change, prevent missing open-backlog status and pandas NaT table errors | Streamlit AppTest + real desktop/mobile capture with exception detection ([PR #16](https://github.com/Granbe1l/beta-test/pull/16)) |
| P2.3 Visual clarity | Condense the mobile opening, move supporting coverage detail into an expandable explanation, avoid Plotly modebar overlay | Actual responsive browser screenshots and retained disclosure tests ([PR #17](https://github.com/Granbe1l/beta-test/pull/17)) |
| P2.4 Decision traceability | Main action opens an original stored record whenever present; source-listing fallback is labelled rather than passing as record-level evidence | Real-snapshot reviewer action audit and browser tests ([PR #18](https://github.com/Granbe1l/beta-test/pull/18)) |
| P2.5 Portfolio readiness | Place the nontechnical reviewer journey first; avoid stale fixed source counts and include a readable CV proof | [one-page case study](PORTFOLIO_CARD.md), [CV evidence](CV_EVIDENCE.md), GitHub Quality Checks and [public-demo gate](PUBLIC_DEPLOYMENT.md) |

The scope of "verified" applies to checked source windows, **not**
software quality, developer productivity, client deadlines or a claim
that all GitHub history was collected. A page being visible in automated
browser tests does not establish a publicly hosted Streamlit URL.

**Still open, outside code-review completion:**
- Three genuinely successful scheduled collection events with acceptable
  spacing have not been established as consistent four-hour operation.
- Streamlit Community Cloud deployment requires owner sign-in and real
  public URL verification; it must not be claimed successful before then.
- A formal human nontechnical participant study has not been performed.
  The automated UI/contrast/evidence tests are valid portfolio
  engineering tests but are not a human-understanding score.
