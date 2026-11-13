# Project Delivery Monitor — Open-Source Analytics

An evidence-first, read-only analytics dashboard that helps nontechnical reviewers understand observable issue, pull request, and GitHub Actions activity across an **audited, non-representative sample** of public GitHub repositories. Built with Python, Streamlit, Pandas, Plotly and SQLAlchemy; **SQLite** is the default collector database, with **PostgreSQL optional**. The public demo reads a compressed snapshot without needing a live SQL server. No React, FastAPI, chatbot, generative AI, or paid AI APIs.

> **Current status (13 November 2026):** The audited 75-repository public snapshot exists, GitHub Actions collection has completed successfully, and desktop/mobile browser screenshot tests have passed. GitHub Actions collection is scheduled every six hours, but individual runs can be delayed or fail; never mistake a stored snapshot for real-time data. Hosted Streamlit Cloud deployment and managed PostgreSQL are separate, optional steps and are **not** claimed verified here. All figures are obtained from public GitHub records.

## What SQL is used for

This project **does use a SQL database for data collection and checkpointing**, but the read-only Streamlit demo primarily analyzes a checked-in JSON snapshot using Python/Pandas. Database access is implemented with SQLAlchemy ORM, not an extensive library of handwritten SQL queries. Read the [actual schema and SQL examples](docs/SQL_DATABASE_USAGE.md) to distinguish the implemented pipeline from illustrative SQL queries.

## Public demo — deployment gate

**Status: public URL not yet verified.** The complete Streamlit application
passes local desktop/mobile browser checks, but do not present a local test
as an accessible hosted demo.

Deploy from **Granbe1l/beta-test**, branch **main**, entrypoint
**streamlit_app.py**, then run the GitHub Actions workflow
**Verify public Streamlit deployment** with the actual public URL.
That workflow verifies the real hosted page, the latest checked-in
snapshot timestamp, visible charts, and Key Findings navigation.

For precise owner steps and acceptance criteria, see
[Publish and verify the public Streamlit demo](docs/PUBLIC_DEPLOYMENT.md).

## Questions answered

1. What observable software-development activity occurred within the configured window?
2. Which repositories have a large share of **observed** open issues aged 30+ days?
3. What was the median time from creation to merge for PRs **merged in the period**?
4. Did issue closure volume increase or decrease between two comparable 28-day windows?
5. Which conclusions have enough source coverage, sample size, and links to be defensible?
6. What review should the reader perform next?

Issue age is **not** lateness, PR merge time is **not** productivity, and CI success share is **not** software quality. The application intentionally avoids a project-quality leaderboard.

## Dashboard design and activity signals

Six visual-first Streamlit views: **Dashboard**, **Explore repositories**,
**Open issues**, **Changes & reviews**, **Build activity**, and **Key findings**.

The dashboard distinguishes genuine event types:

- **Recently pushed:** GitHub repository `pushed_at` metadata within seven days;
  this is not proof of a new feature or release. Metadata is refreshed for
  repositories visited by the collector.
- **Issue activity:** observed `created_at` and `closed_at` timestamps.
- **PR activity:** observed `created_at` and `merged_at` timestamps.
- **Weekly lines:** event counts for the same fixed observation window;
  never arbitrary/random values or an invented commit history.
- **Quieter projects:** no recent signal in the bounded collected data, **not**
  a claim that development has stopped or the project is completed.

The source-scope filter makes both recently active and quieter projects
inspectable. The curated cohort is retained for longitudinal comparisons
instead of silently swapping in more active repositories, which would bias
apparent trends. Repository selections require a push within 30 days at
selection and a bounded issue/PR probe. Full source coverage may still be
partial; all aggregate charts say **retrieved** or **observed** records.

The UI uses restrained purple/white cards, high-contrast navigation labels
without radio bullets, and concise findings linked to GitHub evidence.
Desktop/mobile rendering is verified by real-browser screenshot workflows.

## Architecture

```text
GitHub REST Search API (bounded discovery, manual trigger)
                  |
       selection audit + eligibility probes
                  |
      repositories and selection candidates
                  |
GitHub REST issues / pulls / actions/runs (read-only)
                  |
 bounded paging + normalized validated records
                  |
 PostgreSQL (local option: SQLite) <--- checkpoints, logs, observations
                  ^
 GitHub Actions public snapshot every 6h
                  |
         per-source incremental upsert
                  |
 SQLAlchemy read queries -> deterministic analytics -> Streamlit (600s TTL)
```

Collection and UI are intentionally decoupled: a dashboard visit does **not** initiate full synchronization. The checked-in snapshot runs on Streamlit Cloud without PostgreSQL. Managed PostgreSQL is optional for persistent, deeper data pipelines; Streamlit Community Cloud's local filesystem is ephemeral.

### Files

```text
streamlit_app.py                 Dashboard entry point
src/config/settings.py          Validated environment settings
src/discovery/selection.py      Search, filters, decisions, diversification
src/collectors/client.py        Read-only GitHub REST client, retries, pagination
src/collectors/normalize.py     Source URL, identity, timestamp validation
src/collectors/sync.py          Incremental load, reconciliation, writer lock
src/database/models.py         SQLAlchemy schema / uniqueness constraints
src/database/store.py          Sessions, upsert, safe errors
src/analytics/metrics.py       Deterministic KPIs and denominator rules
src/analytics/findings.py      Evidence-based interpretation and next review
src/analytics/read.py          Read persisted records / source health
src/ui/pages.py                Five dashboard views
src/ui/theme.py                Accessible colors, responsive CSS
scripts/init_db.py             Initialize schema
scripts/run_sync.py            Initial selection / scheduled sync CLI
scripts/audit.py               Counts and verifiable status
.github/workflows/ci.yml       Tests on push/PR/manual dispatch
.github/workflows/sync.yml     6h incremental + Sunday reconciliation
.env.example                   Local configuration template
.streamlit/secrets.example.toml Streamlit configuration example
.tests                         Pytest controlled fixtures (actual path: tests/)
```

## Selection methodology

1. Search multiple language/ecosystem groups (`Python`, `TypeScript`, `Go`, `Rust`, `Java`, `Kotlin`, `C++`, `Ruby`). Each query includes `is:public fork:false archived:false stars:>=50 pushed:>=YYYY-MM-DD`.
2. Search is constrained by `MAX_CANDIDATES`, `SEARCH_PAGES_PER_QUERY`, and a per-language quota, **not** a GitHub-wide crawl. Deduplicate by stable GitHub repository ID.
3. Validate repository metadata: public, nonfork, nonarchived, >=50 stars, last push <=30 days, issues enabled, language recognized.
4. Probe a **bounded** slice of GitHub `/issues?state=all` and `/pulls?state=all` for independent issues and any PRs. A negative bounded probe is an **uncertain rejection**, not proof there has never been an issue. A follow-up collector determines the actual extractable sample.
5. Diversify across broad language categories and star-size tiers (`50–499`, `500–4,999`, `5,000+`) by round-robin. Fill leftover slots with eligible candidates if diversity constraints cannot fill the cap. Select **at most 75**.
6. Record GitHub search queries, timestamps, candidates, selection reasons, and URLs in `SelectionRun` and `Candidate`. The selected set persists to preserve longitudinal comparability; routine sync refreshes last-push metadata for visited repositories. Quieter/archived repositories are flagged, not silently relabeled as finished.

**Sampling limitation:** Search result ordering, API result caps, bounded activity probes, and platform/language choices create selection bias. Even 75 selected repositories **cannot** represent all of GitHub.

## Data extraction and checkpoints

- `issues`: `/repos/{owner}/{repo}/issues`, `state=all`, `sort=updated`, `direction=desc`, `since=...` (and exclude entries with the `pull_request` key).
- `pull_requests`: `/repos/{owner}/{repo}/pulls`, `state=all`, `sort=updated`, `direction=desc`; **no unsupported `since` parameter** is supplied. Stop on the local updated-at boundary if traversed.
- `workflow_runs`: `/repos/{owner}/{repo}/actions/runs`, `created=YYYY-MM-DD..YYYY-MM-DD`; use created-date and age-based overlap, **not** imaginary `since` semantics.
- For each repository/source, persist `high_watermark`, `coverage_start`, `last_success_at`, fetched pages/records, status (`complete`, `partial`, `failed`, `stale`, `unavailable`), and sanitized error logs.
- A `MAX_PAGES_PER_SOURCE` truncation is flagged `partial`; **complete** means exhausted the requested bounded scan or reached a safe chronological boundary, **not** complete lifetime history.
- Incremental upsert uses stable global GitHub IDs plus `(repo_id, number)` constraints on issues/PRs. A 48-hour overlap reduces indexing race risk. Workflow runs recheck a larger 14-day window. Weekly full-window reconciliation is included.
- Each source write and successful checkpoint update is committed together. Errors roll back the failed source transaction, preserve previous records and `last_success_at`, and mark `failed`. Missing data is never silently converted to a numeric zero.
- PostgreSQL advisory lock or local file lock prevents concurrent writer runs. GitHub Actions `concurrency` adds run-level coordination.
- Retries use bounded exponential backoff, rate-limit-aware waits and request timeouts. The GitHub client only issues HTTP **GET** requests and never mutates third-party repositories.

### Coverage caveat

Even with a `complete` bounded scan, open issues that have not been updated in the selected window may be absent. Reported open-item counts and long-lived percentages describe **observed records in the configured collection**, **not** the entire current GitHub backlog. Issue/PR event trends are displayed only when persisted checkpoint coverage spans the full observation period and current sync checks succeed. Comparisons suppress incomplete, stale, or low-sample results.

## Metrics / denominators

| Metric | Calculation | Coverage / conditions |
|---|---|---|
| Observed open issues | Count persisted standalone issues with `state=open` | Complete, current issue collection; limited historical window |
| 30+ day issue share | Observed open issues with `now - created_at >= 30d` ÷ all observed open issues × 100 | Denominator displayed; cross-repository comparison needs ≥5 open issues |
| Issue activity | `created_at` / `closed_at` counts in UTC calendar weeks | Full covered observation period |
| Issue closure change | `(closures in recent 28d - previous 28d closures) / previous 28d closures × 100` | Full 56d coverage and prior closure count >0 |
| Open PRs | Persisted PRs with `state=open`; draft PRs are included | Current, complete PR source |
| Draft PRs | Count of open PRs with `draft=true` | Subset of open PRs; not added again |
| Merged PRs | PRs with `merged_at` in selected window | Full observation window |
| Closed without merge | Closed PRs with no `merged_at` and `closed_at` in window | Full observation window |
| Median merge duration | Median of `(merged_at - created_at)` in days for in-period merged PRs | At least 5 PRs; never the arithmetic mean |
| CI completed | GitHub Actions workflow runs `status=completed`, created in window | Full workflow-run period coverage |
| CI success share | Completed runs with `conclusion=success` ÷ completed runs with **known non-null conclusion** × 100 | Denominator explicit; includes `skipped`/`neutral` among known conclusions |
| Review compliance | Not Available | Missing a consistent review policy and complete approvals history; do not invent a rule |

Source-specific insights are only rendered after validity gates; findings include a claim, its numerator/denominator, a noncausal interpretation, a proposed review, and a link to GitHub evidence. Absence of findings is treated as a valid state.

## Local setup

Recommended Python 3.12+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env     # Windows PowerShell: Copy-Item .env.example .env
```

The default `.env.example` uses SQLite **only for local development**; replace `GITHUB_TOKEN=` with a local GitHub fine-grained read-only token for higher API request budgets, or leave unset at the cost of lower unauthenticated limits. **Do not commit `.env`.**

```bash
python scripts/init_db.py
python scripts/run_sync.py --discover  # explicit initial selection, may make many bounded GET requests
python scripts/audit.py
streamlit run streamlit_app.py
```

`streamlit_app.py` displays a clear unavailable/empty state until the database is initialized and source records exist. If `--discover` finds no eligible candidates, the command exits without inventing data. Subsequent runs can omit `--discover`:

```bash
python scripts/run_sync.py
python scripts/run_sync.py --reconcile
```

**No background local scheduler is implied.** Execute the CLI manually when testing locally; only configured GitHub Actions performs periodic sync.

## PostgreSQL production configuration

1. Provision a persistent **managed PostgreSQL instance** yourself (examples: Supabase PostgreSQL, Neon PostgreSQL, Render PostgreSQL). This project does not create one.
2. Create a dedicated database user with the minimal required privileges and TLS enabled (`sslmode=require` if your provider supports it).
3. Set `DATABASE_URL` (real value, not the example) in **GitHub repository Settings → Secrets and variables → Actions** and in **Streamlit Community Cloud → App settings → Secrets**.
4. Set a read-only `GITHUB_TOKEN` in GitHub Actions Secrets; scope access to necessary public repository metadata and Actions read operations. Do not grant repository contents write permission.
5. Initialize the remote schema one time with `DATABASE_URL=... python scripts/init_db.py` from a protected environment, then manually invoke `run_sync.py --discover` or `workflow_dispatch` with `discover=true`.
6. Verify `python scripts/audit.py` with the remote database and that selected repositories/records have source URLs and complete checkpoints before trusting dashboard claims.
7. Keep PostgreSQL credentials out of Actions logs, code, screenshots, or committed files. Database credentials exist only in secrets.

## GitHub Actions synchronization

The active public-snapshot workflow `.github/workflows/public-snapshot.yml` runs at `27 */6 * * *` (UTC) and also supports manual `workflow_dispatch`. It restores the last saved GitHub snapshot, collects bounded public records, publishes an audit artifact, then commits the updated `.json.gz` snapshot to `main`. The snapshot writer fetches current `main` and reapplies only the new generated binary file; it does not try to rebase conflicting binaries. Code pushes no longer trigger additional data writers. A separate `.github/workflows/sync.yml` is an opt-in PostgreSQL mode and must not be described as a working managed-database deployment without configuration.

Scheduled Actions do **not** guarantee execution at the exact minute, and GitHub may disable scheduled workflows in inactive public repositories. The collector uses read-only GitHub REST API calls. The public snapshot workflow has `contents: write` only to commit its validated snapshot to `main`, and `actions: read` to audit real scheduled runs. The database writer uses a concurrency group and lock.

## Streamlit Community Cloud

The **default portfolio demonstration is snapshot-only**, not a live
PostgreSQL app. A public Streamlit URL has not yet been verified.

1. In Streamlit Community Cloud choose `Granbe1l/beta-test`, branch
   `main`, entrypoint `streamlit_app.py`.
2. **No database secret is required** for the checked-in read-only
   `data/github_public_snapshot.json.gz` mode.
3. GitHub Actions updates that stored snapshot independently. A visitor
   does not trigger GitHub API collection or a SQL write.
4. Check actual deployed desktop/mobile rendering, source links, filter
   behavior, displayed snapshot time and freshness caveats before publishing
   the link in a CV.
5. **Optional, separate path:** for managed PostgreSQL, provision TLS,
   set `DATABASE_URL` securely and configure the protected collector.
   Do not claim that deployment exists until credentials, initialization
   and refresh have been verified.

## Tests and evidence

```bash
python -m compileall -q src scripts streamlit_app.py
python -m pytest -q
python scripts/audit.py
```

The suite covers bounded selection, deduplication, pagination, retry/rate handling, incremental overlaps, idempotent upsert, rollback/status, issue-vs-PR separation, median, ratios/denominators, empty states, responsive CSS **presence**, and secret-related checks. A fixture-based end-to-end test exercises collection → SQL database → deterministic findings. Controlled fixtures are **tests only**; they are not inserted into the production database. Runtime Streamlit smoke testing is skipped when Streamlit is not installed in the current interpreter. A CSS unit test is **not** a mobile screenshot test.

## Outstanding work and integrity boundaries

- GitHub Actions produced and audited real public GitHub snapshots. A stored snapshot is not a live API feed; data availability is reported per source.
- No managed PostgreSQL `DATABASE_URL`, production token, or deployment has been provided.
- Desktop/mobile real-browser screenshots were captured in GitHub Actions. Actual HRD user-testing and hosted public URL verification remain open.
- GitHub API pagination and rate-limit behaviors are covered by fixtures, but real API edge cases may require adjustment after live runs.
- `review-compliance share` remains deliberately Not Available rather than measuring an arbitrary rule.
- Complete historical issue counts are not claimed. Recent changed-record sampling differs from a full open-backlog scan.
- This implementation is intended for analysis and due diligence, not contractual SLAs or causal performance assessment.

## Screenshot evidence

**Actual screenshots: available as GitHub Actions artifacts.** The [successful desktop/mobile capture run](https://github.com/Granbe1l/beta-test/actions/runs/43338398246) contains rendered browser screenshots from the real 75-repo snapshot. These are not design mockups or public usability-test results.

## Repository destination

Repository: <https://github.com/Granbe1l/beta-test> (branch `main`). Source changes have been reviewed and merged through PR #1; deployment to a live public Streamlit URL is not verified.

**GitHub Actions verification (2026-11-13):** main-branch CI passed **111 automated tests**, restored the real 75-repository public snapshot and executed the SQL audit; the [quality-check run](https://github.com/Granbe1l/beta-test/actions/runs/43338398122) is the baseline. Later review changes add regression tests; use the latest completed run rather than assuming an old count remains current.

## Data snapshot — deploy without PostgreSQL first

The repository contains `data/github_public_snapshot.json.gz`, a **read-only real GitHub REST API snapshot** generated by the GitHub Actions `Refresh public GitHub snapshot` workflow. The file has a capture timestamp, original evidence URLs, selected repository count, and coverage per source. It is **not** a live GitHub connection and is **not** representative of all public repositories.

**Streamlit Cloud setup:** select repository `Granbe1l/beta-test`, branch `main`, app file `streamlit_app.py`. No database credential is necessary in snapshot mode. The UI explicitly displays capture time and marks partial/stale source data. It uses real retrieved records to draw observed aging and merge-time charts while suppressing complete-coverage claims. GitHub Actions requests bounded public data every six hours; GitHub may delay or disable schedules.

For production data and historical incremental synchronization, provision managed PostgreSQL, set a secure `DATABASE_URL`, initialize the schema, then run the separate checkpointed collector. The **snapshot workflow re-collects a bounded observation window**, whereas the PostgreSQL collector implements incremental upserts. The PostgreSQL workflow is manual/opt-in until a database is configured, avoiding misleading failed scheduled runs. Snapshots contain no fixture records or credentials.


## Scaling selected GitHub repositories to 75

- **Target: up to 75 curated public repositories** with verified metadata and eligibility, not a representative sample of all GitHub. The existing ten and their evidence records are preserved.
- Each scheduled GitHub Actions run restores the previous public snapshot into an ephemeral SQLite collector, retaining upsert IDs and per-source checkpoints.
- Candidate discovery is bounded and audited; expanding selection is allowed only after GitHub Search and standalone-issue/PR eligibility checks.
- The initial source collection is staged (up to **20 previously unseen repositories per run**). After seeding, the collector attempts incremental updates across the full selection each six-hour run, respecting an **850-request cap** and limited endpoint pagination.
- **A six-hour scheduled run does not guarantee that every repository is refreshed or has complete data every six hours.** GitHub may also delay scheduled runs. The collection order rotates if the request budget is limiting.
- No full GitHub clone, fake production data, or hidden completeness claims. The dashboard labels incomplete, stale, failed, or unavailable data.

Operational commands for the snapshot workflow: `python scripts/restore_public_snapshot.py`, `python scripts/run_sync.py --expand --initial-batch 20 --max-requests 850`, and `python scripts/build_public_snapshot.py`. The dashboard reads the generated public snapshot. PostgreSQL remains optional until its managed service and credentials are provisioned.

## Dashboard validation: comparable periods and evidence quality

- **Historical comparison:** uses only two dates with actual validated
  observations and exactly the same repositories at both dates. It cannot
  infer a full 75-repository trend from partial or one-day snapshots.
- **CI/CD:** a single selectable 30/90-day window is applied to cards, daily
  bars, donut and evidence table. The success-share denominator excludes
  completed runs with unknown outcomes; the charts use that same denominator.
- **Coverage:** `complete` means a bounded endpoint scan finished, not that
  a repository's entire GitHub lifetime history was captured. The dashboard
  reports how many of the 75 bounded scans are complete for each source.
- **Findings:** intentionally varied finding types, with numeric evidence,
  interpretation, next checks, and original GitHub source links. No inferred
  causes, project health scores, or productivity rankings.
- **Mobile QA:** an automated browser test must open the sidebar drawer,
  capture navigation, close it, and compare it with the overview. Duplicated
  navigation and overview images fail the screenshot workflow.

Data coverage is still constrained by GitHub REST pagination, collection
windows, API quotas, and scheduled runner availability; these limitations
must be disclosed rather than hidden by manufactured or estimated totals.

## Visual-first activity trends and HR-friendly interpretation

The Dashboard now includes a **real observed daily line chart** with two tabs:
GitHub issues opened/closed and PRs opened/merged. It defaults to the last
7 calendar days (UTC) and offers 28 days. The line uses timestamped GitHub
events **only**, not fabricated observations or smoothed estimates. A value
of zero means *none in retrieved rows*, not no actual activity on GitHub.

Daily event values can be exported as CSV. Executive summary, a concise
GitHub-term glossary, source-coverage progress bars, and one-sentence
interpretation near key charts help nontechnical readers. The Explorer
includes two-repository comparison based on retrieved records, not rankings.

Historical events can be underrepresented by bounded, recent-focused API
extraction. The line chart is a **visualization of collected activity**, not
a reliable estimate of growth, productivity, backlog change, or project
success. Matched-cohort snapshot comparisons remain a separate,
conservative analytical view.

## Portfolio case study

Read [Project Delivery Monitor — portfolio case study](docs/PORTFOLIO_CASE_STUDY.md) for business context, evidence rules, limitations and interview notes.

## Coverage gates and latest data-pipeline checks

- The line chart now distinguishes **all observed records (exploratory)** from **only repositories with source-complete verified 7/28-day windows**, independently for issue and PR events.
- The public collector bootstraps at the exact 28-day evaluation window instead of wasting API pages on a redundant 30-day attempt; a long explicit reconcile can still retry 28 days before shorter fallbacks. Narrow-window success never proves a full 28-day history.
- Each scheduled run compares its source coverage against the restored baseline in its GitHub Actions step summary and audit artifacts. Completed runs and complete datasets are separate concepts.
- Review findings are ordered by transparent evidence thresholds and include original source URLs, without inventing a project-quality score.
- Browser tests exercise CSV download, two-project comparison, mobile menu, and page captures.

## Visual-first dashboard layout and screenshot evidence

The overview has a compact header and scope filters followed by four
observed KPI cards and the **daily issue/PR activity line chart**. Source
coverage details, longer methodology and the glossary are kept below the
chart in expandable sections, without concealing the selected evidence scope.
The trend's **verified-window** mode restricts data to projects whose
individual issue/PR scan covers the full requested interval. If none
qualify, the chart gives a clear explanation and a one-click switch to the
observed exploratory sample.

The first three findings display real numeric values, small observed
fraction indicators *only if a legitimate numerator/denominator exists*,
inspection actions and direct GitHub evidence links. A median duration is
never turned into an invented progress percentage.

The Playwright workflow now captures stitched screenshots of the
**scrollable Streamlit main area** for every main feature, plus the
desktop/mobile overview. Standard browser `full_page=True` is not
sufficient because Streamlit has an inner scrollbar. The source snapshots
remain real, read-only data.


## Collection improvements (November 2026)

The fixed cohort is selected from **repositories**, not ranked GitHub
contributors. Original eligibility: public and not forked/archived, at
least 50 stars, pushed in the preceding 30 days at discovery, Issues
enabled, and bounded evidence of both Issues and PRs. A round-robin
sample balances language/category and popularity tiers. Quiet repositories
are retained; the chart is not artificially made to rise.

High-volume Actions scans are split by UTC week/day, with a bounded
verified-day checkpoint saved inside the public snapshot. On scheduled
runs, completed older buckets can be reused and recent buckets rechecked
within 24 hours. This does not imply that historic run outcomes cannot
change. Requests are distributed to stale and incomplete sources.

Screenshots automatically rerun after successful source refreshes, and
benchmark steps measure real snapshot loading, analytics time, and server
memory. They are not equivalent to end-user load-speed measurements.

See [data reliability and limitations](docs/DATA_RELIABILITY.md).

## Deployment and demonstration

Deploy on Streamlit Community Cloud from repository Granbe1l/beta-test,
branch main, entrypoint streamlit_app.py. PostgreSQL secrets are not
needed for the checked-in read-only snapshot. The dashboard does not
trigger GitHub ingestion on page visits.

A working public app URL has NOT been verified; deployment must be
checked before claiming a live demo. In an interview, show an observed
finding, open its direct GitHub evidence, explain the verified 7/28/90-day
window, and demonstrate the collector's saved progress.


## Evidence-first triage and executable SQL audit (November 2026)

The finding cards use measured values and a next inspection action. Expand
**Evidence and limitations → Original records to inspect** to open a short
list of relevant source Issues, merged PRs, or failed GitHub Actions runs.
These are real records within the curated sample, **not confirmed defects**.
All four finding categories can enter portfolio-wide review prioritization;
a premature per-repository limit no longer suppresses the last type.

A separate **handwritten SQL query** summarizes real collector tables with
CTEs, JOINs, CASE conditions, aggregation and source-specific 28-day
freshness flags. It groups each source *before* joining to prevent
issue × PR × CI double-counting. This demonstrates SQL analysis without
misrepresenting the Streamlit public snapshot as a live SQL dashboard.

```bash
# From repo root, using the checked-in real snapshot:
python scripts/restore_public_snapshot.py
python scripts/sql_insights.py
```

The SQL output lists observed Issue/PR/CI values and per-source coverage
flags. Counts are observations, not complete GitHub histories, missed
deadlines, software quality, or employee-performance ratings. The CI
workflow runs these SQL statements over the real published snapshot.

See [implementation status](docs/IMPLEMENTATION_STATUS.md) for the
verified coverage gaps and [nontechnical review protocol](docs/REVIEWER_USABILITY_CHECK.md).
The review protocol is **not** evidence that HRD user testing already passed.

## Current reviewer-first dashboard and refresh reliability checks

The real-data dashboard places a **three-part quick reading** immediately
after the first activity chart: recent 7-day observed activity, one source-
linked opportunity for closer inspection, and verified 28-day Issue/PR/CI
coverage denominators. The recorded evidence is not a client delivery SLA,
missed milestone, or employee-productivity score. The rest of the six-page
visual flow and purple-white Streamlit theme remain intact.

The updated CI/CD collection algorithm **never reuses a previous check for
the current UTC day** as though it included subsequent workflow events.
The scheduled GitHub job now also runs
`scripts/schedule_reliability.py`, which audits the most recent three
**actual scheduled** workflow executions and observed 3–9 hour intervals.
Manual/push CI runs cannot satisfy the scheduled-reliability gate.
Insufficient history is explicitly reported as insufficient, never
converted into invented success.

The design can be tested using
[the five-minute nontechnical review protocol](docs/REVIEWER_USABILITY_CHECK.md),
but real participant outcomes have **not yet** been collected. Data-source
coverage improvements must be compared using actual before/after audit
artifacts after a completed refresh; code tests alone do not establish
coverage gains.


## CV-ready verified analysis without waiting 28 days

The prior 28 days of GitHub records can be inspected **now**; collecting
for 28 new days is not a prerequisite. Some large repositories still
reach REST pagination or scheduled API-request limits, so a complete
28-day window is not available for all 75 projects.

The overview includes **strict matching cohort** filters for seven or
28 days: all selected repositories must have complete source coverage
for Issues, pull requests **and** CI runs over the same chosen period.
Other monitored projects remain visible through labelled exploratory
views; missing data never count as zero activity or late delivery.

To get a dated, reproducible summary from the actual checked-in snapshot:

```bash
python scripts/cv_evidence.py
```

See [CV wording and evidence boundaries](docs/CV_EVIDENCE.md). The dated
receipt is also executed on every Quality checks run, avoiding hard-coded
estimates or the false claim that all 75 sources are verified.

## P0 data-integrity improvement: independently audited open-Issue backlog

A GitHub Issues scan with `since` only covers last-updated records;
even 28 days of complete API pagination cannot prove a full backlog.
The collector therefore supports an **independent oldest-first open
Issues inventory**:

```bash
python scripts/run_sync.py --audit-open-backlog --max-requests 850
python scripts/audit.py
```

The configured public refresh uses this option **after** normal
Issue/PR/CI collection and only with spare REST request budget. Results
have their own `open_backlog` status, never confused with verified
7/28-day activity trends. Partial pagination stays partial. Open items
missing from a completely exhausted scan are marked
`not_confirmed_open` instead of receiving a fabricated close date.

Open-work history includes `collection_basis`, making comparisons
between previous updated-event samples and newly completed open-Issue
inventories invalid rather than displaying a fake surge. The workflow
also emits per-repository diagnostics through
`scripts/coverage_triage.py`, distinguishing page limits, stale
checkpoints and short windows.

**Latest validated refresh (13 November 2026, 08:27 WIB):** 75 curated
projects; 11,652 Issue records, 26,450 PR records, 87,122 CI runs;
verified 28-day sources: Issues 40/75, PR 50/75, CI 35/75.
[Audit and published snapshot](https://github.com/Granbe1l/beta-test/actions/runs/43342299579).
Do not claim that the newly added open backlog source is fully covered
before its own real refresh audit confirms it.


## P0 verified-first portfolio and safe candidate verification

All **six Streamlit pages** now default to repositories with verified
28-day Issues, PR and CI/CD history simultaneously, controlled through a
single sidebar evidence-scope selector. A 7-day verified filter
and the original 75-project exploratory view remain accessible. Missing
records are not silently excluded from storage, and 28-day coverage means
historical records checked, **not waiting 28 calendar days**.

The current validated 2026-11-13 09:10 WIB snapshot has:
- 75 curated tracked projects, **35** with all three source types verified
  for the same 28-day period.
- Independent 28-day source coverage: Issues **43/75**, PR **53/75**,
  GitHub Actions **38/75**.
- Independently verified full open-Issue inventories: **7/75** (not
  equivalent to the event-window coverage counts).
- Observed stored records: **12,557 Issues**, **26,549 PRs** and
  **94,573 CI/CD runs**. These are retrieved observations, not complete
  lifetime repository histories.

The nonmutating [Candidate audit workflow](.github/workflows/candidate-audit.yml)
discovers real public repositories and checks 28-day Issue, PR and
CI coverage without changing the fixed original cohort. It publishes
two read-only artifacts: actual verification evidence and a diversity-
matched, unapproved candidate-replacement proposal. No replacement is
automatically performed. An unverified or low-information
candidate is not promoted merely to improve a percentage.

Large open-Issue inventories can fall back to strictly bounded
creation-date search shards when REST pagination is capped. This uses
remaining API budget and labels nonexhaustive attempts as partial.
Full-backlog aged-Issue percentages are now gated on independent
open-inventory verification; otherwise only a **labelled sample**
percentage may be shown. Historical backlog-change charts use only
matched, independently verified full-open-inventory observations.

See [P0 data integrity policy](docs/P0_VERIFIED_FIRST.md) and
[CV-ready language](docs/CV_EVIDENCE.md). P0 source coverage improvements
must be validated by new real GitHub workflow audit artifacts, never
inferred from unit tests or a hand-selected easy repository.
