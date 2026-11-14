# Project Delivery Monitor | Portfolio case study (one-page read)

**Python · SQL (SQLite/SQLAlchemy, read-only grouped queries) · Streamlit ·
Pandas · Plotly · GitHub REST API · GitHub Actions**

## Project scope in one sentence

**This is a public GitHub engineering-activity and evidence-review dashboard, not a tracker of client delivery dates or project milestones.** The name "Project Delivery Monitor" is a portfolio product name; the app does not claim to measure contractual delivery performance.

## The problem

Someone reviewing public software projects can see thousands of GitHub Issues,
pull requests and CI checks, but raw counts lack context. A partial API scan
can look like zero activity; old Issues can look like missed deadlines; and
several sources can have different coverage windows.

## What I built

A six-page, visual-first dashboard that organizes **50 curated public GitHub
repositories** and turns collected public activity into **source-linked
inspection questions**, not opaque project-health or productivity scores.

- **Collect:** authenticated or bounded GitHub REST requests, incremental
  SQLite upserts, source checkpoints, timestamped compressed snapshot
- **Validate:** distinguish each source's complete 7/28-day window from
  exploratory scans; preserve incomplete records instead of deleting them
- **Analyze:** real read-only SQL/CTE insights and deterministic Python
  metrics for Issue age, verified 28-day PR merge time, and known 28-day CI outcomes.
  CI success share includes skipped/other known results in its denominator;
  those outcomes are not treated as verified build failures.
- **Review:** headline measures, trends, filters, original GitHub record
  links where available, three-step inspection actions and CSV evidence plan

## Result / demonstrated engineering

- **50 curated public repositories** were independently Verified on the
  **14 November 2026 09:39 WIB** snapshot for 28-day Issues, PR and CI/CD
  source windows **and separately** 50/50 fresh complete open-Issue
  inventories. This is a timestamped validation, not a live guarantee.
  The curated sample is **not a representative random sample** of GitHub.
- For the historical original 75-repo dataset, the SQL loader reduced its
  measured SELECT count from **376 to 6** after batching sources and
  retaining the 30 most recent per-project observations. This is **query
  count**, not a claimed 98% improvement in browser speed.
- Automated CI checks validate source-row counts against the real compressed
  snapshot, SQL/KPI consistency and desktop/mobile browser behavior,
  including screenshots and detection of hidden Streamlit exceptions.
- Findings distinguish **a directly traceable GitHub Issue/PR/CI record**
  from a fallback **repository listing**, and avoid calling either a proven
  delay, client issue, or engineering defect.

## How a nontechnical reviewer can explore it

1. **Dashboard:** read What happened → Why inspect → Next action → GitHub
   evidence; then inspect the activity chart. Optional detailed charts can
   be expanded without overwhelming the first screen.
2. **Key findings:** open a measurable inspection opportunity and verify
   its source URL and suggested next check
3. **Explore repositories:** compare two sources and switch Verified /
   Exploratory to understand why incomplete records cannot prove zero work

**Portfolio claim boundary:** The app does not monitor confidential client
projects, deadlines, SLAs, developer productivity or code quality. The
four-hour GitHub Actions schedule is best effort; full cadence reliability
is not established by a successful manual run.


## Reviewer readiness: tested versus not yet tested

- **Automated:** real saved GitHub snapshot, SQL/KPI parity, browser screenshots
  on desktop/mobile, original evidence links, and honest missing-source labels.
- **Human:** a 3–5-participant nontechnical usability test **has not been
  conducted**; the [unfilled test protocol](REVIEWER_USABILITY_CHECK.md)
  is available, and no participant scores are invented.
- **Hosting:** a public Streamlit Community Cloud URL **has not been verified**.
  Local browser performance is **not** hosted cold-start performance.

## Links to independently check

- [Public GitHub repository](https://github.com/Granbe1l/beta-test)
- [Quality Checks](https://github.com/Granbe1l/beta-test/actions/workflows/ci.yml)
- [Recorded browser screenshots](https://github.com/Granbe1l/beta-test/actions/workflows/ui-screenshots.yml)
- [SQL query reduction and real-snapshot regression evidence](https://github.com/Granbe1l/beta-test/pull/15)
- [Repository navigation and source status fixes](https://github.com/Granbe1l/beta-test/pull/16)
- [Source-linked business finding action](https://github.com/Granbe1l/beta-test/pull/18)
- [Public deployment verification instructions](PUBLIC_DEPLOYMENT.md)

**Public hosted Streamlit URL: not yet verified.** Do not add a fictional
app link to the CV or portfolio. Deployment needs the repository owner
to sign in to Streamlit Community Cloud and run the real public URL
verification workflow.

**Interview discussion:** Explain why the same public source can yield
different record counts in a verified 28-day cohort versus exploratory
mode, and how SQL checks plus original GitHub links make the conclusions
auditable rather than merely attractive charts.
