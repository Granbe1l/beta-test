"""One-time, evidence-anchored 75 -> 50 curated public GitHub migration.

Run BEFORE restoring the ephemeral SQLite database in the snapshot workflow.
Only selected repository identities are retained in the active snapshot;
25 removed, original report dictionaries are saved in a separate lossless
archive and historical commit remains available.

Never assert future 50/50 Verified status just because they passed on the
dated original audit. Future source freshness is re-evaluated on every read.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import Counter
import gzip
import hashlib
import json
import os
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/github_public_snapshot.json.gz"
MANIFEST = ROOT / "data/curated_50_manifest.json"
ARCHIVE = ROOT / "data/archived_75_to_50_reports.json.gz"
RECEIPT = ROOT / "data/curated_50_transition_receipt.json"
# The original 75-project binary is immutably reachable in this reviewed merge.
SOURCE_75_COMMIT = "0b7e80867c76d1dd3ba824a8749742e6757ff431"
SOURCES = ("issues", "pull_requests", "workflow_runs")


def dt(value):
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def audit_qualifies(report: dict, *, at: datetime) -> bool:
    """Independent all-source coverage, not a precomputed UI flag."""
    for source in SOURCES:
        cp = (report.get("coverage") or {}).get(source) or {}
        if cp.get("status") != "complete":
            return False
        if not cp.get("coverage_start") or not cp.get("last_success_at"):
            return False
        if dt(cp["coverage_start"]) > at - timedelta(days=28):
            return False
        if dt(cp["last_success_at"]) < at - timedelta(hours=12):
            return False
    return True


def validate_manifest(manifest: dict):
    names = manifest.get("selected") or []
    if (manifest.get("schema_version") != 1
            or manifest.get("target_repositories") != 50
            or len(names) != 50 or len(set(names)) != 50
            or manifest.get("source_tracked") != 75):
        raise ValueError("Refusing invalid or duplicate audited 50-project manifest")
    if names != sorted(names):
        raise ValueError("Manifest identities must be stable, sorted and reviewable")
    return names


def transition(original: dict, manifest: dict, *, actual_snapshot_sha256: str,
               now=None) -> tuple[dict, dict, dict]:
    """Return active snapshot, archived removed reports and transition receipt."""
    selected = validate_manifest(manifest)
    if (original.get("schema_version") != 1
            or len(original.get("reports") or []) != 75
            or original.get("generated_at") != manifest["source_snapshot_generated_at"]
            or actual_snapshot_sha256 != manifest["source_snapshot_sha256"]):
        raise ValueError(
            "The 75-project source snapshot changed; refuse an unaudited reselection"
        )
    at = dt(original["generated_at"])
    reports = original["reports"]
    by_name = {r["repository"]["full_name"]: r for r in reports}
    if len(by_name) != 75 or not set(selected).issubset(by_name):
        raise ValueError("Source identity changed or repository duplicated")
    eligible = {
        name for name, report in by_name.items()
        if audit_qualifies(report, at=at)
    }
    if len(eligible) != manifest["source_verified_joint_28d"]:
        raise ValueError("Original strict Verified count no longer matches proof")
    for name in selected:
        record = by_name[name]
        if not audit_qualifies(record, at=at):
            raise ValueError("A selected repository is not Verified: " + name)
        if len(record.get("pr_rows") or []) < 2 or len(record.get("ci_rows") or []) < 2:
            raise ValueError("Selected repository lacks required observed PR and CI data: " + name)
    kept = [r for r in reports if r["repository"]["full_name"] in selected]
    removed = [r for r in reports if r["repository"]["full_name"] not in selected]
    if len(kept) != 50 or len(removed) != 25:
        raise ValueError("Cohort transition failed 50 retained / 25 archived check")
    if len({r["repository"]["id"] for r in reports}) != 75:
        raise ValueError("Duplicate GitHub repository IDs in source snapshot")

    stamp = dt(now or datetime.now(timezone.utc)).isoformat()
    previous = original.get("selection") or {}
    if not isinstance(previous.get("id"), int) or previous.get("status") != "complete":
        raise ValueError("No auditable completed original SelectionRun")
    new_id = previous["id"] + 1
    decisions = []
    for idx, report in enumerate(sorted(reports, key=lambda r:r["repository"]["full_name"]), 1):
        meta = report["repository"]
        retain = meta["full_name"] in selected
        decisions.append({
            "id": idx,
            "selection_run_id": new_id,
            "repo_id": meta["id"],
            "full_name": meta["full_name"],
            "url": meta["url"],
            "category": meta.get("category") or "Other",
            "stars": meta.get("stars") or 0,
            "decision": "selected" if retain else "rejected",
            "reason": ("Original 28d all-source Verified and sufficient observed PR/CI evidence"
                       if retain else "Archived during reviewed 75-to-50 portfolio curation"),
        })
    new_selection = {
        "id": new_id,
        "parameters": {
            "purpose": "curated_verified_50",
            "method": "strict_joint_28d_selection",
            "source_snapshot_generated_at": original["generated_at"],
            "source_audit_run": manifest["source_audit_run"],
            "manifest": "data/curated_50_manifest.json",
            "archived_original_reports": "data/archived_75_to_50_reports.json.gz",
            "prior_selection_id": previous["id"],
            "cohort_version": 2,
        },
        "candidates": 75, "selected": 50,
        "status": "complete",
        "notes": (
            "50 of 56 independently Verified 28-day GitHub repositories retained. "
            "25 original source reports archived losslessly. Historical trends "
            "across the changed population must not be compared as a fixed cohort."
        ),
        "decisions": decisions,
    }
    updated = dict(original)
    updated["reports"] = kept
    updated["selection"] = new_selection
    updated["curation"] = {
        "version": 2, "target": 50,
        "archive": "data/archived_75_to_50_reports.json.gz",
        "audit_snapshot_utc": original["generated_at"],
        "changed_at_utc": stamp,
    }
    # Match SQL restoration: repo selection metadata points to the new run.
    for r in kept:
        r["repository"]["selected"] = True
        r["repository"]["selection_run_id"] = new_id

    archived = {
        "schema_version": 1,
        "archived_at_utc": stamp,
        "source_snapshot_generated_at": original["generated_at"],
        "source_snapshot_sha256": actual_snapshot_sha256,
        "original_selection": previous,
        "original_source": original.get("source"),
        "original_mode": original.get("mode"),
        "removed_reports": removed,
        "removed_count": 25,
        "reason": "Portfolio 75-to-50 cohort curation; all original GitHub evidence preserved",
    }
    languages = Counter(r["repository"].get("language") or "Unknown" for r in kept)
    stars = Counter(
        "small" if r["repository"]["stars"] < 500 else
        "medium" if r["repository"]["stars"] < 5000 else "large"
        for r in kept
    )
    receipt = {
        "schema_version": 1, "decision": "75_to_50_curated_verified",
        "transition_at_utc": stamp, "audit_snapshot_at_utc": original["generated_at"],
        "audit_url": manifest["source_audit_run"],
        "original_snapshot_sha256": actual_snapshot_sha256,
        "original_count":75, "original_verified_28d":len(eligible),
        "selected_count":50, "selected_verified_28d_at_audit":50,
        "removed_count":25,
        "selected_repositories": sorted(selected),
        "archived_repositories": sorted(r["repository"]["full_name"] for r in removed),
        "language_distribution": dict(sorted(languages.items())),
        "size_tiers": dict(sorted(stars.items())),
        "archive_path": "data/archived_75_to_50_reports.json.gz",
        "future_verified_is_dynamic": True,
        "claim": (
            "50 identities passed the ORIGINAL dated audit. This receipt does "
            "not prove all 50 remain Verified after any later refresh."
        ),
    }
    return updated, archived, receipt


def _write_gzip(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=9) as out:
        json.dump(payload, out, ensure_ascii=False, separators=(",", ":"))
    os.replace(temporary, path)


def original_audit_blob() -> bytes:
    """Fetch exactly the previously reviewed 75-project binary from Git history.

    Used only to reconstruct lost archive/receipt if a first publication
    committed its 50-project snapshot without both provenance artifacts.
    Actions must fetch the pinned historical commit before calling this.
    """
    try:
        return subprocess.run(
            ["git", "show", SOURCE_75_COMMIT + ":data/github_public_snapshot.json.gz"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=30,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        raise RuntimeError(
            "Original audited 75-project commit is unavailable; refuse archive recovery"
        ) from None


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    names = validate_manifest(manifest)
    raw = SNAPSHOT.read_bytes()
    payload = json.loads(gzip.decompress(raw))
    previous_names = {r["repository"]["full_name"] for r in payload.get("reports") or []}
    if len(payload.get("reports") or []) == 50:
        if previous_names != set(names):
            raise ValueError("Published 50-project membership differs from reviewed manifest")
        if ARCHIVE.exists() and RECEIPT.exists():
            with gzip.open(ARCHIVE, "rt", encoding="utf-8") as stream:
                archived = json.load(stream)
            receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
            if (len(archived.get("removed_reports") or []) != 25
                    or receipt.get("selected_count") != 50
                    or receipt.get("removed_count") != 25
                    or set(receipt.get("selected_repositories") or []) != set(names)):
                raise ValueError("Existing archive or receipt is incomplete; refusing to ignore it")
            print("CURATED 50: published membership and 25-record archive verified")
            return
        if ARCHIVE.exists() != RECEIPT.exists():
            raise ValueError("Only one transition artifact exists; refusing partial recovery")
        # A first run can commit a 50-repo binary before its archive due to
        # a publisher mistake. Recover strictly from the original SHA-pinned
        # 75-repo binary WITHOUT overwriting more recent 50-repo source data.
        source_blob = original_audit_blob()
        before = json.loads(gzip.decompress(source_blob))
        source_hash = hashlib.sha256(source_blob).hexdigest()
        _, archive, receipt = transition(
            before, manifest, actual_snapshot_sha256=source_hash,
        )
        _write_gzip(ARCHIVE, archive)
        RECEIPT.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("CURATED 50: recovered original 25-project archive and receipt "
              "without altering the current 50-project snapshot")
        return
    if ARCHIVE.exists() or RECEIPT.exists():
        raise ValueError("An archive/receipt exists but source snapshot is still 75; review before retry")
    update, archive, receipt = transition(
        payload, manifest, actual_snapshot_sha256=hashlib.sha256(raw).hexdigest()
    )
    # Preserve original records before changing the active snapshot.
    _write_gzip(ARCHIVE, archive)
    try:
        RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
        _write_gzip(SNAPSHOT, update)
    except Exception:
        # In GitHub Actions the source is still the original git checkout, so
        # a failed transition never publishes a partial altered main branch.
        raise
    print("CURATED 50 TRANSITION:", json.dumps({
        "selected":50,"archived":25,"verified_at_prior_audit":50,
        "languages":len(receipt["language_distribution"]),
        "archive":str(ARCHIVE),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
