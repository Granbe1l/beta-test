# P0 data integrity and verified-first portfolio policy

Updated 14 November 2026.

## Main dataset and candidate sources

- **Tracked:** retain the 50 reviewed Verified-at-selection public GitHub repositories
  and their source records. An incomplete source is not evidence that a
  repository is inactive, broken, or unsuitable.
- **Verified analysis:** one global sidebar selector filters **all six
  pages** to the same cohort with complete Issues, PR and CI/CD history
  for the prior 28 days. It falls back to seven days if no repository
  qualifies, then to explicitly warned exploratory data. The original
  total tracked remains distinct from analyzed source denominators.
- **Exploratory:** all selected 50 remain accessible with the source
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

Result: \`candidate-verified-audit.json\` and
\`candidate-replacement-plan.json\` as retained workflow artifacts.
The second file produces **unapproved nonmutating proposed swaps** only
when original and candidate repository categories AND size tiers match.
Neither file automatically modifies the 50-project current selection (25 source reports archived separately).
Even a verified candidate is **not automatically promoted or substituted**.
Replacement requires a dated selection manifest, a review of language and
size/category diversity, and a complete saved audit for both old and new
cohorts. Existing repository records are never deleted to inflate 50/50.

Important selection caveat: favoring sources that can fit REST pagination
limits can bias the verified cohort toward quieter or smaller projects.
Never describe the cohort as representative of GitHub at large or as
a ranking of developer performance.

## November 14 P0.1 verified replacement expansion

The most recent available real source-audit artifact from the successful
November 13 17:48 UTC refresh had **31 of 75 original repositories**
verified on all three Issues, PR, and CI/CD sources for the SAME complete
28-day window. The new immediate portfolio target is **at least 50 of 75**,
which requires at least **19 additional genuinely verified active repos**
from that baseline.

**First step (this PR):** the independently auditable candidate workflow
searches a diversified pool of up to **96** eligible public repositories
and probes at most **32** every **six hours**. Each run has a hard GitHub
request budget of **850**, and a new early-failure order checks CI/CD and
PR coverage before potentially expensive Issues history. Candidates
must still pass the unchanged *all three sources, complete 28 days,
minimum real records* requirements. A 7-day fallback, 404, partial
pagination, stale checkpoint, or quota exhaustion does not qualify.

**Important:** faster scouting is not the same as replacement. The
original selection is untouched in this stage. A verified candidate must
be checked against up-to-date evidence and ingested into the stored
snapshot, with old records retained and a documented selection change,
before it is promoted. These enhancements **do not** claim 50/75 yet.
GitHub's scheduled jobs may be delayed, and the 850-call limit may cause
fewer than 32 probes; exact completed counts belong to the run artifacts.

The earlier candidate proof (Nov 13 03:15 UTC) found 3 verified candidate
repositories and 2 matched-category-and-size proposals. That audit is
more than 12 hours old at this update, so it is *not* a fresh swap
authorization. Never copy those results into a claimed count of
active Verified repositories.

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
  evidence or unverified 50/50 completeness.

These gates avoid gaming a CV metric. The project is usable today using
a verified subset and its honest denominator, with follow-up work for
sources whose GitHub API histories remain capped.
