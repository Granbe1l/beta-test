"""Restore last public source snapshot into the ephemeral SQLite collector.

A scheduled runner must not discard earlier GitHub source records or
checkpoints; no synthetic records or credentials are restored here.
"""
from __future__ import annotations
import gzip
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.models import (
    Candidate, Issue, Observation, PullRequest, Repository,
    SelectionRun, SyncCheckpoint, WorkflowRun,
)

DATE_FIELDS = frozenset({
    "created_at", "updated_at", "closed_at", "merged_at", "pushed_at",
    "selected_at", "started_at", "completed_at", "last_success_at",
    "high_watermark", "coverage_start", "measured_at", "fetched_at",
    "finished_at", "generated_at",
})


def _parse(value):
    if isinstance(value, list):
        return [_parse(item) for item in value]
    if isinstance(value, dict):
        return {key: (
            datetime.fromisoformat(item.replace("Z", "+00:00"))
            if key in DATE_FIELDS and isinstance(item, str) else _parse(item)
        ) for key, item in value.items()}
    return value


def _model_data(model, row: dict) -> dict:
    columns = {col.key for col in model.__table__.columns}
    return {key: value for key, value in row.items() if key in columns}


def hydrate_snapshot(session: Session, path: Path) -> dict:
    """Restore only to an empty DB; repeated runs never duplicate source IDs."""
    if session.scalar(select(func.count()).select_from(Repository)):
        return {"restored": 0, "reason": "database already populated"}
    if not path.exists():
        return {"restored": 0, "reason": "snapshot not found"}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = _parse(json.load(f))
    if data.get("schema_version") != 1 or not isinstance(data.get("reports"), list):
        raise ValueError("Refusing invalid public snapshot")
    previous = data.get("selection")
    if not isinstance(previous, dict) or not previous.get("id"):
        raise ValueError("Snapshot has no auditable selection")

    try:
        run = SelectionRun(
            id=int(previous["id"]),
            started_at=data["generated_at"],
            completed_at=data["generated_at"],
            parameters=previous.get("parameters") or {},
            candidate_count=int(previous.get("candidates") or 0),
            accepted_count=int(previous.get("selected") or 0),
            status=previous.get("status") or "partial",
            notes=previous.get("notes"),
        )
        session.merge(run)
        session.flush()
        for decision in previous.get("decisions") or []:
            session.merge(Candidate(**_model_data(Candidate, decision)))
        session.flush()
        for report in data["reports"]:
            metadata = _model_data(Repository, report["repository"])
            # Only newest selection run is included in the bundled snapshot.
            metadata["selection_run_id"] = run.id
            session.merge(Repository(**metadata))
        session.flush()

        counts = {"issues": 0, "pull_requests": 0, "workflow_runs": 0}
        for report in data["reports"]:
            for key, model, counter in (
                ("issue_rows", Issue, "issues"),
                ("pr_rows", PullRequest, "pull_requests"),
                ("ci_rows", WorkflowRun, "workflow_runs"),
            ):
                for record in report.get(key) or []:
                    session.merge(model(**_model_data(model, record)))
                    counts[counter] += 1
            for cp in (report.get("coverage") or {}).values():
                if cp:
                    session.merge(SyncCheckpoint(**_model_data(SyncCheckpoint, cp)))
            for observed in report.get("observations") or []:
                session.merge(Observation(**_model_data(Observation, observed)))
        session.commit()
        return {"restored": len(data["reports"]), **counts}
    except Exception:
        session.rollback()
        raise
