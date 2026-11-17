# Independent refresh watchdog — deployed cron observed on 15 Nov 2026

> **Current production status (18 November 2026):** The owner manually deployed the four-hour rescue Worker in Cloudflare as version `cd6b3e5d`, and real automatic cron + GitHub collector run #49 provide production end-to-end evidence below. This GitHub branch is still **draft / not merged**, so the `main` repository source remains at the former six-hour threshold until owner-approved merge. The hourly Cron Trigger is unchanged, and the >4-hour check is **not** a fixed four-hour completion SLA. No token, dataset, repository cohort, or Verified status was altered by this PR.

This is a second scheduler outside GitHub, not a replacement collector.
The existing main-branch `public-snapshot.yml` GitHub schedule remains
every four hours. If Github misses a cron slot, this Cloudflare Cron Trigger
checks snapshot *publication commit age* hourly at UTC minute 00.

**Production evidence, 15 Nov 2026:** owner screenshots show this Worker
deployed with a Cron Trigger every hour, an encrypted
`GITHUB_DISPATCH_TOKEN` secret, and successful real `scheduled`
invocations near 21:01 and 22:01 WIB with no reported errors.
This proves invocation execution, **not** the watchdog decision or which
actor initiated the separate 21:01 WIB GitHub `workflow_dispatch`.
The GitHub collector subsequently published a validated 50/50 snapshot
at 21:05 WIB. These adjacent times are consistent with a Cloudflare
rescue but require a matching `dispatch_accepted` application log for
conclusive attribution. No deployment or secret change is required
just to reconcile documentation.

**Production end-to-end evidence, 18 Nov 2026:** at 02:00:56 WIB, deployed
Cloudflare version `cd6b3e5d` automatically recorded `scheduled` / `outcome=ok`
and application `{"age_minutes":258,"action":"dispatch_accepted"}`.
Five seconds later, [GitHub collector run #49](https://github.com/Granbe1l/beta-test/actions/runs/44154011237)
started as `workflow_dispatch`. Its preflight recorded
`dispatch_target_hours=4`, `snapshot_age_minutes=258.45` and
`should_collect=true`. Collector completed around 02:05 WIB with
50/50 source-specific 28-day Verified Issues/PR/CI, independent 50/50 complete
full-open Issue inventories, and a published updated snapshot. Provider
attribution is strongly supported by timing and matching snapshot age;
this does not guarantee that future cron deliveries are punctual.

**Fail-closed guardrails:** if the latest committed snapshot is <=4 hours old,
no request is dispatched; if a collector is truly running, a pending run has activity within 2 hours,
or a dispatched run was created within 90 minutes, no request is dispatched.
Very old, unchanged GitHub `queued` entries (observed for >3 days) do
not lock the watchdog permanently. Missing pending-run timestamps fail closed. If either GitHub
API read fails, the watchdog raises an error rather than guessing.
It dispatches only the pinned main workflow and does not modify data,
coverage status, Verified denominator or issue inventories.

The age test uses the latest Git commit **that changes the snapshot path**,
not a successful source-coverage audit. A successful HTTP 204 only means
GitHub accepted a dispatch. Actual collector completion and source quality
must be checked in GitHub Actions audit artifacts.

## 15 Nov 2026: Cloudflare runtime compatibility (09:00 WIB)

A real scheduled Cloudflare run failed with `TypeError: Invalid redirect value`.
Cloudflare Workers supports only `redirect: "follow"` or `redirect: "manual"`;
unlike Node, the Workers runtime rejects `redirect: "error"` before sending
the request. Use `redirect: "manual"` to avoid forwarding the GitHub bearer
token to redirect destinations, and let the existing `!response.ok` check
reject 3xx. Regression tests assert manual mode for each API request and
reject a 302 response. After merge, deploy the updated GitHub Worker to
the existing Cloudflare Worker and check **scheduled** logs.

## 15 Nov 2026: stale GitHub queue fix and production-version check

Cloudflare logs at 08:00 WIB showed `skip_collector_active` after a snapshot age
of 6.18h, while GitHub's latest connector query showed zero active executions
and an abandoned collector `queued` since 12 Nov 03:31 WIB. This is strong
evidence of *false-active* detection, but the deployed Cloudflare source
must be checked directly: the observed log format and cron minute differ from
this checked-in Worker version.

This code ignores only pending GitHub runs with no status activity for >=2h.
It still blocks while a job is in progress, while newer pending jobs exist,
or while the 90-minute dispatch backoff applies. Workflow-level GitHub
concurrency continues to protect the collector. To apply this fix, deploy
the updated Worker from GitHub to the **existing** Cloudflare Worker and keep
its configured secret in Cloudflare. Pushing a commit to GitHub does NOT
update a Worker deployed independently through Cloudflare's dashboard.

Proof requires a **real Cloudflare scheduled** invocation after deployment
and the ensuing GitHub `workflow_dispatch` run with valid audit artifact
and snapshot publication. The unit test alone is not proof of production.

## Deploy (requires repository owner's Cloudflare/GitHub accounts)

1. On GitHub create a **fine-grained token** restricted to exactly
   `Granbe1l/beta-test`: repository permissions **Actions: write** and
   **Contents: read**, with a short expiration and rotation plan. No
   administrative permission or broad classic PAT scope is required.
2. Sign in to Cloudflare locally and use Wrangler for this directory:
   `npx wrangler deploy --config external_refresh/cloudflare/wrangler.toml`.
   Deploy from the repository root after confirming Wrangler's root/path
   resolution, or enter the directory and run `npx wrangler deploy`.
3. Set the token as a secret **from that directory**:
   `npx wrangler secret put GITHUB_DISPATCH_TOKEN`.
   Never store it in `wrangler.toml`, Git, screenshots or ChatGPT.
4. Confirm the cron trigger and logs on the Cloudflare dashboard; test
   with `npx wrangler dev --test-scheduled` and local scheduled route.
5. Verify one real stale-snapshot dispatch, the GitHub workflow-run event,
   the resulting published audit and actual 50/50 denominators. Do not
   state that the independent scheduler is active before this happens.
6. After deployment, review Cloudflare usage and alerts and revoke the
   token immediately if the Worker is discontinued.

The source files in this repository remain **optional for other installations**.
For this project, the owner's Cloudflare screenshots dated 15 November
2026 demonstrate that production is deployed and scheduled event
invocations are succeeding. The token name is visible in encrypted settings, but its actual scope/expiry still requires account-side validation. The real 18 November four-hour rescue outcome is documented above.
Merging GitHub code does **not** redeploy the existing Worker.
The checked-in Wrangler cron now matches the observed production
minute 00; do not redeploy solely to reconcile this file.
Running Node tests does not touch GitHub or Cloudflare:

```sh
node --test external_refresh/cloudflare/worker.test.mjs
```

Official references:
- https://developers.cloudflare.com/workers/configuration/cron-triggers/
- https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
- https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
