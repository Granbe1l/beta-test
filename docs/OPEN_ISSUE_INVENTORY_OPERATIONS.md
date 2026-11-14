# Maintaining 50 verifiable full-open Issue inventories

**Different from 50/50 Verified 28-day event coverage.** A repository can have
a complete 28-day Issues/PR/Actions event history while its entire backlog
of old, unchanged open Issues is still unknown.

## Latest verified recovery: 14 November 2026 at 17:54 WIB

[Real source collector #43587299217](https://github.com/Granbe1l/beta-test/actions/runs/43587299217) completed successfully after production catch-up capacity was increased. Its independent audit shows **50/50** fresh, exhausted full-open Issue inventories (zero stale/partial/failed/unavailable), alongside **50/50** verified Issues/PR/CI events across the 28-day source window. The live collector logged **8 pending inventories, 8 attempted, 8 complete, 0 failed, 0 unvisited**, and **633 API requests remaining** within the unchanged 850 limit. Its newly published snapshot contains **5,086 Issue, 5,598 PR, and 45,054 CI/CD records**. This audit is timestamped: it proves the actual catch-up run, **not** that future cron events will always fire on time.

## Earlier verified collection after the 8-to-25 capacity fix

At **14 November 2026, 02:39:47 UTC (09:39:47 WIB)**, the first real
[post-fix GitHub collection](https://github.com/Granbe1l/beta-test/actions/runs/43547169286)
exhausted the open-Issue inventory pages for all nine previously missing or
stale repositories: **9 attempted, 9 complete, 0 partial/failed**.
The complete source audit then reported:

- **50/50 fresh complete full-open Issue inventories**, 0 stale, 0 partial,
  0 failed and 0 unavailable; **50 distinct repository identities**.
- Independently, **50/50 Verified event sources** for the 28-day Issues,
  Pull Requests and CI/CD windows.
- **277/850 API attempts used** across the run; **26** of them were for
  independent inventory scans. New snapshot: 5,023 Issue records,
  5,512 PR records and 44,226 CI/CD run records.
- Actual [dated audit artifact](https://github.com/Granbe1l/beta-test/actions/runs/43547169286/artifacts/14094830686)
  contains snapshot-audit.json, snapshot-audit-before.json,
  open-inventory-triage.json (gaps = []), and the published snapshot.
  The compressed snapshot's Git blob SHA is
  bdb876fa89252d5b1b2c37ea39625594ab4af2d0 and matches the
  data/github_public_snapshot.json.gz blob published on main.

**This verifies one real successful snapshot at that time**, not
continuous compliance. It was a push-triggered collection, so three
consecutive real scheduled refreshes are still required to certify early
four-hour cadence reliability. Never substitute a green test run for
future source audits.

## Grounded baseline

Actual [14 November 2026 scheduled collector run](https://github.com/Granbe1l/beta-test/actions/runs/43540739560):
**41/50** fresh complete open-Issue inventories, **4 stale**, **5 unavailable**.
The four stale snapshots had previously completed a full scan, but did not
meet the independent 12-hour freshness gate. The five unavailable repositories
had no complete inventory checkpoint.

The nine outstanding members at that audit were:

| Previously complete, now stale | No complete inventory checkpoint |
| --- | --- |
| Omega-Destroyer/PairFree | Own716/OwnBoxForAndroid |
| SXP-Simon/astrbot_plugin_qq_group_daily_analysis | SinaXhpm/Submarine |
| VictoriaMetrics/VictoriaMetrics | T8RIN/ImageToolbox |
| alibaba/open-code-review | Waboodoo/HTTP-Shortcuts |
| | adrcotfas/goodtime |

These are **dated findings**, not current promises or reasons to replace
repositories. Repository counts may change, and PRs are not counted as Issues
in the independently exhausted inventory.

## Change: controlled collection capacity, not an invented 50/50

The four-hour scheduled collector keeps its **12-hour source freshness gate**
and **850-request local attempt budget**. Its full-open inventory allowance
was raised from 8 to 25, which handles ordinary two-slot rotation. On 14
November 2026 a missed-schedule catch-up run had **33 pending inventories**
but hit the hard 25 cap, leaving **8 stale** with **573/850 API attempts
unused**. The production workflow now permits **up to 50 pending scans per
run**; the CLI and Python function retain a conservative 25 default.
This is an attempt cap, **not** a success target or a higher API allowance.
Actual rate limits, elapsed time, REST/Search exhaustion and scheduling can
still prevent 50/50 freshness.

Collector order is important:
1. Preserve and refresh at-risk verified 28-day Issues, PR and CI sources.
2. Use **remaining** request budget for eligible stale/missing full-open
   inventories; skip already fresh complete inventories.
3. Allow at most 50 inventory attempts in the production recovery workflow
   (the general-purpose CLI still defaults to 25). Retain the existing
   conservative request reserve for REST scans and bounded Search fallback.
   Never exceed the shared 850-request budget to achieve a target count.
4. A complete inventory may be certified **only** when REST pages are
   exhausted, or every GitHub Search creation-time shard and page is exhausted,
   no incomplete-result flags appear, and the checkpoint is fresh.
5. Missing, partial, stale, rate-limited or unvisited data retain their
   actual status. A partial scan can save observed rows but must never promote
   the full inventory to Verified or invent Issue closure timestamps.

The workflow now stores **open-inventory-triage.json** alongside its source
audit. It lists every incomplete/stale repository, last success, page count,
and sanitized error. The collector also logs attempted/completed/failed
inventory scans and the API budget remaining.

## How to verify outcomes

1. Open [scheduled collector runs](https://github.com/Granbe1l/beta-test/actions/workflows/public-snapshot.yml).
2. Inspect the **github-50-repo-source-audit** artifact, especially
   snapshot-audit.json and open-inventory-triage.json.
3. Confirm **open_backlog.complete == 50** with all checkpoints fresh at the
   same audited timestamp. Do not substitute **issues.verified_28d == 50**.
4. Check consecutive real scheduled runs and published snapshots; a
   one-time 50/50 score does not establish durable completeness. Use separate
   four-hour schedule-reliability evidence.
5. If a repository stays partial, inspect the exact pages and error. Do not
   raise page caps blindly; review secondary Search limits and available
   request/time budgets. Never force checkpoint status or discard a repository
   just to hit the target.

The fixed 50-project cohort remains unchanged. This is a read-only GitHub
ingestion and deterministic validation improvement, not a user-supplied
dataset, a synthetic record generator or a guarantee of a future result.

## 17:46 WIB recovery audit (14 November 2026)

[Actual main-branch collector run](https://github.com/Granbe1l/beta-test/actions/runs/43586500756) published a 50/50 jointly Verified 28-day Issues/PR/CI snapshot,
but independently complete **fresh open-Issue inventories were 42/50**:
33 pending before inventory maintenance, 25 attempted, 25 complete, 8
unvisited because of `per_run_capacity`. The workflow logged 40 requests
used for those 25 inventories and 573 requests remaining. The next
collection with an increased cap must be audited independently; a green
CI check alone cannot establish that the remaining eight were refreshed.
