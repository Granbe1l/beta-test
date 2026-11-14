# GitHub-only refresh: portfolio and interview playbook

**Status:** A practical GitHub-only backup and pre-demo procedure, not proof of
guaranteed four-hour scheduling. No Cloudflare account or external token is
required. All workflow runs and collector results are public GitHub evidence.

## What is configured

- **Primary collector:** [Refresh curated public GitHub snapshot](https://github.com/Granbe1l/beta-test/actions/workflows/public-snapshot.yml).
  A GitHub `schedule` requests collection every four hours at UTC 01:23,
  05:23, 09:23, 13:23, 17:23 and 21:23 (WIB 08:23, 12:23, 16:23,
  20:23, 00:23, 04:23). GitHub can delay or drop scheduled events.
- **GitHub-only watchdog:** [Rescue stale public GitHub snapshot](https://github.com/Granbe1l/beta-test/actions/workflows/snapshot-watchdog.yml).
  Requested hourly at UTC minute 47. On successful main-branch push checks it
  can also inspect snapshot freshness. After **more than six hours** since
  the *committed snapshot's generated_at*, it may send a rescue
  `workflow_dispatch`, **only** if GitHub run history is readable, there
  is no active collector and no collector attempt in the last 90 minutes.
  Source windows and API budgets remain unchanged. Both schedules still rely
  on GitHub, so neither is independently guaranteed.
- **Source quality:** 50 pinned repositories, 28-day Issues/PR/CI verified
  *at the time of each audit*, 12-hour source freshness limit, plus a separate
  full-open Issue inventory. A recent snapshot does not itself establish
  50/50 source coverage. Each audit must state actual denominators.

## Before an interview, CV submission or recruiter demonstration

1. Open the [collector Actions page](https://github.com/Granbe1l/beta-test/actions/workflows/public-snapshot.yml)
   and select **Run workflow → Branch: main → Run workflow**. This action
   requires owner/write access to the repository. Avoid launching a duplicate
   if a collector is already queued or running.
2. Open that exact new **workflow_dispatch** run. Confirm the **refresh** job
   actually finished with **success**. A green unit-test workflow or green
   watchdog is not collection proof.
3. Open its artifact named **github-50-repo-source-audit** (retained for 14
   days). Inspect `snapshot-audit.json`, `coverage-readiness.json`, and
   `open-inventory-triage.json`. Acceptance for a *fresh full* demo is:
   - `tracked = 50`, `verified_joint_28d = 50`,
     `source_verified_28d.issues = 50`,
     `source_verified_28d.pull_requests = 50`, and
     `source_verified_28d.workflow_runs = 50`;
   - `fresh_full_open_inventories = 50`, `gaps = []`, and
     `all_full_open_inventories_current = true`;
   - `window_days = 28`, `stale_hours = 12`, and a genuine dated
     `as_of_utc`. Never edit incomplete data to force those numbers.
4. Confirm the collector **published** the updated
   `data/github_public_snapshot.json.gz` file to `main` (a successful
   audit upload alone is not publication). If the public Streamlit demo has
   been deployed and verified, check its displayed **UTC/WIB timestamp**
   matches the committed snapshot. The dashboard's **Reload stored data**
   button only rereads the local saved snapshot; it does NOT call GitHub.
5. If any denominator is below 50, keep the displayed status **partial/stale**
   and inspect the collector's `coverage-readiness.json` and
   `open-inventory-triage.json` reasons. Retry only when justified after
   checking the API budget, active runs, and 90-minute rescue backoff.
   For a time-limited interview, use the last **dated** reproducible result,
   not a false "50/50 live" claim.

## Which proof counts for which claim?

| Claim | Required evidence |
| --- | --- |
| Collector works with real public GitHub data | One successful actual collector with published snapshot and source audit |
| Demo currently shows fresh complete 50/50 data | Current published snapshot + source-specific 28-day and separate full-open checks above |
| GitHub Actions is configured for four-hour refresh | Workflow cron configuration |
| Four-hour schedule is *operationally reliable* | Three consecutive actual `schedule`-event runs with suitable spacing **and** individual 50/50 source/inventory audit artifacts, using `schedule-audit.yml` |
| GitHub-only rescue works in production | Actual stale-watchdog `workflow_dispatch` plus successful resulting collector/source audit; a simulated test or a watchdog `skip` does not prove this |

## Interview-ready wording (bounded claims)

> Built a Python, SQL, and Streamlit engineering-activity monitor for
> 50 curated public GitHub projects. The dataset uses source-verified
> 28-day Issues, pull-request, and CI/CD observations and separate
> complete open-Issue inventories, with reproducible GitHub Actions audits.
> Refresh is configured every four hours with a GitHub-only stale-snapshot
> rescue and a manual pre-demo fallback; GitHub schedule punctuality is
> not guaranteed.

**Public URL:** Do not claim live hosting unless the
[public deployment verifier](PUBLIC_DEPLOYMENT.md) has passed. The default
read-only app never collects data just because a reviewer opens it.

## When the GitHub-only solution is insufficient

If repeated real observations show missed GitHub primary **and** watchdog
schedules, stop treating this same-provider setup as reliable automatic
delivery. Keep a fresh auditable pre-demo snapshot and consider deploying
the already coded external Cloudflare scheduler **later**, with explicit
account and secret setup. Do not mislabel a watchdog/manual dispatch as a
native scheduled run.
