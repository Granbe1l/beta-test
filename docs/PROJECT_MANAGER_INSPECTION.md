# Project Manager repository inspection (beta)

## Existing curated dataset

Use **Explore repositories → Tracked dataset**. Search among the repositories
in the chosen evidence scope by owner, name, language, or category. The
fixed 50 curated identities, saved Issue/PR/CI rows, 28-day Verified gate,
source checkpoint timestamps, and published snapshot remain unchanged.

A tracked repository missing from Verified mode must be viewed under
**All tracked · exploratory** and must not silently be treated as verified.

## Paste a GitHub URL

Use **Explore repositories → Inspect public GitHub URL** and enter
a root link such as https://github.com/owner/repository.

The inspector performs bounded, read-only **unauthenticated** GitHub REST API
calls to fixed api.github.com endpoints for metadata and at most 30 recent
records from each of Issues, Pull Requests, and Actions workflow runs.
It explicitly separates PR objects returned by GitHub's Issues endpoint.
Results are cached up to five minutes to limit API use, and each table
links to the original GitHub record. The cache is per app server, not
persistent database storage.

This mode intentionally:

- does not add to, remove from, or change the existing 50-repository cohort;
- does not claim a complete Issue backlog or complete 7/28-day API window;
- does not display invented zeros for unavailable sources or rate limits;
- does not infer project deadlines, SLAs, productivity or delivery outcomes;
- does not request, store, or reveal user-supplied GitHub credentials;
- does not support private repositories, enterprise GitHub hosts, or
  arbitrary non-GitHub URLs.

A visitor may view a **public** subordinate's GitHub project without
proving managerial authority. A **private** project requires separate,
permission-scoped OAuth or an approved organization installation; avoid
a global server token that could expose private repositories to strangers.

## Comparable metrics and exported evidence

The Explore repositories view has one **Compare projects** tab. Its first section compares two tracked projects with verified 28-day Issue/PR/CI activity windows. The adjacent 30+ day open-Issue aging metric has a different eligibility gate: a separately verified complete open-Issue inventory. An em dash signifies missing or unqualified evidence, **not zero work**. Its second section compares eligible cohort metrics without ranking teams.

On-demand public GitHub URL inspections also offer **Download this inspection (CSV)** with time, source links, review steps and explicit sample limits. The download never promotes an external project to the fixed curated 50-project cohort; spreadsheet formula-like text is escaped for safety.

## Insight update semantics

Primary curated data collection is scheduled every four hours, but GitHub
Actions timing and individual source completeness are best effort.
A refreshed snapshot can have **unchanged findings** if evidence did not
change, while a short-lived preview may change independently when its
five-minute cache expires.

The current rules are based on observed source records, not scheduled
changes to findings. The **next** analytics enhancement should compare
two successfully committed snapshots for the same source, population,
window, and timestamp. Publish change cards only with validated comparable
denominators, and distinguish true new events from sliding windows or
stale-to-fresh changes. Daily briefs should use a clearly stated UTC/WIB
boundary and avoid claims about missed business deadlines.
