# Five-minute nontechnical review — test protocol

**Purpose:** verify whether someone unfamiliar with GitHub can interpret
Project Delivery Monitor without confusing public development activity with
private consulting milestones or employee performance. This is a test
protocol, **not** a claim that user testing has already taken place.

## Participants and setup

Ask 3–5 people who have not built the app, ideally including at least
two without GitHub or software-development experience. Use the current
real 50-repository snapshot. Record device type (desktop or mobile)
without collecting names, private accounts or personal data.

Provide the dashboard without verbal coaching. Do not explain "PR", "CI/CD"
or "coverage" unless the participant explicitly asks; note that request.

## Tasks

| Task | Intended success criterion |
| --- | --- |
| 1. Explain what the dashboard tracks | Says public GitHub issues, code changes and automated checks; does **not** claim project deadline/SLA measurement |
| 2. Find one project that merits closer inspection | Identifies a source-linked finding and the actual measured reason |
| 3. Show the supporting evidence | Opens an Issue, PR or workflow-run record from the finding's expander |
| 4. Explain a verified vs exploratory trend | Recognizes that missing GitHub API records cannot be treated as inactivity |
| 5. Explain one next action | Can describe a sensible follow-up review, without declaring a confirmed defect |

## Scoring and acceptance

For each task, mark **completed independently / completed with hint /
not completed**. Record misunderstood labels, false conclusions, failed
links, time-to-first-insight, and any layout overflow. Do not invent
participant responses or fabricate a usability percentage.

Release-readiness checks:
- No participant should infer that the dashboard measures customer SLAs or
  guaranteed delivery dates from the wording alone.
- At least 4/5 tasks should be completed independently by each participant,
  with confusing tasks corrected and retested.
- Each surfaced finding must contain a count or measured value, a review
  rationale, a bounded data scope, and a real source link.
- Check mobile width ~390px and desktop ~1440px with browser screenshots.
- Record testing date, snapshot timestamp, consent, tasks attempted,
  observed results, code changes and follow-up test outcomes.

## Reporting template

| Date / device | Participant (anonymous code) | Task 1–5 outcomes | Confusing wording | Change made | Retest result |
| --- | --- | --- | --- | --- | --- |
| Not tested yet | — | — | — | — | — |

Do not mark this document "passed" before real participant evidence exists.

## One-minute guide implemented (automatic check, not human sign-off)

Each of the six Streamlit screens now has a sidebar
**Reading guide · 1 minute**. It explains repository, Issue, PR,
CI/CD check, Verified and Exploratory with plain-language wording.
Navigation controls have short explanatory tooltips, and the selected
scope explicitly explains that a fully scanned **period** does not
establish a full lifetime backlog or software quality. Automated
browser checks open the guide at desktop width and confirm the
incomplete-data warning is actually rendered.

**Still required:** 3–5 external nontechnical people completing the
five tasks above. Use the blank, nonsynthetic
[reviewer result form](REVIEWER_RESULT_FORM.csv). Each participant
may remain anonymous and should not enter private GitHub credentials.
No user scores or participant observations have been invented.

A real participant's first unexplained interpretation is the key
outcome. If someone calls an Issue "overdue" or a failed CI run
"a confirmed project failure", count the corresponding comprehension
task as not independently completed, revise the wording and retest.


## Portfolio-ready alternative: reproducible non-human evaluation

**You may publish this project in a portfolio without recruiting human
participants.** Do not claim that HRD, participants or real users understood
it until such a study actually occurs. Treat the checks below as *automated
UI and evidence audits*, not a usability success percentage.

The existing screenshot workflow now makes a real desktop (1440px) and
mobile (390px) Streamlit session with Playwright. It checks the actual
navigation, collapsed glossary, charts, export, evidence finding state,
comparison table and mobile menu. Its new
`recruiter-browser-audit.json` also records observable viewport width,
horizontal overflow, KPI-card count, rendered chart count, source timestamp
disclosure, analysis-cohort disclosure and the review-action prompt.
Any failed required assertion fails the workflow rather than silently
producing an attractive screenshot.

The CI workflow separately runs `scripts/audit_reviewer_evidence.py`
against the **real committed snapshot**, preserving
`reviewer-evidence-audit.json` as an Actions artifact. It cross-checks
selected verified projects, bounded numeric findings, links to genuine
stored GitHub records, the three-step inspection plan and
unavailable-example listing fallbacks. A missing individual example is
explicitly **not** interpreted as verified record-level evidence.

`tests/test_recruiter_accessibility.py` checks normal-text contrast of
the specific palette pairs used in key reviewer-facing labels and mobile
supporting-text size. It does not establish full WCAG 2.2 conformance
or guarantee readability for every browser and font configuration.

**Recommended reviewer demonstration (without creating sample data):**

1. On Dashboard, explain the exact selected cohort and snapshot age.
2. Inspect one quantified `What should we inspect?` finding.
3. Follow the original GitHub record, then return to the review plan.
4. Switch to exploratory scope and explain why incomplete sources are
   not zero activity.
5. On mobile, verify navigation and charts do not overflow.

Use `python -m pytest -q` and the GitHub Actions screenshots/audit
artifacts as reproducible evidence. Human task testing remains an optional
future strengthening step if you want to say "tested with nontechnical
participants"; it is **not** a prerequisite to listing the technical
project on a CV/portfolio.

### References (patterns and criteria, not borrowed code)

- https://github.com/pingcap/ossinsight : project exploration, comparisons
- https://github.com/chaoss/grimoirelab-sigils : source-specific dashboard views
- https://www.nngroup.com/articles/ten-usability-heuristics/ :
  recognition rather than recall; visibility of status; use familiar language
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html :
  4.5:1 minimum normal-size text contrast

Only the principles are referenced; these audits inspect this project's
own actual code, browser renderings and sourced records.


## P1 reviewer-first flow improvement (automated, not a participant claim)

The Dashboard now starts with one compact, factual reading path: **What
happened during the past 7 days → What should we inspect? → Why inspect →
Next action → Original GitHub evidence**. The confidence column separates
verified 28-day events from the *independently* verified full open-Issue
inventory. Incomplete sources remain unknown, not zero.

Extra Issue-age, CI outcome, matched-history and sample-distribution charts
are behind the optional **Show supporting charts and source details**
toggle. The primary daily trend chart and the three evidence-backed checks
remain directly visible. This reduces default mobile scroll length and
avoids computing hidden Plotly charts on every rerun. Playwright tests
must open the toggle to exercise those chart paths.

This is a change to the UI, not evidence that any human participant understood
it. The anonymous 3–5-person protocol above is still **not performed**.
