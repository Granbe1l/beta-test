# Five-minute nontechnical review — test protocol

**Purpose:** verify whether someone unfamiliar with GitHub can interpret
Project Delivery Monitor without confusing public development activity with
private consulting milestones or employee performance. This is a test
protocol, **not** a claim that user testing has already taken place.

## Participants and setup

Ask 3–5 people who have not built the app, ideally including at least
two without GitHub or software-development experience. Use the existing
real 75-repository snapshot. Record device type (desktop or mobile)
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
