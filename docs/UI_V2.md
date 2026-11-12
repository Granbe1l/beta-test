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
