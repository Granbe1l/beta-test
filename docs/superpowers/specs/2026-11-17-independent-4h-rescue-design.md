# P0.3 — Independent Cloudflare Four-Hour Rescue (Design)

**Date:** 17 November 2026
**Decision:** Option B, explicitly selected by the repository owner. Prepare and test on an isolated GitHub branch; **do not merge, deploy Cloudflare production, rotate secrets or alter selected repositories or data** without separate user approval.

## Why this exists

The primary `public-snapshot.yml` GitHub cron targets four-hour intervals, but its real native `schedule` events can be delayed or absent. The GitHub-only watchdog also shares the GitHub scheduler, so it cannot independently guarantee recovery. The owner-provided Cloudflare Worker did run at 16:00, 17:00 and 18:00 WIB on 17 Nov 2026; the existing six-hour rule skipped `age_minutes=299` and `359`. The independently initiated GitHub `workflow_dispatch` #47 started at 18:01, validated 50/50, and published at 18:09. The user-provided 18:00 export did not contain the application-level `dispatch_accepted` message, so timing alone is not conclusive attribution.

## Goals

- At Cloudflare's existing hourly scheduled check, consider rescue only when the age of the latest committed snapshot is strictly **greater than four hours**, instead of six.
- Dispatch exactly `{"ref":"main","inputs":{"target_hours":"4"}}` so that the downstream GitHub preflight applies the same threshold. Omitting the input retains a six-hour preflight and would silently neutralize the earlier rescue.
- Preserve all existing safety checks: fail-closed API handling, redirect manual, no active collector, recent pending and 120-minute stale pending handling, 90-minute dispatch backoff, and GitHub's `public-snapshot-main` concurrency.
- Do not change the hourly Cloudflare cron, the GitHub native cron, the curated 50-repo cohort, data files, source-validity gates, secrets, or deployed Worker.

## Alternatives considered

**A. Keep six-hour fallback:** lowest production risk but misses the requested earlier independent rescue. **B. Four-hour Cloudflare candidate (selected):** minimal isolated change, still best-effort due to hourly trigger and GitHub queue. **C. New external scheduler:** adds credential/provider complexity without evidence of necessity.

## Expected behavior

At a scheduled Cloudflare invocation, a snapshot aged 239m or 240m is fresh; 241m, 359m and 361m are rescue-eligible **only if** no real collector, pending activity or backoff blocks it. Request acceptance (HTTP 204) is never proof of a completed refresh. A real collector run must pass the strict 50/50 source + full-open inventory checks and publish a new snapshot before operational success can be claimed.

## Release and rollback boundary

The current deployed Cloudflare version is reported by the owner as `eb3a776f-eb97-4a56-8948-af2e436344d3` (six-hour rule). This PR **does not deploy**. Separate owner approval is required to merge and deploy; retain the existing deployment/version for rollback. A deployed four-hour Worker must be checked with real scheduled application logs, a correlated `workflow_dispatch` (preflight target=4), validated collector records, published snapshot and duplicate-dispatch guardrails over several cycles. Do not assert strict four-hour timing; an hourly check means normal recovery can exceed four hours, plus queue and runtime.
