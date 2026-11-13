"""Conditional safety net for delayed or dropped GitHub Actions cron events.

The primary six-hour scheduled collection remains unchanged. This hourly
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
MAX_AGE_HOURS = 8
BACKOFF_MINUTES = 90


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
    # Any queued/in-progress collector means the rescue run is already covered.
    for run in runs:
        if run.get("head_branch") == "main" and run.get("status") in ("queued", "in_progress", "waiting", "requested", "pending"):
            return {**data, "action": "skip", "reason": "collector_already_running"}
    # Do not start new rescue runs every hour when collection itself struggles.
    for run in runs:
        if run.get("head_branch") != "main":
            continue
        started = parse_time(run.get("created_at"))
        if started and -0.25 <= (now-started).total_seconds()/60 < backoff_minutes:
            return {**data, "action": "skip", "reason": "recent_attempt_backoff"}
    return {**data, "action": "dispatch", "reason": "snapshot_exceeds_age_threshold"}


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
                       params={"branch": "main", "per_page": 15}, timeout=20)
    res.raise_for_status()
    decision = watchdog_decision(generated_at, now, res.json().get("workflow_runs") or [])
    if decision["action"] == "dispatch":
        dispatched = requests.post(base + "/dispatches", headers=headers,
                                   json={"ref": "main"}, timeout=20)
        dispatched.raise_for_status()
        decision["dispatched_by"] = "conditional_watchdog_workflow_dispatch"
        decision["github_http_status"] = dispatched.status_code
    output = Path("snapshot-watchdog-audit.json")
    output.write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")
    print("SNAPSHOT WATCHDOG:", json.dumps(decision, sort_keys=True), flush=True)
    if decision["action"] == "error":
        raise RuntimeError("Cannot verify committed snapshot freshness")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Committed GitHub snapshot watchdog\n\n")
            f.write(f"Snapshot age: **{decision['snapshot_age_hours']} hours**; "
                    f"threshold: **{MAX_AGE_HOURS} hours**.\n\n")
            f.write(f"Action: **{decision['action']}** · {decision['reason']}.\n\n")
            f.write("Any backup workflow_dispatch counts as a rescue attempt, "
                    "**never** as proof of on-time six-hour cron execution.\n")


if __name__ == "__main__":
    main()
