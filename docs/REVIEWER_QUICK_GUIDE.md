# Project Delivery Monitor — 60-second reviewer guide

**What is this?** A public GitHub engineering-activity analysis across 50
curated software repositories. It helps reviewers decide **which original
record to inspect next**; it does not know client deadlines, delivery costs,
milestones, SLAs, private team capacity or software quality.

## Find one credible insight

1. **Dashboard (10 seconds):** Look at recorded activity over the last seven
   days, and the number of projects with verified 28-day Issue, PR and CI
   source coverage. Activity is not proof that a release was delivered.
2. **What should we inspect? (20 seconds):** Read a measured observation,
   its relevant count/denominator and the suggested next check.
3. **Original GitHub record (20 seconds):** Open the Issue, PR or Actions run.
   Inspect the discussion, labels, branch or logs before accepting a claim.
   A repository listing is only a starting point, never individual proof.
4. **Verify the scope (10 seconds):** Use `Verified · 28 days` for strictly
   completed source windows. `All tracked · exploratory` includes incomplete
   records, where missing does not equal zero.

## Common terms and their limits

| Label | What it means | What it does **not** establish |
| --- | --- | --- |
| Issue | Public GitHub task, question or bug | A missed deadline |
| Pull request (PR) | Proposed code change | Employee productivity |
| Median merge time | Typical creation-to-merge interval among merged PRs in the selected, verified period (minimum five) | All open changes are blocked or efficient |
| CI result | Outcome of a GitHub Actions workflow run | Overall software quality |
| CI success share | Successful completed runs divided by all known completed outcomes; skipped/cancelled/neutral remain in the denominator | Skipped or cancelled outcomes are failures |
| 30+ day Issue age | Age of a currently observed open Issue | Work is overdue |
| Verified 28 days | Three source windows fully scanned over the same past four weeks | Complete project lifetime or guaranteed delivery |

**Cross-project comparison:** Similar-looking numbers can represent projects
of very different sizes and categories. Treat category medians and percentiles
as descriptive context for this **non-random sample**, not rankings.

**Where to look:** `Explore repositories` compares tracked projects, while
`Inspect public GitHub URL` creates a small, independently fetched external
preview that is never automatically marked Verified or added to the 50.

**Evidence status:** automated tests and browser audits exist, but actual
nontechnical participant comprehension has **not** been evaluated.
