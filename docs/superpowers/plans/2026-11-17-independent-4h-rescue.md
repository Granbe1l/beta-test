# Independent Cloudflare Four-Hour Rescue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task, with superpowers:test-driven-development and superpowers:verification-before-completion.

**Goal:** Produce an unmerged, non-deployed four-hour Cloudflare rescue candidate that passes local and GitHub CI testing.

**Architecture:** Keep the deployed worker and GitHub collector unchanged. In a separate branch, change only the Cloudflare age threshold and dispatch input; retain the hourly check, queue/backoff protections, fail-closed behavior, and GitHub's existing four-hour preflight contract.

**Tech stack:** Cloudflare Workers JavaScript ES modules; Node 22 test runner; GitHub Actions Python + Node CI.

**Spec:** `docs/superpowers/specs/2026-11-17-independent-4h-rescue-design.md`

## Global constraints

- Branch: `fix/p0-3-cloudflare-4h-tdd`; base `79e84bb8`.
- No merge, Cloudflare production deployment, secret, data or Verified cohort changes without explicit owner approval.
- Only Cloudflare `worker.mjs`, `worker.test.mjs`, `README.md` and Superpowers documentation in scope.

## Review focus

- Exactly 240 minutes remains fresh; 241 is eligible.
- Dispatch includes `inputs.target_hours="4"` for GitHub preflight, not just Worker threshold.
- Active / recently queued collector prevents duplicate dispatch; 120m stale pending handling is preserved.
- 90m recent dispatch backoff and fail-closed API/token errors remain.
- Hourly scheduling means no strict four-hour completion promise.

## Task 1 — RED first

**Files:** `external_refresh/cloudflare/worker.test.mjs`; local isolated test harness.

- [x] Define boundary tests at 239m/240m, 241m/359m/361m; verify payload; active and backoff.
- [x] Run RED test against unchanged six-hour Worker; actual local output: **2 passed, 5 failed**.
- [x] Commit test updates to isolated branch before implementation.

## Task 2 — GREEN minimal worker patch

**Files:** `external_refresh/cloudflare/worker.mjs`.

- [x] Change `MAX_AGE_MS` to 4h.
- [x] Send explicit `inputs: { target_hours: "4" }`.
- [x] Run local regression for the seven focused cases: **7 passed, 0 failed**.
- [x] Commit to isolated branch, not main.
- [ ] Confirm full existing `node --test external_refresh/cloudflare/worker.test.mjs` succeeds in GitHub CI at final branch head.
- [ ] Confirm complete GitHub Quality checks finish green at final head.

## Task 3 — Documentation, review and handoff

**Files:** `external_refresh/cloudflare/README.md`, this plan and the spec.

- [x] Document candidate vs real deployed six-hour production Worker.
- [ ] Open draft PR and ensure changed-file list contains no `data/**`, `external_refresh/cloudflare/wrangler.toml`, token or GitHub scheduling workflows.
- [ ] Review actual final-head CI output and PR diff.
- [ ] Hand off unmerged PR; no deployment or source changes.
