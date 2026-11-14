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
      headers: options.headers });
    if (url.includes("/commits?")) return reply(
      [{ commit: { committer: {
        date: new Date(NOW - hoursOld * 3600000).toISOString()
      } } }], commitStatus
    );
    if (url.endsWith("/runs?per_page=30"))
      return reply({ workflow_runs: runs }, listStatus);
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
  assert.deepEqual(JSON.parse(m.calls[2].body), { ref: "main" });
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
