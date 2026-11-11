# Project Delivery Monitor — Open-Source Analytics

**Author:** Candy Ristyan · **Stack:** Python, Streamlit, Pandas, Plotly, SQLAlchemy, PostgreSQL, GitHub REST API, GitHub Actions, Pytest.

An evidence-first, read-only dashboard for reviewing observable software-development activity in a **curated, explicitly non-representative sample** of GitHub public repositories. Designed to be understandable by nontechnical HR reviewers while preserving defensible denominators and source links.

> **Review build, not a production release.** Source code is on branch `review/project-delivery-monitor-streamlit` in [Granbe1l/beta-test](https://github.com/Granbe1l/beta-test). No managed PostgreSQL, verified live ingestion, production dashboard, actual browser screenshots or scheduled collection are active. **Do not interpret fixture records as live findings.** The default `main` branch holds only a short initialization README and has no schedule or deployment.

## Questions answered

1. What work-item and CI activity is observable within the configured sample?
2. Which observed open-issue sets have larger 30+ day shares?
3. What is the median time from creation to merge among merged PRs?
4. Did issues closed in the most recent 28 days increase or decrease against the preceding 28 days?
5. What evidence underpins the most important findings?
6. Which review action can a human take next?

Issue age alone does **not** establish lateness. PR merge duration does **not** prove productivity. CI success rates do **not** measure overall software quality. No single-metric repository quality ranking is produced.

## Dashboard navigation

| Area | Purpose |
|---|---|
| Overview | Executive summary, at most three quantitative findings, observed KPIs, up to two relevant charts, suggested reviews and coverage |
| Repository Explorer | Compact searchable, filterable, sortable table with GitHub URLs |
| Repository Analysis | Issue aging, PR merge duration, opened-vs-closed weekly activity, CI and source evidence |
| Cross-Repository Comparison | Contextual comparison by category, window and metric with sample limits |
| Findings & Methodology | Auditable evidence, selection decisions, denominators, data integrity and synchronization status |

Theme: **Midnight Navy / Ice Blue**, light background, responsive CSS over native Streamlit. Real desktop and mobile visual testing is still needed.

## Architecture

```text
GitHub Search API -> bounded candidate discovery -> eligibility validation
                                              -> auditable diverse sample (<=20)
GitHub REST issues / pulls / actions/runs -> normalization -> SQLAlchemy
                                              -> PostgreSQL (SQLite local)
                                              -> checkpoints + sync logs + observations
GitHub Actions (6-hour schedule / weekly reconciliation) -> read-only incremental GET
Persisted data -> deterministic KPI/insight calculations -> Streamlit cache (600s)
```

The Streamlit page does **not** initiate full data ingestion on each visit.

## Repository selection

- **Public** repositories; exclude forks and archived repos.
- **50+ stars** used solely for first-pass filtering, never as a quality score.
- Recent `pushed_at` within configurable 90 days.
- GitHub issues enabled; bounded probes must find a standalone issue and a PR.
- Search queries cover Python, TypeScript, Go, Rust, Java, Kotlin, C++, and Ruby ecosystems.
- Maximum **75 distinct candidates** and **20 selected repos** by default.
- Candidate metadata, rejection reasons, search parameters, selection time and GitHub evidence URL are persisted.
- Diversity is pursued through language-category and star-size round-robin, rather than simply sorting by most stars.
- Normal synchronization does **not** silently add new repositories.
- Search API pagination and search result caps mean this is not a sample representative of all GitHub repositories.

Uncertain negative activity probes are logged as such. If fewer than 20 repos qualify, the app only uses the actual eligible count.

## Sources and incremental collection

| Source | Endpoint / strategy |
|---|---|
| Issues | `GET /repos/{owner}/{repo}/issues`, `state=all`, descending updated timestamp, `since` |
| Pull requests | `GET /repos/{owner}/{repo}/pulls`, `state=all`, descending updated timestamp, local cutoff; **no unsupported since parameter** |
| GitHub Actions | `GET /repos/{owner}/{repo}/actions/runs`, created-date filter; **not** an updated/since cursor |
| Repository search | `GET /search/repositories` with bounded language-specific queries and pagination |

The collector excludes the `pull_request` items that can appear in GitHub's issues endpoint. Every source row is validated for GitHub ID, repository ID, timestamps, and valid GitHub evidence URL.

Checkpoints are stored **per repository and data type** with high watermark, coverage start, last successful sync, pages and record counts, status and safe errors. Records use stable global GitHub IDs, unique issue/PR constraints and idempotent upserts. An overlap window reduces missed recent changes; workflow runs use a longer window and scheduled weekly reconciliation. Failure rolls back incomplete writes and does **not** advance the last-success timestamp. A capped pagination traversal is marked `partial`, not complete.

GitHub is accessed using read-only **GET** requests. API timeouts, bounded retries with exponential backoff and rate-limit responses are handled. PostgreSQL advisory locks, local SQLite lock files and Actions concurrency prevent overlapping writers.

**Important:** Even an exhausted bounded updated-at collection can exclude older issues that have not changed recently. Reported open issues and their age share refer to the **observed sample**, never the whole historical backlog.

## Metric definitions and safeguards

| KPI | Formula / denominator |
|---|---|
| Observed open issues | Count of non-PR source records with state open in collected scope |
| Open issues 30+ days (%) | Observed open issues at least 30 days old / all observed open issues * 100; comparison needs at least 5 |
| Issue activity | Created and closed issue events by UTC week; requires covered window |
| Issue closure change (%) | (last 28-day closures - prior 28-day closures) / prior closures * 100, suppressed when prior=0 |
| Open and draft PRs | Draft PRs are a subset of open PRs |
| Merged and unmerged closures | `merged_at` and `closed_at` events within the observation window |
| Median merge days | Median of (merged_at - created_at), merged PRs only; requires at least 5 merges |
| CI success share | Completed runs with conclusion success / completed runs with known outcome * 100; skipped counts in denominator |
| Review compliance | **Not Available** until consistent approval-review event coverage/policy is implemented |

Results are suppressed as **Insufficient Data / Not Available** if the relevant source is partial, stale, failed, unavailable, or too small for an asserted comparison. Summaries and findings are deterministic from persisted records and include evidence, careful interpretation, next review and original GitHub links.

## Local setup

Requires Python 3.12+.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env  # PowerShell: Copy-Item .env.example .env
python scripts/init_db.py
python scripts/run_sync.py --discover
python scripts/audit.py
streamlit run streamlit_app.py
```

Local database defaults to `sqlite:///local.sqlite3`. Add a read-only GitHub token in ignored `.env` for higher API budgets, or rely on lower unauthenticated limits. The CLI selection is explicitly triggered with `--discover`; later calls can run `python scripts/run_sync.py` or `--reconcile`. The repo contains no preloaded production records.

Test locally:

```bash
python -m compileall -q src scripts streamlit_app.py
python -m pytest -q
```

The test suite includes controlled cases for discovery, deduplication, pagination, retries, incremental overlap, failure rollback, upsert idempotency, separation of issue/PR, denominators, median, source health, UI empty-state/CSS presence, and a fixture-driven ingestion-to-findings path. These tests **do not prove live GitHub ingestion or mobile-browser compatibility**. Previous local result: 26 passed and one Streamlit runtime test skipped because the package was unavailable.

## Persistent PostgreSQL production setup (not activated)

1. Provision an actual managed PostgreSQL service, such as Neon, Supabase or Render.
2. Configure TLS and a minimally privileged database user.
3. Supply a real `DATABASE_URL` to GitHub Actions Secrets and Streamlit Cloud Secrets, **never to source control**.
4. Add an appropriately scoped read-only GitHub token to GitHub Actions secrets.
5. Initialize schema (`scripts/init_db.py`), explicitly run initial selection, then audit record counts and source coverage.
6. Only with owner approval, bring the sync workflow onto the **default `main`** branch. GitHub Actions scheduled workflows are inactive on a non-default feature branch.
7. Deploy Streamlit Community Cloud from the approved branch using entry point `streamlit_app.py`; set matching managed database secrets.

The workflow config uses cron `17 */6 * * *` and a weekly reconciliation `43 3 * * 0`, plus `workflow_dispatch` flags. GitHub's scheduled tasks may be delayed or disabled for inactive public repositories. Streamlit Community Cloud is **not** treated as a scheduler. Production synchronization cannot be called operational until PostgreSQL/secrets are configured and real runs have been audited.

## Secrets and evidence

Never commit the real `.env`, `.streamlit/secrets.toml`, password-bearing DATABASE_URL, tokens, or a production database file. Example configuration values are placeholders. The local SQLite database and lockfile remain outside the tracked source.

No real collection totals, selected repository list or quantitative findings are claimed in the current review release. To get verified counts, execute `python scripts/audit.py` against a database filled by actual GitHub API collection; follow its evidence links and inspect checkpoint statuses.

**Actual screenshots:** pending. Once Streamlit is running in a browser, add real desktop and mobile captures under `docs/screenshots/` and link them here. Do not substitute invented screenshot images.

## Source organization

```text
streamlit_app.py
src/config/          environment settings
src/discovery/       auditable GitHub Search selection
src/collectors/      REST client, normalization and incremental sync
src/database/        schema, sessions and idempotent writes
src/analytics/       deterministic metrics, findings and source reads
src/ui/              Streamlit views and CSS
scripts/             initialize, synchronize and audit
tests/               controlled automated regression tests
.github/workflows/   quality checks and scheduled collector definitions
.streamlit/          visual theme and example secrets
docs/                implementation status and phase checkpoints
```

For remaining limitations and a continuation checklist, read [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md). No merge or deployment is authorized by this review upload.
