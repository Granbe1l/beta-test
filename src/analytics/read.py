"""Materialize current persisted records as reports for display."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.models import Repository, Issue, PullRequest, WorkflowRun, SyncCheckpoint, SelectionRun, Candidate, Observation
from src.analytics.metrics import calculate_issues, calculate_prs, calculate_ci, closure_change, utc


def source_row(x):
    return {c.name: getattr(x, c.name) for c in x.__table__.columns}


def available_source(cp, now, stale_hours):
    if cp is None: return "unavailable"
    if cp.status != "complete": return cp.status
    from datetime import timedelta
    if not cp.last_success_at or utc(cp.last_success_at) < now - timedelta(hours=stale_hours):
        return "stale"
    return "complete"


def load_reports(session: Session, now: datetime | None = None, observation_days=90, stale_hours=12) -> list[dict]:
    now = utc(now or datetime.now(timezone.utc))
    reports = []
    for repo in session.scalars(select(Repository).where(Repository.selected.is_(True)).order_by(Repository.full_name)):
        cps = {v.source: v for v in session.scalars(select(SyncCheckpoint).where(SyncCheckpoint.repo_id == repo.id))}
        statuses = {s: available_source(cps.get(s), now, stale_hours) for s in ("issues", "pull_requests", "workflow_runs")}
        issues = [source_row(v) for v in session.scalars(select(Issue).where(Issue.repo_id == repo.id))]
        prs = [source_row(v) for v in session.scalars(select(PullRequest).where(PullRequest.repo_id == repo.id))]
        ci = [source_row(v) for v in session.scalars(select(WorkflowRun).where(WorkflowRun.repo_id == repo.id))]
        observations = [source_row(v) for v in session.scalars(select(Observation).where(Observation.repo_id == repo.id).order_by(Observation.measured_at.desc()).limit(30))]
        ic = cps.get("issues")
        pc = cps.get("pull_requests")
        cc = cps.get("workflow_runs")
        i = calculate_issues(issues, now, observation_days, statuses["issues"] == "complete", ic.coverage_start if ic else None)
        p = calculate_prs(prs, now, observation_days, statuses["pull_requests"] == "complete", pc.coverage_start if pc else None)
        c = calculate_ci(ci, now, observation_days, statuses["workflow_runs"] == "complete", cc.coverage_start if cc else None)
        change = closure_change(issues, now, statuses["issues"] == "complete", ic.coverage_start if ic else None)
        reports.append({"repository": source_row(repo), "issues": i, "prs": p, "ci": c,
                        "closure": change, "issue_rows": issues, "pr_rows": prs, "ci_rows": ci, "observations": observations,
                        "status": statuses, "coverage_ok": all(v == "complete" for v in statuses.values()),
                        "last_success": (min(utc(cps[s].last_success_at) for s in statuses)
                                         if all(cps.get(s) and cps[s].last_success_at for s in statuses) else None),
                        "coverage": {s: source_row(cp) if (cp := cps.get(s)) else None for s in statuses}})
    return reports


def selection_info(session):
    run = session.scalars(select(SelectionRun).order_by(SelectionRun.id.desc())).first()
    if not run: return None
    return {"id": run.id, "parameters": run.parameters, "candidates": run.candidate_count,
            "selected": run.accepted_count, "status": run.status, "notes": run.notes,
            "decisions": [source_row(x) for x in session.scalars(select(Candidate).where(Candidate.selection_run_id == run.id))]}
