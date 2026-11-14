# Public GitHub URL Inspector

The second mode of **Explore repositories** is a **read-only, on-demand preview**.
Paste a publicly accessible root link such as \`https://github.com/psf/requests\`.
Private repositories, direct Issue/PR/file URLs, custom domains, and visitor
tokens are not accepted. The default mode remains **Tracked dataset**.

## What reviewers see

- A conspicuous **External inspection** label that distinguishes this preview
  from the separately audited fixed **50 tracked repositories**. A 50/50 Verified
  status elsewhere in the dashboard does **not** certify the inspected URL.
- The repository's original GitHub link, UTC observation timestamp, up to 30
  latest Issue/PR/CI records per source, compact observed-only KPIs, and
  evidence-linked **inspection steps** ranked by availability of source
  evidence—not a risk score or an estimate of developer performance.
- CI outcome and PR-state bar charts calculated only from returned rows.
  Pending, cancelled, skipped/neutral and failed results are counted distinctly;
  no residual category is called "successful" without evidence.
- Source-specific missing/403/429/HTTP-failure messaging, and a manually
  requested retry with a **60-second per-session cooldown**. A successful
  lookup can be cached for five minutes to avoid repeated API calls.
- Issues, PR, CI/CD source tables (original link, short title and status) and
  definitions of terms in **Evidence limits**.

## Shareable inspection evidence

A read-only CSV download includes the repository name, UTC lookup time, sample-only Issues/PR/CI observations, source-specific availability or error labels, and evidence-linked next inspection steps. Missing API data is unknown rather than zero; the file states that this project is outside the fixed 50-Verified cohort. Formula-like source text is escaped before spreadsheet export. This file **does not** update the database or qualify the searched repository for 28-day verification.

## Strict scope / limitations

The request is bounded to **four unauthenticated GET calls** to GitHub's fixed
API host: repository metadata, latest 30 updated Issues (excluding GitHub's
embedded PR objects), latest 30 PRs, and latest 30 workflow runs. A 30-row page
is never a complete 28-day scan. Total open backlog, lifetime activity,
deliverable acceptance, milestones, SLA and team productivity are **unknown**.

Errors are an unknown measurement, **not zero activity**. When a source is
unavailable, its chart and KPI are suppressed rather than implying "none."
The inspector has no database mutations; it cannot add a 51st project, revise
the fixed cohort, or change the dashboard's Verified KPI. Replacing one of the
50 tracked repositories requires a separate reviewed audit and archival
procedure with source-completeness proof.

## Evidence and acceptance

- \`tests/test_public_repo_inspector.py\`: URL allowlist, safe network boundary,
  four-call cap, error handling, false-Verified prevention.
- \`tests/test_inspector_presenter.py\`: outcome partition, source errors,
  evidence-linked inspection order, no invented full-coverage claims.
- \`scripts/capture_ui.py\`: real Playwright desktop **empty URL**, **filled URL**,
  **submitted GitHub response**, plus mobile **empty** and **submitted** captures
  and horizontal-overflow checks. These screenshot artifacts are captured
  from a running Streamlit instance and a real public GitHub repository,
  **not** fabricated illustration data.

## Deployment

The repository runs locally and in GitHub Actions; a public Streamlit Cloud URL
is **not yet independently verified**. Only the repository owner can sign in to
Streamlit Community Cloud, deploy \`streamlit_app.py\`, and provide the actual URL.
Once deployed, run the existing **Verify public Streamlit deployment**
workflow with its allowed HTTPS URL and check its rendered screenshot and
published snapshot timestamp. Do not claim a live demo before that test passes.
