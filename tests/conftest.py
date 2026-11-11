from dataclasses import replace
from datetime import datetime, timezone
import pytest
from src.config.settings import Settings
from src.database.store import make_engine, init_db, session_factory
from src.database.models import Repository

NOW = datetime(2026, 11, 12, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def cfg(tmp_path):
    return replace(Settings.from_env(), database_url=f"sqlite:///{tmp_path/'app.sqlite3'}", max_pages=2, per_page=2, backfill_days=180, comparison_days=90)

@pytest.fixture
def db(cfg):
    engine=make_engine(cfg.database_url)
    init_db(engine)
    with session_factory(engine)() as session:
        session.add(Repository(id=101, full_name="sample/project", owner="sample",name="project",url="https://github.com/sample/project",language="Python",category="Data & backend",stars=123,selected=True))
        session.commit()
        yield session
    engine.dispose()


def issue_payload(n=1, state="open", is_pr=False, updated="2026-11-10T00:00:00Z"):
    raw={"id":1000+n,"number":n,"html_url":f"https://github.com/sample/project/issues/{n}","title":f"Issue {n}","state":state,"created_at":"2026-08-01T00:00:00Z","updated_at":updated,"closed_at":None,"labels":[{"name":"bug"}],"comments":0}
    if is_pr: raw["pull_request"]={"url":"https://api.github.com/repos/sample/project/pulls/2"}
    return raw


def pr_payload(n=1, merged=True, updated="2026-11-10T00:00:00Z"):
    return {"id":2000+n,"number":n,"html_url":f"https://github.com/sample/project/pull/{n}","title":f"PR {n}","state":"closed" if merged else "open","draft":False,"created_at":"2026-11-01T00:00:00Z","updated_at":updated,"closed_at":"2026-11-10T00:00:00Z" if merged else None,"merged_at":"2026-11-10T00:00:00Z" if merged else None,"labels":[]}


def run_payload(n=1):
    return {"id":3000+n,"html_url":f"https://github.com/sample/project/actions/runs/{3000+n}","name":"CI","status":"completed","conclusion":"success","head_branch":"main","event":"push","created_at":"2026-11-10T00:00:00Z","updated_at":"2026-11-10T00:10:00Z"}
