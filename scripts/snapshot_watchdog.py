"""Conditional safety net for delayed or dropped GitHub Actions cron events.

The primary four-hour scheduled collection is complemented by this watchdog. This hourly
watchdog checks the *actual committed snapshot generated_at*, not the date a
workflow started, and can dispatch one extra collector run when data age
passes an independently documented threshold. It never fabricates a
schedule event or upgrades any source's verified status.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import requests

SNAPSHOT = Path("data/github_public_snapshot.json.gz")
API_WORKFLOW = "public-snapshot.yml"
MAX_AGE_HOURS = 6
BACKOFF_MINUTES = 90
STALE_PENDING_MINUTES = 120  # Match Cloudflare: ignore only abandoned, unchanged queues.
PENDING_STATUSES = frozenset(("queued", "requested", "waiting", "pending"))


def parse_time(value: str | None):
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def snapshot_generated(path: Path = SNAPSHOT):
    """Read only the first decompressed bytes, never the large rows graph."""
    with gzip.open(path, "rb") as file:
        start = file.read(4096)
    found = re.search(rb'"generated_at"\s*:\s*"([^"]+)"', start)
    if not found:
        raise ValueError("The committed snapshot has no generated_at marker")
    return parse_time(found.group(1).decode("ascii"))


def pending_wait_metrics(run: dict, now: datetime) -> dict:
    """Diagnose pending age, not why GitHub has queued the workflow."""
    result = {"id": run.get("id"), "status": run.get("status")}
    try:
        started = parse_time(run.get("created_at"))
    except (TypeError, ValueError, OverflowError):
        started = None
    if started is None or (now - started).total_seconds() < -900:
        return {**result, "queue_wait_minutes": None, "queue_severity": "unknown"}
    elapsed = max(0.0, (now - started).total_seconds() / 60)
    severity = ("escalation" if elapsed >= 120 else
                "incident" if elapsed >= 60 else
                "warning" if elapsed >= 15 else "normal")
    return {**result, "queue_wait_minutes": round(elapsed, 2),
            "queue_severity": severity}


def watchdog_decision(generated_at, now, runs: list[dict], *,
                      max_age_hours=MAX_AGE_HOURS,
                      backoff_minutes=BACKOFF_MINUTES):
    now = parse_time(now) if isinstance(now, str) else now
    now = now.astimezone(timezone.utc)
    generated_at = parse_time(generated_at) if isinstance(generated_at, str) else generated_at
    if generated_at is None:
        return {"action": "error", "reason": "missing_snapshot_timestamp"}
    age = (now-generated_at).total_seconds()/3600
    if age < -0.25:
        return {"action": "error", "reason": "snapshot_timestamp_in_future", "age_hours": round(age, 2)}
    data = {"snapshot_age_hours": round(age, 2),
            "max_age_hours": max_age_hours,
            "snapshot_generated_at_utc": generated_at.isoformat(),
            "evaluated_at_utc": now.isoformat()}
    if age <= max_age_hours:
        return {**data, "action": "skip", "reason": "snapshot_fresh"}
    # In-progress work always blocks. Recent pending jobs block; an abandoned
    # queue entry must not prevent recovery indefinitely (12-15 Nov incident).
    # Missing/invalid pending timestamps fail closed rather than guessing.
    ignored_stale_pending_ids = []
    for run in runs:
        if run.get("head_branch") != "main":
            continue
        status = run.get("status")
        if status == "in_progress":
            return {**data, "action": "skip", "reason": "collector_already_running"}
        if status not in PENDING_STATUSES:
            continue
        raw_activity = run.get("updated_at") or run.get("created_at")
        try:
            last_activity = parse_time(raw_activity)
        except (ValueError, TypeError, OverflowError):
            last_activity = None
        if last_activity is None or (now - last_activity).total_seconds() / 60 < STALE_PENDING_MINUTES:
            return {**data, "action": "skip", "reason": "collector_already_running",
                    "blocking_run": pending_wait_metrics(run, now)}
        if run.get("id") is not None:
            ignored_stale_pending_ids.append(run["id"])
    # Do not start new rescue runs every hour when collection itself struggles.
    for run in runs:
        if run.get("head_branch") != "main":
            continue
        started = parse_time(run.get("created_at"))
        if started and -0.25 <= (now-started).total_seconds()/60 < backoff_minutes:
            return {**data, "action": "skip", "reason": "recent_attempt_backoff"}
    return {**data, "action": "dispatch", "reason": "snapshot_exceeds_age_threshold",
            "ignored_stale_pending_run_ids": ignored_stale_pending_ids}


def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "Granbe1l/beta-test")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for audited rescue dispatch")
    now = datetime.now(timezone.utc)
    generated_at = snapshot_generated()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": "Bearer " + token,
    }
    base = f"https://api.github.com/repos/{repo}/actions/workflows/{API_WORKFLOW}"
    res = requests.get(base + "/runs", headers=headers,
                       params={"branch": "main", "per_page": 50}, timeout=20)
    res.raise_for_status()
    payload = res.json()
    # An API error or changed response shape must not be interpreted as
    # "no collector is running": refuse dispatch until runs are verifiable.
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise RuntimeError("Cannot inspect current collector runs; refusing rescue dispatch")
    decision = watchdog_decision(generated_at, now, payload["workflow_runs"])
    if decision["action"] == "dispatch":
        dispatched = requests.post(base + "/dispatches", headers=headers,
                                   json={"ref": "main"}, timeout=20)
        dispatched.raise_for_status()
        if dispatched.status_code != 204:
            raise RuntimeError("Collector workflow dispatch was not acknowledged with HTTP 204")
        decision["dispatched_by"] = "conditional_watchdog_workflow_dispatch"
        decision["github_http_status"] = dispatched.status_code
    output = Path("snapshot-watchdog-audit.json")
    output.write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")
    print("SNAPSHOT WATCHDOG:", json.dumps(decision, sort_keys=True), flush=True)
    if decision["action"] == "error":
        raise RuntimeError("Cannot verify committed snapshot freshness")
    blocking = decision.get("blocking_run") or {}
    if blocking.get("queue_severity") in {"warning", "incident", "escalation"}:
        print(f"::warning::Collector {blocking.get('id')} pending for "
              f"{blocking['queue_wait_minutes']} minutes "
              f"({blocking['queue_severity']}); no duplicate dispatch requested.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Committed GitHub snapshot watchdog\n\n")
            f.write(f"Snapshot age: **{decision['snapshot_age_hours']} hours**; "
                    f"threshold: **{MAX_AGE_HOURS} hours**.\n\n")
            f.write(f"Action: **{decision['action']}** · {decision['reason']}.\n\n")
            f.write("Any backup workflow_dispatch counts as a rescue attempt, "
                    "**never** as proof of on-time four-hour cron execution.\n")


if __name__ == "__main__":
    main()
