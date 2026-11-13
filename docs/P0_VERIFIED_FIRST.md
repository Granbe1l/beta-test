# P0 data integrity and verified-first portfolio policy

Updated 13 November 2026.

## Main dataset and candidate sources

- **Tracked:** retain the original 75 selected, public GitHub repositories
  and their source records. An incomplete source is not evidence that a
  repository is inactive, broken, or unsuitable.
- **Verified analysis:** the Streamlit overview initially selects the
  exact intersection of repositories with complete *Issues, PR, and CI/CD*
  scans covering the **previous 28 days**. When no such repository exists,
  it falls back to 7 days; if neither works, it uses an explicitly
  exploratory selection, never a fictitious empty/zero series.
- **Exploratory:** all original 75 remain accessible with the source
  denominators and a visible missing-data caveat.
- **Candidate pool:** a separate, nonmutating read-only workflow discovers
  public repositories using the same GitHub activity, source eligibility,
  language and star conditions. It verifies 28-day GitHub Issue, PR and CI
  scans for the same repository, requiring actual source rows. A completed
  one- or seven-day fallback does NOT pass the 28-day requirement.

Run read-only scouting through the **Audit verified replacement candidates**
GitHub Actions workflow, or with:

\`\`\`bash
python scripts/audit_candidate_pool.py
\`\`\`

Result: \`candidate-verified-audit.json\` as a retained workflow artifact.
Even a verified candidate is **not automatically promoted or substituted**.
Replacement requires a dated selection manifest, a review of language and
size/category diversity, and a complete saved audit for both old and new
cohorts. Existing repository records are never deleted to inflate 75/75.

Important selection caveat: favoring sources that can fit REST pagination
limits can bias the verified cohort toward quieter or smaller projects.
Never describe the cohort as representative of GitHub at large or as
a ranking of developer performance.

## P0.2: old open-Issue inventory

The REST Issues \`since\` parameter selects **last-updated records**. It
does not discover every long-lived open Issue. A separate open-backlog
source first tries the oldest-first \`state=open\` REST endpoint. When
the result hits the page cap, the collector tries Github Search issues
with \`repo:<owner>/<name> is:issue is:open created:<start>..<end>\`.
If the returned count exceeds the accessible result window (or
\`incomplete_results\` is true), the date-time interval is bisected.
Individual response pages and immutable Issue IDs are validated.
A partial or budget-interrupted search never becomes a complete inventory.

GitHub Search has special rate limits and cannot guarantee a perfectly
atomic snapshot while Issues are changing. The search attempt uses a
bounded number of calls and leftover scheduled collection budget.
Full-backlog timestamps describe the completed audit instant, not a
live 24/7 consistency guarantee.

Audits prioritize the existing cohort with 28-day verified source
history, with deterministic rotation so a single high-volume project
cannot indefinitely starve other candidates. Older records are retained.
When a fully exhausted current-open scan no longer includes an old
record, the stored Issue is marked \`not_confirmed_open\`; **no closing
timestamp is invented**.

## P0.3: meaning of KPI and charts

1. \`sample_aged_percent\` and \`sample_aged_denominator\`: age share of
   only the retrieved open-Issue sample. Always labelled **sample**.
2. \`aged_percent\` and \`aged_denominator\`: available **only** after an
   independently complete, fresh open-backlog inventory.
3. A complete 7/28-day updated-event scan validates **events in the
   period**, **not** the number of all still-open Issues.
4. Backlog change charts only compare the *same repositories* using two
   independently verified full-open-inventory observations. Two separate
   partial samples may never be reported as true backlog growth.
5. No full-open PR inventory exists; open-PR sample changes are therefore
   excluded from the verified Issue-backlog-change chart.
6. No missing sample or stale source may be treated as evidence of zero
   activity, missed client deadlines or employee productivity.

## Measurement gates for P0 completion

- CI passes Python tests, real restored GitHub SQL audit and screenshots.
- Snapshot publishing preserves source IDs, last successful checkpoints,
  and audit trail, even when the remaining API budget is insufficient.
- The independent open-Issue inventory is checked by **actual GitHub API
  collection**. Status remains partial when Search query windows are not
  fully exhausted or API is limited.
- Candidate reports show exact pass/fail reasons, all three source
  verification flags, source counts, sample diversity and the UTC time.
- New repositories enter a selection **only** through a separate
  audited, explicitly documented promotion; no rewrite of historical
  evidence or unverified 75/75 completeness.

These gates avoid gaming a CV metric. The project is usable today using
a verified subset and its honest denominator, with follow-up work for
sources whose GitHub API histories remain capped.
