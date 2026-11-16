"""Read-only, per-run GitHub Actions queue and runner-start evidence.

This audit records only provider timestamps and public workflow/job IDs.
It cannot explain why GitHub held a run, guarantee scheduling punctuality,
or cancel queued jobs. API failures result in an honest unavailable receipt,
never a synthetic zero-minute queue or a failed data collector.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import requests

AUDIT_PATH = Path("collector-queue-audit.json")
WARNING_MINUTES = 15
INCIDENT_MINUTES = 60
ESCALATION_MINUTES = 120


def timestamp(raw: str) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError("missing_timestamp")
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp_without_timezone")
    return dt.astimezone(timezone.utc)


def queue_severity(minutes: float) -> str:
    if minutes >= ESCALATION_MINUTES:
        return "escalation"
    if minutes >= INCIDENT_MINUTES:
        return "incident"
    if minutes >= WARNING_MINUTES:
        return "warning"
    return "normal"


def queue_receipt(run: dict, jobs: list[dict], *, job_name: str = "refresh") -> dict:
    """Distinguish run->job creation delay from job->runner start delay."""
    if not isinstance(run, dict) or not isinstance(jobs, list):
        raise ValueError("invalid_workflow_or_jobs_payload")
    matching = [
        job for job in jobs
        if isinstance(job, dict) and job.get("name") == job_name
    ]
    if len(matching) != 1:
        raise ValueError("expected_exactly_one_refresh_job")
    job = matching[0]
    created = timestamp(run.get("created_at"))
    job_created = timestamp(job.get("created_at"))
    started = timestamp(job.get("started_at"))
    if not created <= job_created <= started:
        raise ValueError("inconsistent_provider_timestamps")
    pre_job = (job_created - created).total_seconds() / 60
    runner = (started - job_created).total_seconds() / 60
    return {
        "status": "verified",
        "run_id": run.get("id"),
        "job_id": job.get("id"),
        "trigger_event": run.get("event"),
        "run_created_utc": created.isoformat(),
        "job_created_utc": job_created.isoformat(),
        "job_started_utc": started.isoformat(),
        "pre_job_queue_minutes": round(pre_job, 2),
        "runner_start_wait_seconds": round((started - job_created).total_seconds(), 2),
        "total_before_job_start_minutes": round(pre_job + runner, 2),
        "severity": queue_severity(pre_job),
        "thresholds_minutes": {
            "warning": WARNING_MINUTES,
            "incident": INCIDENT_MINUTES,
            "escalation": ESCALATION_MINUTES,
        },
        "interpretation": "GitHub timestamps show delay; they do not establish its provider root cause.",
    }


def inspect_current_run(*, repo: str, run_id: str, token: str,
                        client=requests) -> dict:
    if not token or not repo or not run_id.isdecimal():
        raise ValueError("missing_or_invalid_github_context")
    base = "https://api.github.com/repos/" + repo + "/actions/runs/" + run_id
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": "Bearer " + token,
    }
    def get_json(url: str) -> dict:
        response = client.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    run = get_json(base)
    jobs = get_json(base + "/jobs?per_page=100")
    return queue_receipt(run, jobs.get("jobs"))


def main() -> None:
    repo = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    token = os.getenv("GITHUB_TOKEN", "")
    try:
        receipt = inspect_current_run(repo=repo, run_id=run_id, token=token)
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError) as exc:
        # Observability MUST NOT prevent a real, validated 50-repository refresh.
        # No exception bodies: GitHub API exceptions can contain request context.
        receipt = {
            "status": "unavailable",
            "run_id": run_id or None,
            "error_type": type(exc).__name__,
            "note": "Provider queue timestamps unavailable; no delay inferred.",
        }
    AUDIT_PATH.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    print("COLLECTOR QUEUE AUDIT:", json.dumps(receipt, sort_keys=True), flush=True)
    if receipt.get("severity") in {"warning", "incident", "escalation"}:
        minutes = receipt["pre_job_queue_minutes"]
        print(f"::warning::GitHub pre-job queue delay {minutes:.2f} minutes "
              f"({receipt['severity']}); check run {run_id} before another dispatch.")


if __name__ == "__main__":
    main()
