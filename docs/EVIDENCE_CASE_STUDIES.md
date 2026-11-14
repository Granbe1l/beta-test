# Real GitHub source studies — evidence before decisions

This dashboard contains public activity observations, **not actual verified
client delivery outcomes**. The goal is to demonstrate responsible analytical
reasoning on a real dataset: a reviewer sees a defensible observation, opens an
original record, checks context, and decides *whether* a follow-up is warranted.

The **Key findings → Real GitHub evidence walkthroughs** section uses the
verified 28-day tracked cohort and selects up to one example of each:

| Example | Measured signal | What can actually be checked | Action boundary |
| --- | --- | --- | --- |
| Older open Issues | Observed 30+ day open-Issue share from complete current inventory | Original issue status, labels, conversation | Aged ≠ late; only follow up if still relevant |
| CI results | Known completed run success share and at least one genuine failed/timed-out run | Actual Actions logs, branch and adjacent reruns | Failed run ≠ failed release |
| PR merge duration | Median creation-to-merge time over verified 28-day merged changes, n≥5 | Actual merged PR scope and review timeline | Median ≠ developer productivity |

Each case is **conditional**, not an investigation already completed.
The tool cannot validate private task importance, maintainers' intentions,
release outcomes, business loss, developer hours or customer deadlines.

**Reproduce with actual stored sources:**

```bash
python scripts/audit_case_studies.py
```

That command uses `data/github_public_snapshot.json.gz`, and validates
case-to-record membership. It emits `case-study-evidence-audit.json` with
the exact case types, GitHub URLs, scope and metric values. GitHub Quality
Checks preserves this as an artifact. Do not report three available cases
unless the receipt actually lists three; missing evidence is never filled.

For complete methodology, see [portfolio narrative](PORTFOLIO_CASE_STUDY.md).
