"""Scaling invariants for audited selection and incremental public snapshots."""
from dataclasses import replace
from pathlib import Path
from sqlalchemy import select, func
import gzip
import json
import pytest

from src.collectors.restore import hydrate_snapshot
from src.collectors.sync import synchronize
from src.collectors.client import GitHubClient, GitHubAPIError
from src.database.models import Repository, SelectionRun, Candidate, SyncCheckpoint, Issue
from src.database.store import make_engine, init_db, session_factory
from src.discovery.selection import expand_repositories
from .conftest import NOW
from .test_discovery import candidate


class SelectionClient:
    def get(self, path, params):
        if path == "/search/repositories":
            if "Python" in params["q"]:
                return {"items": [candidate(101),candidate(201),candidate(202)]}, None
            if "Rust" in params["q"]:
                return {"items": [candidate(203, "Rust")]}, None
            return {"items": []}, None
        if path.endswith("/issues"):
            return [{"number": 1}], None
        if path.endswith("/pulls"):
            return [{"number": 1}], None
        raise AssertionError(path)


def test_expansion_preserves_selected_repositories_and_hard_cap(db, cfg):
    cfg = replace(cfg, max_repos=3, max_candidates=15)
    result = expand_repositories(SelectionClient(), db, cfg, now=NOW)
    assert result["added"] == 2 and result["selected_total"] == 3
    assert db.get(Repository,101).full_name == "sample/project"
    assert db.scalar(select(func.count()).select_from(Repository).where(Repository.selected.is_(True))) == 3
    run = db.scalars(select(SelectionRun).order_by(SelectionRun.id.desc())).first()
    assert run.accepted_count == 3 and run.parameters["purpose"] == "expansion"
    decisions = list(db.scalars(select(Candidate).where(
        Candidate.selection_run_id == run.id, Candidate.decision == "selected")))
    assert len(decisions) == 3
    assert expand_repositories(SelectionClient(), db, cfg, now=NOW)["added"] == 0


class DummyPage:
    complete = True
    pages = 1
    items = []

class SourceClient:
    def paginate(self, *args, **kwargs): return DummyPage()


def test_initial_collection_batches_then_refreshes_full_selection(db, cfg):
    for id in (202,203,204,205):
        db.add(Repository(id=id,full_name=f"org/repo{id}",name=f"repo{id}",
            owner="org",url=f"https://github.com/org/repo{id}",language="Python",
            category="Data & backend",stars=100,selected=True))
    db.commit()
    assert len(synchronize(db, SourceClient(), cfg, initial_batch_size=2)) == 6
    assert db.get(SyncCheckpoint,(202,"issues")) is not None
    assert db.get(SyncCheckpoint,(204,"issues")) is None
    assert len(synchronize(db, SourceClient(), cfg, initial_batch_size=2)) == 6
    # The baseline repository in the fixture also lacks a checkpoint.
    assert len(synchronize(db, SourceClient(), cfg, initial_batch_size=2)) == 3
    assert len(synchronize(db, SourceClient(), cfg, initial_batch_size=2)) == 15


def test_restoring_public_snapshot_preserves_real_record_ids(tmp_path):
    snapshot = Path(__file__).resolve().parents[1] / "data/github_public_snapshot.json.gz"
    assert snapshot.exists()
    with gzip.open(snapshot, "rt", encoding="utf-8") as f:
        source = json.load(f)
    counts = {name:sum(len(r[key]) for r in source["reports"]) for name,key in
              (("issues","issue_rows"),("pull_requests","pr_rows"),("workflow_runs","ci_rows"))}
    engine = make_engine(f"sqlite:///{tmp_path / 'hydrate.db'}")
    init_db(engine)
    try:
        with session_factory(engine)() as session:
            summary = hydrate_snapshot(session, snapshot)
            assert summary["restored"] == len(source["reports"])
            for key in counts: assert summary[key] == counts[key]
            assert session.scalar(select(func.count()).select_from(SyncCheckpoint)) >= 3
            assert hydrate_snapshot(session,snapshot)["restored"] == 0
            assert session.scalar(select(func.count()).select_from(Issue)) == counts["issues"]
    finally:
        engine.dispose()


class RequestSession:
    def __init__(self):self.headers={};self.calls=0
    def get(self,*args,**kwargs):
        self.calls+=1
        class Response:
            status_code=200
            headers={}
            def json(self):return []
        return Response()


def test_hard_request_budget():
    raw = RequestSession()
    client = GitHubClient(session=raw, max_requests=2, sleeper=lambda _:None)
    client.get("/rate_limit")
    client.get("/rate_limit")
    with pytest.raises(GitHubAPIError, match="budget"):
        client.get("/rate_limit")
    assert raw.calls == 2 and client.request_count == 2
