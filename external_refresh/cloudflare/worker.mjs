// Independent, fail-closed, read-only-until-needed GitHub snapshot watchdog.
// A deployment requires an explicitly provisioned Cloudflare account and
// a GitHub fine-grained PAT scoped to only this repository (Actions: write,
// Contents: read). No secret is committed.
const OWNER = "Granbe1l";
const REPO = "beta-test";
const WORKFLOW = "public-snapshot.yml";
const SNAPSHOT_PATH = "data/github_public_snapshot.json.gz";
const MAX_AGE_MS = 6 * 60 * 60 * 1000;
const RETRY_BACKOFF_MS = 90 * 60 * 1000;
const API = `https://api.github.com/repos/${OWNER}/${REPO}`;

async function request(path, token, fetcher, options = {}) {
  const response = await fetcher(API + path, {
    ...options,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "project-delivery-monitor-external-watchdog",
      ...(options.headers ?? {}),
    },
    redirect: "error",
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`GitHub API HTTP ${response.status}`);
  return response;
}

export async function checkSnapshot({ token, fetcher = fetch, nowMs = Date.now() }) {
  if (typeof token !== "string" || !token.trim()) {
    throw new Error("Missing GITHUB_DISPATCH_TOKEN; fail closed");
  }
  const commitResponse = await request(
    `/commits?path=${encodeURIComponent(SNAPSHOT_PATH)}&per_page=1`,
    token, fetcher
  );
  const commits = await commitResponse.json();
  const timestamp = commits?.[0]?.commit?.committer?.date;
  const publishedMs = Date.parse(timestamp || "");
  if (!Number.isFinite(publishedMs) || publishedMs > nowMs + 300000) {
    throw new Error("Snapshot publication timestamp missing or invalid");
  }
  const ageMs = nowMs - publishedMs;
  if (ageMs <= MAX_AGE_MS) {
    return { action: "skip_fresh", age_minutes: Math.round(ageMs / 60000) };
  }

  // Fail closed if we cannot inspect running or recently dispatched workflows.
  const runsResponse = await request(
    `/actions/workflows/${WORKFLOW}/runs?per_page=30`,
    token, fetcher
  );
  const body = await runsResponse.json();
  if (!Array.isArray(body?.workflow_runs)) {
    throw new Error("Workflow run history unavailable");
  }
  const running = body.workflow_runs.some(
    r => ["queued", "in_progress", "requested", "waiting", "pending"].includes(r.status)
  );
  if (running) {
    return { action: "skip_active", age_minutes: Math.round(ageMs / 60000) };
  }
  const recentlyDispatched = body.workflow_runs.some(r =>
    r.event === "workflow_dispatch" &&
    Number.isFinite(Date.parse(r.created_at || "")) &&
    nowMs - Date.parse(r.created_at) >= 0 &&
    nowMs - Date.parse(r.created_at) < RETRY_BACKOFF_MS
  );
  if (recentlyDispatched) {
    return { action: "skip_backoff", age_minutes: Math.round(ageMs / 60000) };
  }

  const response = await request(
    `/actions/workflows/${WORKFLOW}/dispatches`,
    token, fetcher, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main" }),
    }
  );
  // GitHub returns 204 for accepted workflow_dispatch; this is NOT proof of
  // workflow completion, successful collection, or fresh verified coverage.
  if (response.status !== 204) {
    throw new Error(`Unexpected dispatch status ${response.status}`);
  }
  return { action: "dispatch_accepted", age_minutes: Math.round(ageMs / 60000) };
}

export default {
  async scheduled(_controller, env) {
    const result = await checkSnapshot({ token: env.GITHUB_DISPATCH_TOKEN });
    console.log(JSON.stringify(result));
  },
};
