"""Promote audited replacements without destroying historical source records."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import gzip
import json
import os
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.audit_candidate_pool import MIN_ROWS, SOURCES
from scripts.replacement_plan import proposed_swaps
from src.analytics.read import load_reports
from src.analytics.snapshot import SNAPSHOT_PATH, read_snapshot
from src.collectors.client import GitHubClient
from src.collectors.sync import sync_one, sync_lock
from src.config.settings import Settings
from src.database.models import Candidate, Repository, SelectionRun, SyncCheckpoint
from src.database.store import init_db, make_engine, session_factory
from src.discovery.selection import category, parse_dt, size_tier, validate_candidate
from src.ui.observed import verified_joint_cohort

ARCHIVE = Path("data/archived_repository_reports.json.gz")
RECEIPT = Path("data/verified_cohort_change_receipt.json")


def dt(value):
    if not isinstance(value, str):
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
    except ValueError:
        return None


def candidate_has_verified_proof(proposal, audit, now):
    created = dt(audit.get("generated_at_utc"))
    if not created or not timedelta(0) <= now - created <= timedelta(hours=12):
        return False
    for item in audit.get("results") or []:
        if item.get("full_name") != proposal["candidate_name"] or item.get("github_id") != proposal["candidate_github_id"]:
            continue
        if item.get("verdict") != "verified_candidate":
            return False
        evidence = item.get("sources") or {}
        return all(
            (evidence.get(s) or {}).get("status") == "verified_28d"
            and (evidence[s].get("records") or 0) >= MIN_ROWS[s]
            and dt(evidence[s].get("source_start_utc")) is not None
            and dt(evidence[s]["source_start_utc"]) <= created - timedelta(days=28)
            for s in SOURCES
        )
    return False


def identity_matches(raw, proposal, now):
    created = dt(raw.get("created_at"))
    return (
        raw.get("id") == proposal["candidate_github_id"]
        and raw.get("full_name") == proposal["candidate_name"]
        and validate_candidate(raw, now, 30) is None
        and category(raw) == proposal["category"]
        and size_tier(raw) == proposal["size_tier"]
        and created is not None and created <= now - timedelta(days=29)
    )


def recollected_complete(session, rid, now):
    for source in SOURCES:
        cp = session.get(SyncCheckpoint, (rid, source))
        if not cp or cp.status != "complete" or not cp.coverage_start or not cp.last_success_at:
            return False
        start = cp.coverage_start.replace(tzinfo=timezone.utc) if cp.coverage_start.tzinfo is None else cp.coverage_start
        latest = cp.last_success_at.replace(tzinfo=timezone.utc) if cp.last_success_at.tzinfo is None else cp.last_success_at
        if (start > now - timedelta(days=28) or latest < now - timedelta(hours=12)
                or cp.records_fetched < MIN_ROWS[source]):
            return False
    return True


def archive_originals(swaps, now):
    with gzip.open(SNAPSHOT_PATH, "rt", encoding="utf-8") as fh:
        original = json.load(fh)
    indexed = {r["repository"]["id"]: r for r in original["reports"]}
    if ARCHIVE.exists():
        with gzip.open(ARCHIVE, "rt", encoding="utf-8") as fh:
            history = json.load(fh)
    else:
        history = {"schema_version": 1, "archived": []}
    saved = {item["original_github_id"] for item in history["archived"]}
    for swap in swaps:
        rid = swap["old_id"]
        if rid in saved or rid not in indexed:
            raise ValueError("Missing original source or duplicate archive")
        history["archived"].append({
            "original_github_id": rid,
            "replaced_by_github_id": swap["new_id"],
            "archived_at": now.isoformat(),
            "source_snapshot_generated_at": original["generated_at"],
            "full_original_report": indexed[rid],
        })
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    tmp = ARCHIVE.with_suffix(".gz.tmp")
    with gzip.open(tmp, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(history, fh, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(ARCHIVE)


def promote(proof, *, limit=6, request_limit=350):
    # The reviewed cohort is pinned. Candidate proofs do not authorize a
    # membership change or revision of the historical cutover receipt.
    raise ValueError(
        "The 50-repository cohort is pinned; promotion requires an owner-approved "
        "cohort migration with a versioned manifest and compatible refresh gates. "
        "No data was changed. Use the read-only candidate audit workflows."
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/promote_verified_candidates.py candidate-verified-audit.json")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    receipt = promote(data, limit=int(os.getenv("PROMOTION_MAX_SWAPS", "6")),
                      request_limit=int(os.getenv("PROMOTION_API_BUDGET", "350")))
    print("STRICT SOURCE PROMOTION", json.dumps({
        "before": receipt["verified_before"], "after": receipt["verified_after"],
        "swapped": len(receipt["replacements"]), "requests": receipt["request_count"]
    }))
