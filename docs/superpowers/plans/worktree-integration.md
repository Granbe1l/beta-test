# Worktree integration ? completed 19 November 2026

## Baseline and isolation

- Managed detached worktree: C:/Users/ASUS/.codex/worktrees/pdm-pr-integration/beta-test.
- Base: origin/main 1a2110ebe5dacce2ee956fc1c6a5a576edd7ecd7, fetched with sslVerify=true and schannel. No new branch/commit.
- Exactly 52 allowlisted files copied byte-for-byte. No path overlap with the six upstream snapshot commits. This checkpoint is the only extra candidate document: 53 changed/new files total, 43 tracked modifications and 10 new documents/tests.
- All six latest dataset hashes equal the clean-worktree receipt. Git-filter-normalized content matches HEAD blobs. Initial raw-byte comparison to Git blobs encountered normal Windows CRLF conversion on the manifest; no data change occurred, and normalized hashes plus clean data diff confirm it.
- Source audit-menyeluruh remains untouched at b893c04b14e0ae4d745218ec35ea83b728530f9d. Before/after aggregate hash of every tracked/nonignored-untracked file: 6906b2eab2fa4649ccddaa9815f5f8e084ea6c91b6f078efc7b8c020e34fc78e. Full porcelain status and index also identical.

## Checks

| Check | Status | Evidence |
|---|---|---|
| Candidate/diff/data | selesai | All 52 copies identical; dataset receipt hashes retained; git diff --check clean; no staged files or data diff. |
| Python integration | selesai | 550 passed in 65.59s, exit 0; .venv/integration-pytest.log. Imports confirmed from new worktree. |
| Cloudflare/Node | selesai | 19 passed, exit 0; .venv/integration-node.log. |
| Actual restore and SQL/KPI | selesai | 50 repositories; 5,551 Issues, 6,310 PRs, 54,095 CI records; exact IDs/counts and SQL eligibility agree at capture and current probe; second restore idempotent. .venv/integration-restore.log. |
| P0 boundaries | selesai | Pinned identities/manifest/archive validated; full suite includes N1 ephemeral restore, N2 clock separation, stale HEAD/publication retries and scheduler gates. |
| Six actual-snapshot routes | selesai | 1 AppTest covering six pages passed in 6.62s, network blocked; .venv/integration-real-app.log. |
| Regression repair | not needed | No demonstrated integration failure; no application/test changes beyond copying the approved candidate. No TDD repair cycle invented. |
| Hosted exact-candidate CI | tertunda | No candidate commit, push or PR yet. |
| Production evidence | tertunda | No live refresh, dispatch, Cloudflare deployment, PostgreSQL migration or scheduler validation. |

The additional regression was justified by the new base snapshot/worktree, not a repeated F1?F12 audit. Python 3.12 runtime reused from the original isolated environment; no dependencies installed. Logs/probe/receipt exist only in ignored .venv in this worktree. Temporary SQLite restore database was removed.

At 19 November 2026 09:13:25 WIB (02:13:25 UTC), stored evidence qualified 50/50 joint 28-day sources but 17/50 fresh full-open inventories. At original capture both were 50/50. Independent timestamps/definitions are preserved; this is a read-only observation of fetched data, not operational production proof.

## Decision and next step

**READY for an authorized PR preparation step; CONDITIONAL for merge on hosted CI and review.** No local integration blocker or source conflict found. Worktree stays detached and uncommitted; keep it intact for continuation.

After separate authorization, prepare the PR branch/commit from this worktree, include intended code/tests/workflows/docs and this checkpoint, exclude data/.venv/logs, then obtain exact-candidate GitHub checks. If main advances, compare affected paths before deciding targeted revalidation. Never overwrite newer main data with the original source snapshot.

First-refresh risks remain documented: unknown/private metadata may block export; legacy caches need bounded revalidation; existing PostgreSQL requires reviewed BIGINT migration if applicable. No metric, cohort or validation policy was weakened.

No stage, commit, push, merge, deployment or source checkout edit. Resume from this checkpoint without repeating completed audit/integration tests unless files or baseline change.


## Authorized PR publication ? 19 November 2026

Owner authorized creating candidate branch, committing the explicit allowlist, pushing that branch, and opening a PR to main. Branch name: codex/pdm-audit-remediation. Pre-publication verification: 53 allowlisted files, unchanged latest-base dataset hashes, empty initial index and clean diff whitespace. Fresh fetch still points to integration base 1a2110ebe5dacce2ee956fc1c6a5a576edd7ecd7. Local 550 Python / 19 Node / real restore SQL and six-page AppTest results remain applicable; no code change or reason to repeat the local audit/tests.

Hosted exact-head CI is pending at commit creation. Record the resulting PR URL/head SHA and check results in .venv/pr-state.json and the chat report; those runtime records must not be committed. No merge, deployment, production Cloudflare operation or manual refresh is authorized. Source audit-menyeluruh remains unchanged.
