# P2 evidence: performance, comparisons, accessibility and API safety

This records checks available **before public Streamlit deployment**. No
independently verified public hosting URL or real nontechnical user study
exists, and no recruiter comprehension score is invented.

## First-screen usability (P1, implemented and browser-tested)

The Dashboard begins with **What happened → Why inspect → Next action →
GitHub evidence**. It separates seven-day recorded activity, 28-day jointly
Verified event sources and independently exhausted full-open Issues.
Main Issues/PR trend and the primary evidence-linked action remain visible.
The three full evidence cards are one expandable step away to avoid long
stacked cards on narrow screens. Deep
Issue-age, CI, matched-history and activity charts sit behind an explicit
toggle; expensive Plotly charts are not generated when the toggle is closed.

Measured with local Playwright screenshot capture at fixed widths:
- Latest 390px mobile overview: **5,067 to 3,180 pixels**, about **37%**
  shorter after the supporting findings became explicitly expandable
  ([PR #53](https://github.com/Granbe1l/beta-test/pull/53)).
- Earlier historical 390px baseline: **7,227 to 5,108 pixels**, 29% shorter.
- Earlier desktop main-page baseline: **4,298 to 2,680 pixels**, 38% shorter.

Those are layout lengths, not speed, production availability or proof
that human participants understand the information.

## P2.1: Real local browser timing, not public cold start

The actual Playwright script records monotonic wall-clock elapsed
milliseconds between navigating to local Streamlit and detecting the
first rendered Plotly chart, independently for desktop and mobile.
The output is the recruiter-browser-audit.json artifact. The runner is
shared and timings vary; no arbitrary pass/fail latency threshold has
been invented. This is **NOT** a hosted Streamlit cold-start or SLA.

The snapshot load already uses cached data. Optional expensive charts
are now conditional. Official reference:
https://docs.streamlit.io/develop/concepts/design/performance

## P2.2: Shared server-process GitHub request budget

One uncached public URL inspection makes up to four anonymous public
GitHub REST GETs. The five-minute cache avoids repeating identical
requests. A thread-safe, process-shared **12 new inspections per rolling
60-minute window** guard limits this workload to at most 48 GET calls
per process/hour under regular no-retry behavior, leaving some headroom
relative to common unauthenticated API quotas. The existing per-session
60-second retry cooldown is separate.

This is NOT a distributed limiter across Cloud replicas, a per-IP quota,
permission to access private repositories, or a guarantee against GitHub
secondary rate limits. Missing API responses remain unknown rather than
zero; rate-limited users see an actionable retry message.

## P2.3b: Source-qualified peer eligibility in comparisons

The Explore repositories comparison now shows **how many repositories in each
category actually qualify for the chosen metric and time window**, including
missing/withheld counts. Verified zero is still eligible. A median and
interquartile range are shown only when at least four eligible source
values exist for that category. Cross-category counts are **not normalized
by project size or team capacity**, so the chart cannot rank quality or
workers. The browser suite opens the disclosure and checks it renders.

## P2.3: Keyboard and assisted reading

KPI groups include accessible label, value and context, while decorative
icons are hidden from assistive technologies. Author CSS declares explicit
focus-visible outlines for buttons, links, tabs and sidebar controls.
Small mobile controls have a minimum height of 44px where project CSS
can control the target. Existing contrast and no-horizontal-overflow
tests remain. The source is W3C WCAG 2.2:
https://www.w3.org/TR/WCAG22/

Passing these automated probes is **NOT** a formal WCAG certification.
Manual keyboard and screen-reader review remains recommended.

## P2.5: Within-category distributions, not rankings

The Compare projects view adds a median and 25th/75th percentile table
for the selected period metric, only when at least four repositories in
the same category have **eligible verified values**. It displays the
eligible n, total category size and excluded/unknown count.

Exploratory retrieved-record totals cannot form peer distributions,
and missing records never become zeros. Category differences describe
only this **nonrandom curated 50-project sample**. They do not represent
all GitHub projects, delivery deadlines, code quality or productivity.

## Human study: still not performed

The anonymous protocol for 3–5 real nontechnical participants and an
empty response form already exist in REVIEWER_USABILITY_CHECK.md and
REVIEWER_RESULT_FORM.csv. Playwright checks are not a human study.

## Release proof

Use GitHub Quality checks, actual desktop/mobile screenshot workflow
and source-integrity audits to validate each changed feature. Deployment
and real external usability are separate acceptance gates left untouched
at the user's request.
