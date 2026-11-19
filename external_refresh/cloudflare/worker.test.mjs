import test from "node:test";
import assert from "node:assert/strict";
import { checkSnapshot } from "./worker.mjs";

const NOW = Date.parse("2026-11-14T20:00:00Z");
function reply(body, status = 200) {
  return { ok: status >= 200 && status < 300, status,
    async json() { return body; } };
}
function mock({ hoursOld = 7, runs = [], commitStatus = 200,
                listStatus = 200, dispatchStatus = 204 } = {}) {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push({ url, method: options.method || "GET", body: options.body,
      headers: options.headers, redirect: options.redirect });
    if (url.includes("/commits?")) return reply(
      [{ commit: { committer: {
        date: new Date(NOW - hoursOld * 3600000).toISOString()
      } } }], commitStatus
    );
    if (new URL(url).pathname.endsWith("/runs"))
      return reply({ workflow_runs: runs.map(r => ({ head_branch: "main", ...r })) }, listStatus);
    if (url.endsWith("/dispatches")) return reply(undefined, dispatchStatus);
    throw new Error("Unexpected URL " + url);
  };
  return { calls, fetcher };
}
test("fresh snapshot: no workflow lookup or dispatch", async () => {
  const m = mock({ hoursOld: 2 });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_fresh");
  assert.equal(m.calls.length, 1);
});

test("candidate branch history never suppresses main rescue", async () => {
  for (const status of ["in_progress", "completed"]) {
    const m = mock({ hoursOld: 5, runs: [{ head_branch: "candidate", status,
      event: "workflow_dispatch", created_at: new Date(NOW - 600000).toISOString() }] });
    const result = await checkSnapshot({ token: "test", fetcher: m.fetcher, nowMs: NOW });
    assert.equal(result.action, "dispatch_accepted");
    assert.equal(new URL(m.calls[0].url).searchParams.get("sha"), "main");
    assert.equal(new URL(m.calls[1].url).searchParams.get("branch"), "main");
  }
});

test("unknown workflow branch fails closed instead of ignoring an active run", async () => {
  const m = mock({ runs: [{ head_branch: undefined, status: "in_progress" }] });
  await assert.rejects(checkSnapshot({ token: "test", fetcher: m.fetcher, nowMs: NOW }), /branch/);
  assert.equal(m.calls.some(c => c.method === "POST"), false);
});
test("stale snapshot and running collector: do not duplicate", async () => {
  const m = mock({ runs: [{ status: "in_progress" }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_active");
  assert.equal(m.calls.length, 2);
});
test("recent dispatched run: back off even after its failure", async () => {
  const m = mock({ runs: [{ status: "completed", event: "workflow_dispatch",
    conclusion: "failure", created_at: new Date(NOW - 600000).toISOString() }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_backoff");
  assert.equal(m.calls.length, 2);
});
test("stale, no active or recent dispatch: request only main workflow", async () => {
  const m = mock();
  const result = await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW });
  assert.equal(result.action, "dispatch_accepted");
  assert.equal(m.calls.length, 3);
  assert.equal(m.calls[2].method, "POST");
  assert.match(m.calls[2].url, /public-snapshot\.yml\/dispatches$/);
  assert.deepEqual(JSON.parse(m.calls[2].body),
    { ref: "main", inputs: { target_hours: "4" } });
});
test("do not dispatch when API, timestamp, token or body is invalid", async () => {
  const m = mock({ listStatus: 403 });
  await assert.rejects(checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW }), /HTTP 403/);
  assert.equal(m.calls.length, 2);
  await assert.rejects(checkSnapshot({ token: "", fetcher: m.fetcher,
    nowMs: NOW }), /Missing/);
  const bad = async () => reply([], 200);
  await assert.rejects(checkSnapshot({ token: "test", fetcher: bad,
    nowMs: NOW }), /timestamp/);
});
test("403 dispatch cannot be reported as successful", async () => {
  const m = mock({ dispatchStatus: 403 });
  await assert.rejects(checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW }), /HTTP 403/);
});

test("stale queued collector from days ago must not block recovery forever", async () => {
  const m = mock({ runs: [{
    id: 43096556666, status: "queued", event: "push",
    created_at: new Date(NOW - 3 * 86400000).toISOString(),
    updated_at: new Date(NOW - 3 * 86400000).toISOString(),
  }] });
  const result = await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW });
  assert.equal(result.action, "dispatch_accepted");
  assert.deepEqual(result.ignored_stale_pending_run_ids, [43096556666]);
  assert.equal(m.calls.filter(x => x.method === "POST").length, 1);
});
test("recent queued collector blocks a duplicate dispatch", async () => {
  const m = mock({ runs: [{
    id: 2, status: "queued",
    created_at: new Date(NOW - 20 * 60000).toISOString(),
    updated_at: new Date(NOW - 20 * 60000).toISOString(),
  }] });
  const result = await checkSnapshot({ token: "test", fetcher: m.fetcher, nowMs: NOW });
  assert.equal(result.action, "skip_active");
  assert.deepEqual(result.blocking_run, { id: 2, status: "queued" });
  assert.equal(m.calls.length, 2);
});
test("queued activity updated recently remains protected even if originally old", async () => {
  const m = mock({ runs: [{
    status: "queued",
    created_at: new Date(NOW - 3 * 86400000).toISOString(),
    updated_at: new Date(NOW - 10 * 60000).toISOString(),
  }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_active");
  assert.equal(m.calls.length, 2);
});
test("queued with unknown timing fails closed", async () => {
  const m = mock({ runs: [{ id: 4, status: "queued" }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_active");
  assert.equal(m.calls.length, 2);
});
test("in-progress job always blocks even if timestamp is old", async () => {
  const m = mock({ runs: [{
    status: "in_progress",
    created_at: new Date(NOW - 4 * 86400000).toISOString(),
    updated_at: new Date(NOW - 4 * 86400000).toISOString(),
  }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_active");
  assert.equal(m.calls.length, 2);
});

test("Cloudflare Workers compatible redirect mode: manual on every request", async () => {
  const m = mock();
  const result = await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW });
  assert.equal(result.action, "dispatch_accepted");
  assert.equal(m.calls.length, 3);
  assert.ok(m.calls.every(call => call.redirect === "manual"));
});
test("redirect response is rejected rather than followed with secret", async () => {
  const requests = [];
  const fetcher = async (url, options) => {
    requests.push({ url, redirect: options.redirect });
    return reply(undefined, 302);
  };
  await assert.rejects(
    checkSnapshot({ token: "test", fetcher, nowMs: NOW }),
    /GitHub API HTTP 302/
  );
  assert.equal(requests.length, 1);
  assert.equal(requests[0].redirect, "manual");
});

test("four-hour boundary: 239m and 240m do not dispatch", async () => {
  for (const minutes of [239, 240]) {
    const m = mock({ hoursOld: minutes / 60 });
    const result = await checkSnapshot({ token: "test", fetcher: m.fetcher, nowMs: NOW });
    assert.equal(result.action, "skip_fresh");
    assert.equal(m.calls.length, 1);
  }
});

test("four-hour boundary: 241m, 359m and 361m dispatch explicitly at 4h", async () => {
  for (const minutes of [241, 359, 361]) {
    const m = mock({ hoursOld: minutes / 60 });
    const result = await checkSnapshot({ token: "test", fetcher: m.fetcher, nowMs: NOW });
    assert.equal(result.action, "dispatch_accepted");
    assert.equal(m.calls.length, 3);
    assert.deepEqual(JSON.parse(m.calls[2].body),
      { ref: "main", inputs: { target_hours: "4" } });
    assert.ok(m.calls.every(call => call.redirect === "manual"));
  }
});

test("four-hour stale snapshot still refuses dispatch while collector is active", async () => {
  const m = mock({ hoursOld: 250 / 60, runs: [{ status: "in_progress" }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_active");
  assert.equal(m.calls.length, 2);
});

test("four-hour stale snapshot still respects ninety-minute dispatch backoff", async () => {
  const m = mock({ hoursOld: 250 / 60, runs: [{
    event: "workflow_dispatch", status: "completed",
    created_at: new Date(NOW - 25 * 60000).toISOString(),
  }] });
  assert.equal((await checkSnapshot({ token: "test", fetcher: m.fetcher,
    nowMs: NOW })).action, "skip_backoff");
  assert.equal(m.calls.length, 2);
});
