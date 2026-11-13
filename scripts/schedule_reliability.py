"""Report real scheduled GitHub refresh reliability; never fabricate cycles.

Reads the public repository's Actions run history using an optional workflow
token. Only actual schedule events can satisfy the consecutive-run gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import sys

import requests


def parsed(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc)


def schedule_health(runs: list[dict], required: int = 3, *,
                    now=None, max_schedule_age_hours=6.5) -> dict:
    """Require recent, successful, evenly spaced *actual cron* events.

    Even three historically perfect runs cannot establish that a schedule
    still works if the latest cron is older than the freshness budget.
    """
    if required < 2:
        raise ValueError("At least two scheduled runs are required")
    now = parsed(now) if isinstance(now, str) else (now or datetime.now(timezone.utc))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    chosen = sorted(
        (r for r in runs if r.get("event") == "schedule"
         and r.get("head_branch") == "main" and r.get("created_at")),
        key=lambda r: r["created_at"], reverse=True,
    )[:required]
    result = {
        "status": "insufficient_history", "required": required,
        "actual_scheduled_runs": len(chosen),
        "successful_scheduled_runs": sum(
            r.get("status") == "completed" and r.get("conclusion") == "success"
            for r in chosen),
        "links": [r.get("html_url") for r in chosen if r.get("html_url")],
        "evaluated_at_utc": now.isoformat(),
    }
    if chosen:
        newest = parsed(chosen[0]["created_at"])
        age_hours = (now - newest).total_seconds() / 3600
        result["latest_scheduled_at_utc"] = newest.isoformat()
        result["latest_scheduled_run_age_hours"] = round(age_hours, 2)
        result["latest_schedule_is_recent"] = (
            -0.25 <= age_hours <= max_schedule_age_hours
        )
    else:
        result["latest_scheduled_at_utc"] = None
        result["latest_scheduled_run_age_hours"] = None
        result["latest_schedule_is_recent"] = False
    if len(chosen) < required:
        return result
    if not all(r.get("status") == "completed" and
               r.get("conclusion") == "success" for r in chosen):
        result["status"] = "needs_review"
        return result
    timestamps = [parsed(r["created_at"]) for r in chosen]
    spacing = [
        (timestamps[i] - timestamps[i + 1]).total_seconds() / 3600
        for i in range(required - 1)
    ]
    result["observed_intervals_hours"] = [round(v, 2) for v in spacing]
    if not all(3 <= hours <= 6.5 for hours in spacing):
        result["status"] = "needs_review"
    elif not result["latest_schedule_is_recent"]:
        result["status"] = "stale_schedule"
    else:
        result["status"] = "verified_recent_cycles"
    return result


def main():
    repo = os.getenv("GITHUB_REPOSITORY", "Granbe1l/beta-test")
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/"
           "public-snapshot.yml/runs")
    res = requests.get(url, headers=headers, timeout=20,
                       params={"event": "schedule", "branch": "main",
                               "per_page": 20})
    res.raise_for_status()
    output = schedule_health(res.json().get("workflow_runs") or [])
    # A dated, machine-readable proof from only actual 'schedule' events.
    # This does not modify GitHub data or create synthetic green runs.
    from pathlib import Path
    Path("schedule-reliability.json").write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print("SCHEDULE RELIABILITY:", json.dumps(output, sort_keys=True))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n### Four-hour schedule reliability (actual events)\n\n")
            handle.write(
                f"Status: **{output['status']}** · "
                f"{output['successful_scheduled_runs']}/{output['required']} "
                "recent scheduled runs successful.\n\n"
            )
            if output.get("latest_scheduled_run_age_hours") is not None:
                handle.write(
                    f"Most recent scheduled run age: "
                    f"**{output['latest_scheduled_run_age_hours']} h** · "
                    f"recent: **{output['latest_schedule_is_recent']}**.\n\n"
                )
            if output.get("observed_intervals_hours"):
                handle.write("Observed run intervals (hours): " +
                             ", ".join(map(str, output["observed_intervals_hours"])) +
                             "\n\n")
            handle.write("Only `schedule` events count. Push/manual runs "
                         "cannot satisfy this gate.\n")


if __name__ == "__main__":
    main()
