"""SQLAlchemy 2.x schema. Global GitHub IDs prevent duplicate source records."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # GitHub repository id
    full_name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    language: Mapped[str | None] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(90), default="Other")
    stars: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    default_branch: Mapped[str] = mapped_column(String(120), default="main")
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selection_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("selection_runs.id"))


class SelectionRun(Base):
    __tablename__ = "selection_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="running")
    notes: Mapped[str | None] = mapped_column(Text)


class Candidate(Base):
    __tablename__ = "selection_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    selection_run_id: Mapped[int] = mapped_column(ForeignKey("selection_runs.id"))
    repo_id: Mapped[int] = mapped_column(Integer)
    full_name: Mapped[str] = mapped_column(String(250))
    url: Mapped[str] = mapped_column(String(600))
    category: Mapped[str] = mapped_column(String(90))
    stars: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(String(300))
    __table_args__ = (UniqueConstraint("selection_run_id", "repo_id"),)


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # global GitHub issue id
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    labels: Mapped[list] = mapped_column(JSON, default=list)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("repo_id", "number"), Index("ix_issues_repo_updated", "repo_id", "updated_at"))


class PullRequest(Base):
    __tablename__ = "pull_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    draft: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    labels: Mapped[list] = mapped_column(JSON, default=list)
    review_comments: Mapped[int | None] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("repo_id", "number"), Index("ix_pr_repo_updated", "repo_id", "updated_at"))


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(600), nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(250), default="Unknown")
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    conclusion: Mapped[str | None] = mapped_column(String(40))
    branch: Mapped[str | None] = mapped_column(String(200))
    event: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (Index("ix_runs_repo_created", "repo_id", "created_at"),)


class SyncCheckpoint(Base):
    __tablename__ = "sync_checkpoints"
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id"), primary_key=True)
    source: Mapped[str] = mapped_column(String(25), primary_key=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    high_watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    coverage_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(25), default="unavailable")
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(400))
    # Verified CI creation-date buckets. Persisted in the compressed snapshot
    # so expensive weeks/days do not need to be rescanned every six hours.
    verified_days: Mapped[dict] = mapped_column(JSON, default=dict)



class SyncLog(Base):
    __tablename__ = "sync_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id"))
    source: Mapped[str] = mapped_column(String(25))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(25), default="running")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(400))


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id"))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    open_issues_observed: Mapped[int] = mapped_column(Integer)
    aged_issues_observed: Mapped[int] = mapped_column(Integer)
    open_prs_observed: Mapped[int] = mapped_column(Integer)
    __table_args__ = (Index("ix_observations_repo_time", "repo_id", "measured_at"),)
