"""Database session and idempotent source-level upserts."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import re
from sqlalchemy import create_engine, select, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from .models import Base, Issue, PullRequest, WorkflowRun, Repository, SyncCheckpoint, SyncLog, utcnow

ENTITY_MAP = {"issues": Issue, "pull_requests": PullRequest, "workflow_runs": WorkflowRun}


def make_engine(url: str):
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False, "timeout": 30}
    return create_engine(url, **options)


def init_db(engine):
    Base.metadata.create_all(engine)
    # Existing optional persistent SQL/PG deployments need a small additive
    # migration; create_all never alters existing tables. Fresh Actions
    # SQLite databases already have the column from Base.metadata.
    with engine.begin() as conn:
        columns = {c["name"] for c in inspect(conn).get_columns("sync_checkpoints")}
        if "verified_days" not in columns:
            conn.execute(text(
                "ALTER TABLE sync_checkpoints ADD COLUMN verified_days JSON"
            ))
        observation_columns = {c["name"] for c in inspect(conn).get_columns("observations")}
        if "collection_basis" not in observation_columns:
            conn.execute(text(
                "ALTER TABLE observations ADD COLUMN collection_basis "
                "VARCHAR(40) NOT NULL DEFAULT 'legacy_observed'"
            ))


def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)


def upsert(session: Session, model, row: dict) -> None:
    # merge performs an INSERT or UPDATE keyed on the global GitHub primary key.
    session.merge(model(**row))


def upsert_repository(session: Session, values: dict) -> None:
    upsert(session, Repository, values)


def write_records(session: Session, source: str, rows: list[dict]) -> None:
    for row in rows:
        upsert(session, ENTITY_MAP[source], row)
    session.flush()


def get_checkpoint(session: Session, repo_id: int, source: str) -> SyncCheckpoint:
    cp = session.get(SyncCheckpoint, (repo_id, source))
    if cp is None:
        cp = SyncCheckpoint(repo_id=repo_id, source=source, status="unavailable")
        session.add(cp)
        session.flush()
    return cp


def safe_error(exc: Exception) -> str:
    # Suppress credentials even when a request error contains a URL or headers.
    msg = str(exc)
    msg = re.sub(r"(?i)(token|password|authorization|secret|apikey|api_key)\s*[:=]\s*[^\s&]+", r"\1=[REDACTED]", msg)
    msg = re.sub(r"(?i)(ghp_|gho_|github_pat_)[a-z0-9_]+", "[REDACTED]", msg)
    return msg[:350]
