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
    now = datetime.now(timezone.utc)
    previous, _, metadata = read_snapshot(now=now)
    if len(previous) != 75 or metadata["stale"]:
        raise ValueError("The active 75-repo snapshot must be current before replacement")
    verified_before = len(verified_joint_cohort(previous, 28, now))
    proposal = proposed_swaps(previous, proof, now=now)
    if not proposal["candidate_evidence_fresh"]:
        raise ValueError("Candidate audit expired; cannot promote")
    candidates = proposal["proposed_unapproved_swaps"][:limit]
    if not candidates:
        raise ValueError("No independently verified, diversity-matched candidates")
    cfg = Settings.from_env()
    api = GitHubClient(cfg.github_token, cfg.timeout_seconds, cfg.max_retries,
                       max_requests=request_limit)
    engine = make_engine(cfg.database_url)
    init_db(engine)
    changes, skipped = [], []
    try:
        with sync_lock(engine):
            with session_factory(engine)() as session:
                active = list(session.scalars(select(Repository).where(Repository.selected.is_(True))))
                if len(active) != 75:
                    raise ValueError("Wrong restored active cohort size")
                original_ids = {r["repository"]["id"] for r in previous}
                for item in candidates:
                    name = item["candidate_name"]
                    if not candidate_has_verified_proof(item, proof, now):
                        skipped.append([name, "invalid 28-day source proof"])
                        continue
                    old = session.get(Repository, item["retain_original_github_id"])
                    if not old or not old.selected or old.id not in original_ids or old.full_name != item["exclude_from_future_active_cohort_only"]:
                        skipped.append([name, "original repository mismatch"])
                        continue
                    try:
                        raw, _ = api.get("/repos/" + name)
                    except Exception:
                        skipped.append([name, "live metadata retrieval failed"])
                        continue
                    if not identity_matches(raw, item, now) or session.get(Repository, raw["id"]):
                        skipped.append([name, "identity, category, size or eligibility changed"])
                        continue
                    r = Repository(
                        id=raw["id"], full_name=raw["full_name"],
                        owner=raw["owner"]["login"], name=raw["name"],
                        url=raw["html_url"], language=raw["language"],
                        category=category(raw), stars=raw["stargazers_count"],
                        created_at=parse_dt(raw["created_at"]),
                        pushed_at=parse_dt(raw["pushed_at"]),
                        default_branch=raw.get("default_branch", "main"),
                        is_fork=False, archived=False, selected=False,
                    )
                    session.add(r)
                    session.commit()
                    # Fetch 29 days, not 28, to leave a publication-time buffer.
                    results = [sync_one(session, api, r, source, cfg, now=now,
                                        min_window_days=29) for source in SOURCES]
                    if not all(v["status"] == "complete" for v in results) or not recollected_complete(session, r.id, datetime.now(timezone.utc)):
                        skipped.append([name, "real source re-collection incomplete"])
                        continue
                    old.selected = False
                    r.selected = True
                    r.selected_at = now
                    session.commit()
                    changes.append({"old_id": old.id, "old": old.full_name,
                                    "new_id": r.id, "new": r.full_name,
                                    "sources": results})
                if not changes:
                    raise ValueError("Zero safe replacements; original published dataset remains unchanged")
                updated = load_reports(session, now=datetime.now(timezone.utc),
                                       observation_days=cfg.comparison_days, stale_hours=cfg.stale_hours)
                verified_after = len(verified_joint_cohort(updated, 28, datetime.now(timezone.utc)))
                if len(updated) != 75 or verified_after < verified_before + len(changes):
                    raise ValueError("Unverified swap or cohort count regression; refusing publication")
                archive_originals(changes, now)
                selection = SelectionRun(
                    started_at=now, completed_at=datetime.now(timezone.utc),
                    parameters={"method": "strict_verified_swap", "audit_at": proof["generated_at_utc"],
                                "archived_data_path": str(ARCHIVE), "changes": changes},
                    candidate_count=75 + len(changes), accepted_count=75, status="complete",
                    notes=("Previously nonverified sources remain in immutable historical archive. "
                           "Replacing project identities changes the curated cohort; compare across "
                           "versions only after accounting for composition changes."),
                )
                session.add(selection)
                session.flush()
                replaced_ids = {x["new_id"] for x in changes}
                for row in session.scalars(select(Repository).where(Repository.selected.is_(True))):
                    row.selection_run_id = selection.id
                    session.add(Candidate(
                        selection_run_id=selection.id, repo_id=row.id,
                        full_name=row.full_name, url=row.url, category=row.category,
                        stars=row.stars, decision="selected",
                        reason="verified replacement" if row.id in replaced_ids else "retained",
                    ))
                session.commit()
                receipt = {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "proof_at": proof["generated_at_utc"],
                    "active": 75,
                    "verified_before": verified_before,
                    "verified_after": verified_after,
                    "replacements": changes,
                    "skipped": skipped,
                    "request_count": api.request_count,
                    "archive": str(ARCHIVE),
                    "caveat": "Curated and composition-changing sample, not random or representative of all GitHub projects.",
                }
                RECEIPT.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
                return receipt
    finally:
        engine.dispose()


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
