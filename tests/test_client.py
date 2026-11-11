import requests
import pytest
from src.collectors.client import GitHubClient, GitHubAPIError
from .conftest import NOW


class FakeResponse:
    def __init__(self,status=200,data=None,links=None,headers=None):
        self.status_code=status;self._data=data or [];self.links=links or {};self.headers=headers or {}
    def json(self):return self._data

class FakeSession:
    def __init__(self,responses):self.responses=iter(responses);self.headers={};self.calls=[]
    def get(self,url,params,timeout):
        self.calls.append((url,params));return next(self.responses)


def test_pagination_all_pages():
    sess=FakeSession([FakeResponse(data=[{"id":1},{"id":2}],links={"next":{}}),FakeResponse(data=[{"id":3}])])
    cli=GitHubClient(session=sess,sleeper=lambda _:None)
    r=cli.paginate("/repos/org/repo/pulls",{"per_page":2},max_pages=3)
    assert r.complete and not r.cap_reached and r.pages==2 and len(r.items)==3


def test_pagination_partial():
    sess=FakeSession([FakeResponse(data=[{"id":1},{"id":2}],links={"next":{}})])
    r=GitHubClient(session=sess,sleeper=lambda _:None).paginate("/repos/org/repo/pulls",{"per_page":2},1)
    assert r.cap_reached and not r.complete


def test_sorted_cutoff():
    items=[{"updated_at":"2026-11-10T00:00:00Z"},{"updated_at":"2026-01-01T00:00:00Z"}]
    r=GitHubClient(session=FakeSession([FakeResponse(data=items,links={"next":{}})]),sleeper=lambda _:None).paginate("/repos/org/repo/issues",{"per_page":2},1,cutoff=NOW.replace(month=10))
    assert r.complete and len(r.items)==1


def test_retry_rate_limit_and_timeout():
    waits=[]
    s=FakeSession([FakeResponse(status=429,headers={"Retry-After":"1"}),FakeResponse(status=200,data={"ok":True})])
    cli=GitHubClient(session=s,sleeper=waits.append)
    data,_=cli.get("/rate_limit")
    assert data["ok"] and len(waits)==1


def test_hard_http_failure_and_url_restriction():
    cli=GitHubClient(session=FakeSession([FakeResponse(status=404)]),sleeper=lambda _:None)
    with pytest.raises(GitHubAPIError):cli.get("/repo/missing")
    with pytest.raises(ValueError):cli.get("https://evil.example/steal")
