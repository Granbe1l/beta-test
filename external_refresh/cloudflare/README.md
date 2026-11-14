# Independent refresh watchdog — optional deployment, NOT ACTIVE

This is a second scheduler outside GitHub, not a replacement collector.
The existing main-branch `public-snapshot.yml` GitHub schedule remains
every four hours. If Github misses a cron slot, this Cloudflare Cron Trigger
checks snapshot *publication commit age* hourly at UTC minute 07.

**Fail-closed guardrails:** if the latest committed snapshot is <=6 hours old,
no request is dispatched; if a collector run is active or a dispatched run
was created within 90 minutes, no request is dispatched. If either GitHub
API read fails, the watchdog raises an error rather than guessing.
It dispatches only the pinned main workflow and does not modify data,
coverage status, Verified denominator or issue inventories.

The age test uses the latest Git commit **that changes the snapshot path**,
not a successful source-coverage audit. A successful HTTP 204 only means
GitHub accepted a dispatch. Actual collector completion and source quality
must be checked in GitHub Actions audit artifacts.

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

The Cloudflare job is optional. Without a connected Cloudflare account
and a securely provisioned token, this repository only contains tested
configuration and implementation, not a running external scheduler.
Running Node tests does not touch GitHub or Cloudflare:

```sh
node --test external_refresh/cloudflare/worker.test.mjs
```

Official references:
- https://developers.cloudflare.com/workers/configuration/cron-triggers/
- https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
- https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
