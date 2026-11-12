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
