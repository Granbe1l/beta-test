"""Materialize current persisted records as reports for display."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import select, func
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


def _rows_by_repo(session: Session, model, repo_ids: list[int]) -> dict[int, list[dict]]:
    """Fetch original records once per source, without ORM identity-map inflation.

    The rows are unchanged database values, ordered by GitHub's stable ID
    just as the existing SQLite primary-key scan would be. Selected repo
    batches are at most 500 IDs for SQLite's bind parameter budget.
    """
    output = defaultdict(list)
    for start in range(0, len(repo_ids), 500):
        group = repo_ids[start:start + 500]
        stmt = (select(model.__table__)
                .where(model.repo_id.in_(group))
                .order_by(model.repo_id, model.id))
        for row in session.execute(stmt).mappings():
            value = dict(row)
            output[value["repo_id"]].append(value)
    return output


def _observations_by_repo(session: Session, repo_ids: list[int]) -> dict[int, list[dict]]:
    """Retrieve only the 30 newest snapshots per repo, in one windowed query.

    Previous logic executed one ORDER BY ... LIMIT 30 query per repo.
    This portable SQLite/PostgreSQL window preserves the per-project cap.
    """
    output = defaultdict(list)
    for start in range(0, len(repo_ids), 500):
        group = repo_ids[start:start + 500]
        ranked = (select(
            Observation.id.label("observation_id"),
            func.row_number().over(
                partition_by=Observation.repo_id,
                order_by=(Observation.measured_at.desc(), Observation.id.desc()),
            ).label("row_number"),
        ).where(Observation.repo_id.in_(group)).subquery())
        stmt = (select(Observation.__table__)
                .join(ranked, Observation.id == ranked.c.observation_id)
                .where(ranked.c.row_number <= 30)
                .order_by(Observation.repo_id, Observation.measured_at.desc(),
                          Observation.id.desc()))
        for row in session.execute(stmt).mappings():
            value = dict(row)
            output[value["repo_id"]].append(value)
    return output


def load_reports(session: Session, now: datetime | None = None,
                 observation_days=90, stale_hours=12) -> list[dict]:
    """Use bounded batch queries instead of five per-repository SQL scans.

    Never change the coverage eligibility, zero/missing semantics, or
    existing deterministic Issue/PR/CI calculations.
    """
    now = utc(now or datetime.now(timezone.utc))
    repositories = list(session.scalars(
        select(Repository)
        .where(Repository.selected.is_(True))
        .order_by(Repository.full_name)))
    if not repositories:
        return []
    repo_ids = [repo.id for repo in repositories]
    checkpoints = defaultdict(dict)
    for start in range(0, len(repo_ids), 500):
        group = repo_ids[start:start + 500]
        for cp in session.scalars(select(SyncCheckpoint).where(
                SyncCheckpoint.repo_id.in_(group))):
            checkpoints[cp.repo_id][cp.source] = cp

    all_issues = _rows_by_repo(session, Issue, repo_ids)
    all_prs = _rows_by_repo(session, PullRequest, repo_ids)
    all_ci = _rows_by_repo(session, WorkflowRun, repo_ids)
    all_observations = _observations_by_repo(session, repo_ids)
    reports = []
    for repo in repositories:
        cps = checkpoints[repo.id]
        statuses = {s: available_source(cps.get(s), now, stale_hours) for s in (
            "issues", "pull_requests", "workflow_runs")}
        issues = all_issues[repo.id]
        prs = all_prs[repo.id]
        ci = all_ci[repo.id]
        observations = all_observations[repo.id]
        ic = cps.get("issues")
        pc = cps.get("pull_requests")
        cc = cps.get("workflow_runs")
        backlog_cp = cps.get("open_backlog")
        backlog_status = available_source(backlog_cp, now, stale_hours)
        i = calculate_issues(issues, now, observation_days,
                             statuses["issues"] == "complete",
                             ic.coverage_start if ic else None,
                             backlog_complete=backlog_status == "complete")
        p = calculate_prs(prs, now, observation_days,
                          statuses["pull_requests"] == "complete",
                          pc.coverage_start if pc else None)
        c = calculate_ci(ci, now, observation_days,
                         statuses["workflow_runs"] == "complete",
                         cc.coverage_start if cc else None)
        change = closure_change(issues, now, statuses["issues"] == "complete",
                                ic.coverage_start if ic else None)
        reports.append({
            "repository": source_row(repo), "issues": i, "prs": p,
            "ci": c, "closure": change, "issue_rows": issues, "pr_rows": prs,
            "ci_rows": ci, "observations": observations,
            "open_backlog_status": backlog_status, "status": statuses,
            "coverage_ok": all(v == "complete" for v in statuses.values()),
            "last_success": (
                min(utc(cps[s].last_success_at) for s in statuses)
                if all(cps.get(s) and cps[s].last_success_at for s in statuses)
                else None
            ),
            "coverage": {
                **{s: source_row(cp) if (cp := cps.get(s)) else None
                   for s in statuses},
                "open_backlog": source_row(backlog_cp) if backlog_cp else None,
            },
        })
    return reports


def selection_info(session):
    run = session.scalars(select(SelectionRun).order_by(SelectionRun.id.desc())).first()
    if not run: return None
    return {"id": run.id, "parameters": run.parameters, "candidates": run.candidate_count,
            "selected": run.accepted_count, "status": run.status, "notes": run.notes,
            "decisions": [source_row(x) for x in session.scalars(select(Candidate).where(Candidate.selection_run_id == run.id))]}
