# Maintaining 50 verifiable full-open Issue inventories

**Different from 50/50 Verified 28-day event coverage.** A repository can have
a complete 28-day Issues/PR/Actions event history while its entire backlog
of old, unchanged open Issues is still unknown.

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
is now **up to 25 repositories per run** instead of 8. This gives capacity
for all 50 members across two four-hour slots (with a third slot of
headroom) under ordinary conditions; real API failures, GitHub scheduling,
page counts, request budgets and long pagination can reduce actual throughput.

Collector order is important:
1. Preserve and refresh at-risk verified 28-day Issues, PR and CI sources.
2. Use **remaining** request budget for eligible stale/missing full-open
   inventories; skip already fresh complete inventories.
3. Allow no more than 25 inventory attempts per run. Maintain a conservative
   request reserve for a full REST scan plus the bounded Search fallback.
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
