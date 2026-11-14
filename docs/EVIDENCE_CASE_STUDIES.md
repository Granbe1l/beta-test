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

## Snapshot-backed examples, 14 November 2026

The following examples were selected by the deterministic case builder and
individually checked against GitHub REST. **These are observations, not
confirmed product problems.** Snapshot generated **2026-11-14 02:39:47 UTC**.

| Observation from the real snapshot | Original public record | What the analyst can responsibly say |
| --- | --- | --- |
| **HKUDS/RAG-Anything:** **92 of 94** complete-inventory open Issues were at least 30 days old (**98%**). | [Issue #2: Excel files with embedded images](https://github.com/HKUDS/RAG-Anything/issues/2) (open at external check). | This merits reviewing priorities and relevance; neither the high share nor Issue #2 proves a missed delivery deadline. |
| **Kronuz/Xapiand:** **311 of 628** completed CI runs with known outcomes succeeded (**about 50%**) in the verified 28-day window. | [Failed CI run 43478798335](https://github.com/Kronuz/Xapiand/actions/runs/43478798335). | Investigate the workflow/branch, failure logs and reruns. The other **317 outcomes cannot all be called failures**: skipped/other results remain in the denominator. A failed run does not prove a failed release. |
| **Anionex/dsh-turn-rewind:** median creation-to-merge time was **4 minutes across seven merged PRs** in the verified 28-day window. | [Merged PR #34: Restore attachments in the draft](https://github.com/Anionex/dsh-turn-rewind/pull/34) took **85.4 hours (~3.6 days)** from creation to merge. | PR #34 was **deliberately selected as the longest observed example to inspect**, *not* as a representative of the four-minute median. These distinct values are compatible; neither establishes developer productivity or a team bottleneck without reviewing context. |

These values are **dated**, reflect this particular non-random curated sample,
and may change in subsequent snapshots. Do not hardcode them as live KPI
values in the Streamlit app: the dashboard always recomputes from the stored
dataset with verification rules.

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
