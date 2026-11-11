from datetime import datetime, timedelta, timezone
from src.discovery.selection import validate_candidate, deduplicate, diversified_sample, size_tier, select_repositories
from src.database.models import Candidate, SelectionRun, Repository
from sqlalchemy import select
from .conftest import NOW


def candidate(i, language="Python",stars=120):
    return {"id":i,"name":f"repo{i}","full_name":f"org/repo{i}","html_url":f"https://github.com/org/repo{i}","owner":{"login":"org"},"language":language,"stargazers_count":stars,"pushed_at":"2026-11-10T00:00:00Z","created_at":"2025-01-01T00:00:00Z","has_issues":True,"fork":False,"archived":False,"private":False,"default_branch":"main"}


def test_candidate_validation():
    r=candidate(1); assert validate_candidate(r,NOW) is None
    for flag,reason in [("fork","fork"),("archived","archived"),("private","private")]:
        copy=dict(r);copy[flag]=True;assert validate_candidate(copy,NOW)==reason
    r["stargazers_count"]=40; assert validate_candidate(r,NOW)=="below initial star filter"
    r=candidate(1);r["pushed_at"]="2026-01-01T00:00:00Z";assert "inactive" in validate_candidate(r,NOW)


def test_dedup_and_diversity():
    values=[candidate(1),candidate(1),candidate(2,"Rust"),candidate(3,"TypeScript",900),candidate(4,"Go",12000)]
    unique=deduplicate(values)
    assert len(unique)==4
    chosen=diversified_sample(unique,4)
    assert len(chosen)==4
    assert len({v["language"] for v in chosen})==4
    assert size_tier(candidate(1,stars=8000))=="large"


class SearchClient:
    def get(self,path,params):
        if path=="/search/repositories":
            if "Python" in params["q"]: return {"items":[candidate(1),candidate(2, "Go")]},None
            if "Rust" in params["q"]: return {"items":[candidate(3,"Rust")]},None
            return {"items":[]},None
        if path.endswith("/issues"):return [{"id":1,"number":2}],None
        if path.endswith("/pulls"):return [{"id":2,"number":1}],None
        raise ValueError(path)


def test_audited_selection(db,cfg):
    results=select_repositories(SearchClient(),db,cfg,now=NOW)
    assert results["candidates"]==3
    assert len(results["selected"])==3
    assert db.scalar(select(SelectionRun)).candidate_count==3
    assert len(db.scalars(select(Candidate)).all())==3
    assert db.scalar(select(Repository).where(Repository.id==1)).selected
