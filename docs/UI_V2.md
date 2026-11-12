# Project Delivery Monitor · Visual-first UI V2

This version is designed to be easier for nontechnical reviewers. The home screen
explains the sample, highlights verifiable KPIs, and leads with charts and short
evidence-backed findings. It uses a purple/white layout with a dark sidebar.

## Six sections

| Navigation | Visual answer |
| --- | --- |
| Dashboard | Work in progress, age of open issues, CI check outcomes, weekly issue activity, review candidates |
| Explore repositories | Project-specific figures, observation history, comparison, coverage |
| Open issues | Age groups, opened/closed trend, searchable original GitHub issues |
| Changes & reviews | Open PRs, merge-duration distribution, searchable original PRs |
| Build activity | Daily GitHub Actions results, outcome mix, workflow links |
| Key findings | Short source-backed follow-up opportunities and methodology |

## Implementation

- Entrypoint: streamlit_app.py
- New visual pages: src/ui/dashboard_v2.py
- Purple/white style: src/ui/theme_v2.py
- Legacy UI helpers: src/ui/pages.py and src/ui/theme.py (retained)
- Data contracts: src/analytics/read.py and src/analytics/snapshot.py (unchanged)

All figures are based on collected public GitHub records, not fabricated metrics.
Incomplete collection can suppress KPIs, and retrieved subsets are explicitly labelled.
Issue age is **not** an overdue deadline, and GitHub Actions success is **not**
a project-quality score. Project comparisons are descriptive, not performance rankings.

View refresh **does not** trigger the GitHub collector. Updating the snapshot
uses the existing GitHub Actions workflow.

## Validation

- Run existing automated tests: python -m pytest -q
- Run the app: streamlit run streamlit_app.py
- Check desktop and mobile navigation, charts, source URLs, filter behavior,
  missing-data states, and partial/stale source disclaimers.
- If a public snapshot is old, check the scheduled collection workflow and
  its last successful run; a manual UI refresh alone does not update the source.

No claim is made that the visual UI has been browser-tested merely by committing
the source code. Screenshots require a successful Streamlit deployment.


## Evidence-first UI improvements (revision)

- Sidebar uses six native Streamlit buttons with plain feature names and a
  visible selected state; the former radio circles are gone.
- Overview KPI counts and charts use the **same retrieved rows**. These are
  not estimates of complete project activity. A visible coverage strip
  reports verified issues, PRs and workflow sources separately.
- Weekly opened/closed issue activity uses observed rows and is explicitly
  identified as incomplete when applicable.
- Findings may use a verified issues or PR source even if some other source
  types remain incomplete. Each finding still has denominator thresholds.
- Repository composition comes from public GitHub metadata; no project score,
  ranking or fabricated risk indicator was introduced.

Design references (patterns, not copied code):
- https://github.com/pingcap/ossinsight — clear repository exploration and
  project comparisons.
- https://github.com/chaoss/grimoirelab-sigils — separation of overview,
  source-specific dashboards, and source filters.
- https://github.com/ParthibanRajasekaran/delivery-intel — explicit evidence
  and sample size per metric; no adoption of its scores or DORA estimates.

Updated screenshot tests should cover all six navigation destinations and
repository Explorer tabs. The screenshots are captures from real Streamlit
browser sessions, not generated mockups.

## Ongoing development vs static snapshots

- The selected cohort contains 75 public repositories; selection requires
  recent GitHub pushes (within 30 days) and observed issue/PR evidence.
  A push is not proof of active feature development.
- Each scheduled run queries GitHub, updates repository `pushed_at` for
  visited projects, and persists source records as a new snapshot on `main`.
- The dashboard filters recent pushes, recent issue/PR activity, and quieter
  projects; it shows eight-week trends using event timestamps from actual
  collected issue/PR records. It does not fabricate changes merely to make
  a line graph move.
- Some repositories may become quiet later. They remain in the historical
  sample so trend comparisons are not biased by continual silent replacement.
- Six-hour schedule is an **attempt**, not guaranteed freshness for every
  source or immediate updates in the Streamlit browser. Source and snapshot
  timestamps explain partial/stale data.
- GitHub Actions workflow uses a schedule/manual trigger and safe
  publication of the binary public snapshot to prevent stale rebase conflicts.

## UI revision: comparable evidence (13 November 2026 release)

- Replaces the misleading rising eight-week line (older GitHub events are
  frequently undercollected) with a strict matched-cohort, two-date
  observation comparison. When there is no comparable historical pair,
  a descriptive 7-day event breakdown appears instead.
- Uses the same 30/90-day time window for GitHub Actions cards, daily
  outcome bars, outcome donut, and the source evidence table. Unknown
  conclusions are excluded from the shared success-share denominator.
- Limits finding cards to distinct evidence types; includes actual evidence,
  what can be inferred, next steps, and links to original records.
- Shortens the hero on mobile, aligns Activity/Repository filters in two
  desktop columns, and verifies the sidebar's opened/closed states through
  browser-driven screenshots.
- Source-complete means **bounded recent-window scan complete**. It is
  not a claim of complete project activity or full GitHub history.

## Chart design V3: purpose before decoration

| Question | Visualization | Why |
| --- | --- | --- |
| What share of automated checks passed? | Donut with explicit known-outcome denominator | Part-to-whole |
| How old are open issues across the whole sample? | Horizontal categorical bars | Compare ordered counts |
| What fraction of one repository's observed open issues fall in each age band? | Donut with count and age caution | Composition |
| How many PRs merged in each duration band? | Distribution columns | Compare ordered buckets |
| How did open work change for the same repositories? | Two-point slope lines, separated per metric | Honest matched-date net change |
| Which sampled repositories show observed activity? | Stacked horizontal bars (issue vs PR events) | Compare composition of activity without pretending ranking quality |
| What happened to automated checks by week? | Stacked weekly columns + outcome donut | Trend-like distribution and total composition using one time window |

Labels use counts and units; captions explain the limits of recent-window public
GitHub collection. Every visual is derived from the same read-only snapshot.
No fabricated scores, new external data sources or artificial up/down lines.

## V4 · Observed daily line chart and readable insights

- Priority line chart added directly below the four overview KPI cards:
  issues opened vs closed or pull requests opened vs merged.
- Data is built from real UTC dates and issue/PR timestamp fields; no API
  history is invented. User can select 7 or 28 days and download the exact
  displayed daily values as CSV.
- New executive summary and glossary define Issue, PR, merge and CI/CD in
  nontechnical language.
- Source completeness shows explicit proportions for Issues, PRs and
  GitHub Actions, with a bounded-scan disclaimer.
- Explorer has an optional "Compare two projects" tab with observed counts
  and direct links to both GitHub repositories.
- Source evidence limitations and plain-language interpretations remain
  visible; unmatched historical snapshots cannot be mistaken for growth.
- Browser screenshot workflow captures both line-chart tabs separately.


## V5 · Source collection completeness (adaptive, verified window)

- Scheduled six-hour GitHub REST collection bootstraps up to **20 previously
  unvisited repositories** per run, within the existing **850-request cap**.
  It retains a stable 75-repository curated cohort rather than replacing
  quieter repositories to make plots move.
- The first incremental source scan targets 30 days; if a repository has
  more than the six-page cap, the collector retries 7 days then 1 day.
  Results from every successful attempt are **upserted**, so useful older
  records are not discarded. Explicit \`--reconcile\` still attempts the full
  backfill, with an honest shorter-window fallback if pagination overflows.
- A source can only be marked complete when GitHub pagination actually
  exhausts the selected window. Its \`coverage_start\` is the **actual
  completed window**; a successful 1-day scan is NOT 28/90-day coverage.
  Partial scans never advance source success timestamps.
- If the API budget is nearly depleted, no speculative retries are issued;
  unvisited sources retain their prior checkpoints and records.
- After bootstrap, the collector rotates repositories and gives extra turns
  to partial/stale sources while reserving turns for already-complete ones,
  avoiding starvation.
- Data coverage UI and audit distinguish: (a) number of bounded scans
  completed and (b) number with **verified 28-day coverage**. A "complete"
  one-day scan must never be presented as full GitHub history.
- Every collection run produces \`snapshot-audit.json\` with source
  complete/partial/stale/unavailable counts and 28-day readiness.
- Collection may remain partial for very busy repositories even with a
  one-day window; the proper response is additional targeted collection or
  a narrower time scope, not manufactured coverage percentages.

These improvements are code changes. Existing snapshots do not magically
gain data when the UI is refreshed; source coverage changes only after a new
successful GitHub Actions collection publishes a new snapshot.

## Reliability-first revision · November 2026

- Trend chart now offers explicit **Exploratory** versus **Verified source window** scope. Verified mode excludes incomplete, stale or short-window repository sources; separate issue/PR source readiness and CSV cohort sizes are shown.
- Dashboard prioritizes KPI → executive summary → trends; long coverage explanations and glossary are in expanders following the chart.
- Review insights use transparent priority labels and are sorted by evidence types, not by project popularity, developer output or an opaque score.
- GitHub collector retries a **28-day** window before **7-day** and **1-day** bounded fallbacks; the real certified start time is stored.
- Source-audit before/after counts are attached to each scheduled GitHub Actions run and summarized in the workflow report. A passed UI test does not prove the scheduler refreshed actual source data.
- Browser screenshot test additionally checks the real CSV download and the two-project comparison tab. A separate [portfolio case study](PORTFOLIO_CASE_STUDY.md) explains the analysis and limits.

## Visual hierarchy and screenshot coverage · Nov 2026

- Overview order: compact title → filter → four KPIs → real activity line chart
  → quick interpretation → three evidence-backed visual insight cards
  → secondary age/CI charts → snapshot comparison → additional exploration.
- Caution for exploratory data is a concise always-visible note next to
  the chart. A source-methodology expander holds longer explanations;
  verified-window empty states have a specific action to inspect the
  sampled observations without claiming validated full coverage.
- Issue-age and CI success findings use native proportion indicators with
  observed counts and denominators. Merge duration uses its own observed
  median, **not** a fake progress share.
- Common purple = new/opened; green = resolved/merged/success; red = failures.
  Every chart labels its period explicitly; 7-day, 28-day, 30-day, and
  90-day summaries are not silently mixed.
- Desktop and mobile viewport screenshots are kept alongside stitched
  `*-full.png` images of the inner scrollable main section. Those full
  captures reveal charts and tables hidden below the first viewport.
