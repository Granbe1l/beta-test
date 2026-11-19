from datetime import timedelta
import pytest
from sqlalchemy import select, func
from src.collectors.sync import sync_one, fetch_source, start_window, record_observations, refresh_repo_metadata
from src.collectors.normalize import issue, pull_request, workflow_run
from src.database.models import Repository, Issue, PullRequest, WorkflowRun, SyncCheckpoint, SyncLog
from .conftest import NOW,issue_payload,pr_payload,run_payload


class FakePagination:
    def __init__(self,records,complete=True):
        self.items=records;self.pages=1;self.complete=complete

class ScriptedClient:
    def __init__(self,payload,complete=True,exc=None):self.payload=payload;self.complete=complete;self.exc=exc
    def paginate(self,path,params,max_pages,**kwargs):
        if self.exc:raise self.exc
        if "/issues" in path:return FakePagination(self.payload["issues"],self.complete)
        if "/pulls" in path:return FakePagination(self.payload["pull_requests"],self.complete)
        return FakePagination(self.payload["workflow_runs"],self.complete)


def test_issue_pr_separation():
    assert issue(issue_payload(1,is_pr=True),101) is None
    assert issue(issue_payload(1),101)["repo_id"]==101
    assert pull_request(pr_payload(1),101)["merged_at"] is not None
    assert workflow_run(run_payload(1),101)["id"]==3001


def test_sync_complete_and_idempotent(db,cfg):
    repo=db.get(Repository,101)
    client=ScriptedClient({"issues":[issue_payload(1),issue_payload(2,is_pr=True)],"pull_requests":[pr_payload(2)],"workflow_runs":[run_payload(1)]})
    for _ in range(2):
        for source in ("issues","pull_requests","workflow_runs"):
            r=sync_one(db,client,repo,source,cfg,now=NOW)
            assert r["status"]=="complete"
    assert db.scalar(select(func.count()).select_from(Issue))==1
    assert db.scalar(select(func.count()).select_from(PullRequest))==1
    assert db.scalar(select(func.count()).select_from(WorkflowRun))==1
    assert record_observations(db,101,now=NOW)


def test_incremental_overlap(db,cfg):
    repo=db.get(Repository,101)
    c=ScriptedClient({"issues":[issue_payload(1)],"pull_requests":[],"workflow_runs":[]})
    sync_one(db,c,repo,"issues",cfg,now=NOW)
    cp=db.get(SyncCheckpoint,(101,"issues"))
    assert start_window(cp,cfg,NOW+timedelta(hours=6),False)==NOW-timedelta(hours=cfg.overlap_hours)
    assert start_window(cp,cfg,NOW+timedelta(hours=6),True)==NOW+timedelta(hours=6)-timedelta(days=cfg.backfill_days)


def test_partial_never_advances_success(db,cfg):
    repo=db.get(Repository,101)
    c=ScriptedClient({"issues":[issue_payload(1)],"pull_requests":[],"workflow_runs":[]},complete=False)
    result=sync_one(db,c,repo,"issues",cfg,now=NOW)
    cp=db.get(SyncCheckpoint,(101,"issues"))
    assert result["status"]=="partial" and cp.last_success_at is None
    assert db.scalar(select(func.count()).select_from(Issue))==1


def test_failure_preserves_old_records_and_checkpoint(db,cfg):
    repo=db.get(Repository,101)
    good=ScriptedClient({"issues":[issue_payload(1)],"pull_requests":[],"workflow_runs":[]})
    sync_one(db,good,repo,"issues",cfg,now=NOW)
    before=db.get(SyncCheckpoint,(101,"issues")).last_success_at
    bad=ScriptedClient(None,exc=RuntimeError("secret=private-token"))
    result=sync_one(db,bad,repo,"issues",cfg,now=NOW+timedelta(hours=6))
    cp=db.get(SyncCheckpoint,(101,"issues"))
    assert result["status"]=="failed" and cp.last_success_at==before
    assert "private-token" not in cp.last_error
    assert db.scalar(select(func.count()).select_from(Issue))==1



def test_repo_last_push_metadata_refresh_uses_real_github_id(db):
    class RepoClient:
        def get(self, path):
            assert path == "/repos/sample/project"
            return {
                "id": 101, "private": False,
                "pushed_at": "2026-11-12T10:00:00Z",
                "stargazers_count": 238,
                "language": "Go",
                "archived": False,
            }, None
    repository = db.get(Repository, 101)
    assert refresh_repo_metadata(db, RepoClient(), repository)
    assert repository.pushed_at.year == 2026
    assert repository.pushed_at.day == 12
    assert repository.stars == 238
    assert repository.category == "Cloud & infrastructure"


def test_metadata_failure_preserves_existing_push_date(db):
    repo = db.get(Repository, 101)
    repo.pushed_at = NOW - timedelta(days=3)
    db.commit()

    class WrongRepo:
        def get(self, path):
            return {"id": 999, "pushed_at": "2026-11-12T10:00:00Z"}, None

    from src.collectors.sync import RepositoryIdentityMismatch
    with pytest.raises(RepositoryIdentityMismatch):
        refresh_repo_metadata(db, WrongRepo(), repo)
    assert db.get(Repository, 101).pushed_at.date() == (NOW - timedelta(days=3)).date()


def test_identity_mismatch_blocks_all_sources_and_open_inventory(db, cfg):
    from src.collectors.sync import synchronize
    from src.database.models import Observation
    class ReusedSlug:
        def get(self, path, params=None):
            return {"id": 999, "full_name": "sample/project"}, None
        def paginate(self, *args, **kwargs):
            pytest.fail("Identity mismatch must stop all source/inventory requests")
    result = synchronize(db, ReusedSlug(), cfg, run_at=NOW, audit_open_backlog=True)
    assert result and all(r["status"] == "failed" for r in result)
    assert db.scalar(select(func.count()).select_from(Issue)) == 0
    assert db.scalar(select(func.count()).select_from(Observation)) == 0


def test_backlog_only_repository_cannot_bypass_identity_check(db, cfg, monkeypatch):
    from src.collectors.sync import synchronize
    db.add(Repository(id=102, full_name="zzz/reused", owner="zzz", name="reused",
                      url="https://github.com/zzz/reused", selected=True))
    db.commit()
    class Client(ScriptedClient):
        def get(self, path, params=None):
            return {"id": 999 if "zzz/reused" in path else 101, "private": False}, None
    attempts = []
    def backlog(session, client, repo, settings, **kwargs):
        attempts.append(repo.id)
        return {"status": "complete"}
    monkeypatch.setattr("src.collectors.backlog.sync_open_backlog", backlog)
    synchronize(db, Client({"issues": [], "pull_requests": [], "workflow_runs": []}),
                cfg, initial_batch_size=1, run_at=NOW, audit_open_backlog=True)
    assert 102 not in attempts
    assert db.get(SyncCheckpoint, (102, "open_backlog")).status == "failed"


def test_identity_quarantine_survives_transient_metadata_error(db, cfg):
    from src.collectors.sync import synchronize
    cp = SyncCheckpoint(repo_id=101, source="open_backlog", status="failed",
                        last_error="RepositoryIdentityMismatch: GitHub repository ID mismatch")
    db.add(cp); db.commit()
    class Client:
        def get(self, *args, **kwargs):
            raise RuntimeError("temporary metadata outage")
        def paginate(self, *args, **kwargs):
            pytest.fail("Previously mismatched identity needs positive revalidation")
    result = synchronize(db, Client(), cfg, run_at=NOW, audit_open_backlog=True)
    assert result and all(r["status"] == "failed" for r in result)
