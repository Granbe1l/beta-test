"""Verify completed *scheduled* collectors with their actual source-audit artifacts.

A successful GitHub workflow is not proof of 50/50 Verified source windows.
This separate receipt checker fails closed for absent/expired/invalid artifacts.
It only promotes the **evidence status** if the independent cadence test
has already observed 3 recent, successful and correctly spaced schedule runs.
Push, manual, workflow_run, and mock runs do not qualify.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import zipfile

import requests

EXPECTED = 50
SOURCES = ("issues", "pull_requests", "workflow_runs")
ARTIFACT_NAME = "github-50-repo-source-audit"
REQUIRED = ("snapshot-audit.json", "coverage-readiness.json", "open-inventory-triage.json")
MAX_ZIP_BYTES = 25 * 1024 * 1024


def read_receipt(zip_bytes: bytes) -> dict:
    """Parse the *actual* GitHub archive without extracting untrusted paths."""
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ValueError("audit_archive_exceeds_limit")
    result = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for expected in REQUIRED:
            names = [name for name in archive.namelist()
                     if name == expected or name.endswith("/" + expected)]
            if len(names) != 1:
                raise ValueError("audit_file_missing_or_ambiguous:" + expected)
            info = archive.getinfo(names[0])
            if info.file_size > 12 * 1024 * 1024:
                raise ValueError("audit_file_exceeds_limit:" + expected)
            with archive.open(info) as file:
                content = file.read(12 * 1024 * 1024 + 1)
                if len(content) > 12 * 1024 * 1024:
                    raise ValueError("audit_file_exceeds_limit:" + expected)
                result[expected] = json.loads(content)
    return result


def validate_source_receipt(files: dict, *, expected: int = EXPECTED) -> dict:
    """Require 3 distinct-source completions AND independently full open Issues."""
    audit = files["snapshot-audit.json"]
    coverage = files["coverage-readiness.json"]
    inventory = files["open-inventory-triage.json"]
    rows = audit.get("repositories")
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError("source_repo_denominator_mismatch")
    names = [r.get("name") for r in rows]
    if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != expected:
        raise ValueError("source_repo_identity_missing_or_duplicate")
    summary = audit.get("coverage_summary") or {}
    for source in SOURCES:
        stats = summary.get(source) or {}
        if any(stats.get(k) != expected for k in ("total_repositories", "complete", "verified_28d")):
            raise ValueError("source_window_incomplete:" + source)
        if any(stats.get(k) != 0 for k in ("partial", "stale", "failed", "unavailable")):
            raise ValueError("source_status_regression:" + source)
        if coverage.get("source_verified_28d", {}).get(source) != expected:
            raise ValueError("checkpoint_28d_incomplete:" + source)
    if (coverage.get("tracked") != expected or
        coverage.get("verified_joint_28d") != expected or
        coverage.get("window_days") != 28 or
        coverage.get("stale_hours") != 12):
        raise ValueError("strict_joint_28d_not_verified")
    if (summary.get("open_backlog", {}).get("complete") != expected or
        summary.get("open_backlog", {}).get("total_repositories") != expected or
        inventory.get("total_selected_repositories") != expected or
        inventory.get("fresh_full_open_inventories") != expected or
        inventory.get("all_full_open_inventories_current") is not True or
        inventory.get("gaps") != []):
        raise ValueError("full_open_inventory_not_complete")
    for row in rows:
        if row.get("open_backlog_status") != "complete":
            raise ValueError("repository_open_inventory_not_complete")
        if any((row.get("status") or {}).get(s) != "complete" for s in SOURCES):
            raise ValueError("repository_source_not_complete")
    return {"tracked": expected, "joint_verified_28d": expected,
            "full_open_inventories": expected, "scope": "dated collector artifact, not live GitHub state"}


def fetch_run_receipt(session, *, api_base: str, run_id: int, headers: dict) -> dict:
    """Observe one actual run's retained audit. Never infer from green status."""
    if type(run_id) is not int or run_id < 1:
        raise ValueError("invalid_run_id")
    query = session.get(f"{api_base}/actions/runs/{run_id}/artifacts",
                        headers=headers, params={"per_page": 100}, timeout=20)
    query.raise_for_status()
    artifacts = query.json().get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("artifact_listing_unavailable")
    matches = [a for a in artifacts if a.get("name") == ARTIFACT_NAME
               and a.get("expired") is False]
    if len(matches) != 1:
        raise ValueError("source_audit_artifact_missing_expired_or_duplicate")
    art = matches[0]
    if (not isinstance(art.get("size_in_bytes"), int)
            or art["size_in_bytes"] > MAX_ZIP_BYTES):
        raise ValueError("source_audit_artifact_size_invalid")
    url = f"{api_base}/actions/artifacts/{art['id']}/zip"
    with session.get(url, headers=headers, timeout=40, stream=True) as download:
        download.raise_for_status()
        chunks, used = [], 0
        for part in download.iter_content(chunk_size=65536):
            used += len(part)
            if used > MAX_ZIP_BYTES:
                raise ValueError("source_audit_download_exceeds_limit")
            chunks.append(part)
    return validate_source_receipt(read_receipt(b"".join(chunks)))


def evaluate_gate(schedule: dict, receipts: list[dict]) -> dict:
    ids = schedule.get("run_ids") or []
    valid_ids = (len(ids) == 3 and len(set(ids)) == 3 and
                 all(type(i) is int and i > 0 for i in ids))
    good = (valid_ids and len(receipts) == 3 and
            {r.get("run_id") for r in receipts} == set(ids) and
            all(r.get("status") == "verified" for r in receipts))
    passed = schedule.get("status") == "verified_recent_cycles" and good
    return {
        "status": "verified_operational_cycles" if passed else (
            "blocked_schedule" if schedule.get("status") != "verified_recent_cycles"
            else "blocked_source_evidence"),
        "cadence_status": schedule.get("status", "unknown"),
        "actual_schedule_run_ids": ids,
        "source_verified_runs": sum(r.get("status") == "verified" for r in receipts),
        "required": 3,
        "receipts": receipts,
        "note": "Three actual on-time scheduled successes with 50/50 source AND full-open inventory artifacts, never push/manual",
    }


def main() -> None:
    schedule = json.loads(Path("schedule-reliability.json").read_text(encoding="utf-8"))
    ids = schedule.get("run_ids") or []
    receipts = []
    if schedule.get("status") == "verified_recent_cycles" and len(ids) == 3:
        repo = os.environ.get("GITHUB_REPOSITORY", "Granbe1l/beta-test")
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("Actions-read token is missing; refuse unverifiable proof")
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "Authorization": f"Bearer {token}"}
        api = f"https://api.github.com/repos/{repo}"
        with requests.Session() as session:
            for run_id in ids:
                try:
                    values = fetch_run_receipt(
                        session, api_base=api, run_id=run_id, headers=headers)
                    receipts.append({"run_id": run_id, "status": "verified", **values})
                except (ValueError, KeyError, zipfile.BadZipFile,
                        requests.RequestException, json.JSONDecodeError):
                    # Do not leak GitHub auth headers or external error payloads.
                    receipts.append({"run_id": run_id, "status": "unverified",
                                     "reason": "source_artifact_unreadable_or_incomplete"})
    result = evaluate_gate(schedule, receipts)
    Path("scheduled-source-proof.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SCHEDULE + SOURCE GATE:", json.dumps(result, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("\n### Strict scheduled-run source-audit gate\n\n")
            file.write(f"Status: **{result['status']}**; source-audited "
                       f"runs: **{result['source_verified_runs']}/3**.\n\n")
            file.write("Cadence alone and workflow success alone never "
                       "certify current 50/50 data.\n")
    # Block *claims*, not audit execution: workflow is an observer, not a
    # collector, and cannot generate three missing cron events.


if __name__ == "__main__":
    main()
