# Evidence-ready CV presentation — no 28-day waiting period

**Purpose:** Use Project Delivery Monitor now with defensible claims about
public GitHub data. There is **no 28-day waiting period**: the term
"verified 28-day window" means GitHub returned a complete scan of historical
activity covering the **previous** 28 days. A repository with capped
pagination is excluded from *verified-period* charts and kept available for
clearly marked exploratory review.

## What to show on the Streamlit dashboard

The overview includes two additional Activity filter options:

- `Verified all three sources · 7 days`: **exact same** source-eligible
  repositories have verified Issue, pull-request and GitHub Actions history
  over the last seven days.
- `Verified all three sources · 28 days`: the stricter, **same-cohort**
  comparison over 28 days.

These subsets can differ in size and must always show the **actual denominator**;
they may correctly show all 50 only when the dated source audit verifies them.
The data-readiness caption displays the exact joint denominators
computed live from the loaded real snapshot. Selecting all projects keeps
the exploratory sample and existing source-specific verified trends.

For a reproducible numbers-based receipt run:

```bash
python scripts/cv_evidence.py
```

CI runs this against the **real checked-in GitHub snapshot**, with exact
source record counts, UTC snapshot timestamp, independent 7/28-day source
coverage and matching three-source cohort sizes. **Never copy old counts
without refreshing their snapshot timestamp.**

## CV wording — English (ATS-friendly)

**Project Delivery Monitor | Python, SQL, Streamlit, GitHub REST API, GitHub Actions**

- Developed an analytics dashboard for observable engineering activity
  across **50 curated public GitHub repositories**, integrating issues,
  pull requests and CI/CD workflow runs.
- Built a bounded incremental collection pipeline with source-level
  completeness checks, reproducible SQL aggregates and evidence-linked
  issue/PR/CI analysis.
- Distinguished **verified 7/28-day matched source cohorts** from
  incomplete exploratory records to prevent misleading trends or
  unsupported claims about delivery performance.

For a one-line CV, use the first two bullets or combine them.
**Do not reuse old examples with hard-coded Issue/PR/CI counts**: source
records update as GitHub Actions publishes new snapshots. Generate the
current evidence receipt with `python scripts/cv_evidence.py`, record its
UTC snapshot timestamp, and report the result as **observed source records**,
not the complete lifetime activity of all 50 repositories. If space permits,
a defensible engineering proof is that the historical real restored 75-repository
SQL query loader was tested at **6 SELECTs versus the previous 376 SELECTs**
([P2.1 CI evidence](https://github.com/Granbe1l/beta-test/pull/15)).
Do not present that as a browser load-time improvement.

## Optional evidence-first analytics bullet

- Developed three **conditional source-backed case walkthroughs** using real
  public GitHub Issue, Actions and PR records, verified source denominators,
  and explicit inspection decisions; checked links and KPI integrity in CI.
  [Dated examples and limits](EVIDENCE_CASE_STUDIES.md).

This demonstrates analytical discipline and traceability. It does **not**
prove that a repository missed deadlines or that a proposed action was
implemented by its maintainers. Keep this bullet only if the interview
allows enough time to explain the evidence.

## Optional technical-impact bullet for data / IT roles

- Optimized SQL-based snapshot loading from **376 to 6 SELECT queries**
  across the historical 75-repository dataset; validated source-row parity
  with SQLite and the compressed GitHub snapshot in CI.

This was a measured SQL **query-count reduction**, not a claimed
98.4% decrease in page latency or proof of production hosting uptime.
The project also retains direct GitHub source links and explicitly
distinguishes incomplete exploratory histories.

## Bahasa Indonesia

- Mengembangkan dashboard analisis aktivitas pengembangan perangkat
  lunak dari **50 repository GitHub publik terkurasi**, memanfaatkan
  Python, SQL, Streamlit, GitHub REST API, dan GitHub Actions.
- Mengimplementasikan pengumpulan data inkremental, pengecekan
  kelengkapan sumber, analisis Issue/PR/CI, serta tautan bukti langsung.
- Memisahkan data periode 7/28 hari yang terverifikasi dari sampel
  eksploratif untuk mencegah kesimpulan menyesatkan.

## What not to claim

A [dated 14 November 2026 source audit](https://github.com/Granbe1l/beta-test/actions/runs/43547169286)
**did** verify 50/50 complete 28-day Issue/PR/CI sources and separately
50/50 fresh full-open Issue inventories. You may state that **dated**
result with its verification link, but do **not** imply permanent
50/50 coverage, continuous 24/7 uptime, live real-time data, employee
productivity rankings, confirmed missed deadlines, customer SLAs,
or comprehensive GitHub history. The fixed cohort is not a random statistical sample and is
not representative of every GitHub project.

Use [actual source coverage and remaining gates](IMPLEMENTATION_STATUS.md)
and [nontechnical review protocol](REVIEWER_USABILITY_CHECK.md) for
interview evidence. Human usability testing remains unverified.
