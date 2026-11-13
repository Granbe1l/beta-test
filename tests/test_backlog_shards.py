"""P0.2: prove large backlog is split using real GitHub Search semantics."""
from dataclasses import replace
from datetime import timedelta, datetime, timezone

from src.collectors.backlog_search import search_open_issues_by_created
from src.collectors.backlog import fetch_open_backlog, sync_open_backlog
from src.collectors.client import PageResult
from src.database.models import Issue, Repository, SyncCheckpoint
from .conftest import NOW, issue_payload


class DateShardClient:
    def __init__(self, rows, *, incomplete=False, cap=100):
        self.rows = rows
        self.max_requests = cap
        self.request_count = 0
        self.incomplete = incomplete
        self.queries = []

    def paginate(self, *args, **kwargs):
        self.request_count += 1
        return PageResult(self.rows[:2], 1, False, True, False)

    def get(self, path, params=None):
        assert path == "/search/issues"
        self.request_count += 1
        assert "is:issue is:open created:" in params["q"]
        start, end = params["q"].split("created:")[1].split("..")
        left = datetime.fromisoformat(start.replace("Z", "+00:00"))
        right = datetime.fromisoformat(end.replace("Z", "+00:00"))
        matching = [
            row for row in self.rows
            if left <= datetime.fromisoformat(
                row["created_at"].replace("Z", "+00:00")) <= right
            and row["state"] == "open" and "pull_request" not in row
        ]
        matching.sort(key=lambda row: row["created_at"])
        self.queries.append((left, right, len(matching)))
        per_page = params["per_page"]
        page = params["page"]
        return {
            "total_count": len(matching),
            "incomplete_results": self.incomplete,
            "items": matching[(page-1)*per_page:page*per_page],
        }, None


def make_rows():
    output = []
    for index, age in enumerate((390, 300, 200, 120, 40), start=1):
        row = issue_payload(index)
        row["created_at"] = (NOW-timedelta(days=age)).isoformat()
        output.append(row)
    return output


def test_created_sharding_exhausts_all_ranges_and_deduplicates(db, cfg):
    cfg = replace(cfg, per_page=2, max_pages=1)
    repo = db.get(Repository, 101)
    repo.created_at = NOW-timedelta(days=450)
    db.commit()
    client = DateShardClient(make_rows())
    rows, result = fetch_open_backlog(client, repo, cfg, now=NOW)
    assert result.complete
    assert [r["number"] for r in sorted(rows, key=lambda r:r["number"])] == list(range(1, 6))
    assert len(client.queries) > 1
    assert all(len({r["id"] for r in rows}) == 5 for _ in [None])
    saved = sync_open_backlog(db, DateShardClient(make_rows()), repo, cfg, now=NOW)
    assert saved["full_open_backlog_verified"]
    assert saved["records"] == 5


def test_sharded_full_inventory_drops_stale_old_rest_sample(db, cfg):
    cfg = replace(cfg, per_page=2, max_pages=1)
    repo = db.get(Repository, 101)
    repo.created_at = NOW-timedelta(days=450)
    db.commit()
    old = issue_payload(99)
    old["created_at"] = (NOW-timedelta(days=350)).isoformat()
    client = DateShardClient(make_rows())
    client.paginate = lambda *a, **k: PageResult([old], 1, False, True, False)
    rows, result = fetch_open_backlog(client, repo, cfg, now=NOW)
    assert result.complete
    assert 99 not in {r["number"] for r in rows}


def test_rate_capped_search_never_certifies_open_inventory(db, cfg):
    cfg = replace(cfg, per_page=2, max_pages=1)
    repo = db.get(Repository, 101)
    repo.created_at = NOW-timedelta(days=450)
    db.commit()
    client = DateShardClient(make_rows(), cap=3)
    rows, result = fetch_open_backlog(client, repo, cfg, now=NOW)
    assert not result.complete
    assert rows
    assert client.request_count <= client.max_requests


def test_incomplete_search_result_is_not_verified(db, cfg):
    cfg = replace(cfg, per_page=2, max_pages=1)
    repo = db.get(Repository, 101)
    repo.created_at = NOW-timedelta(days=450)
    db.commit()
    client = DateShardClient(make_rows(), incomplete=True)
    shard = search_open_issues_by_created(
        client, repo, cfg, now=NOW, max_calls=6)
    assert not shard.complete
    assert shard.cap_reached
    assert len(client.queries) <= 6


def test_partial_search_does_not_fabricate_closed_at(db, cfg):
    cfg = replace(cfg, per_page=2, max_pages=1)
    repo = db.get(Repository, 101)
    repo.created_at = NOW-timedelta(days=450)
    db.add(Issue(
        id=1099, repo_id=101, number=99,
        url="https://github.com/sample/project/issues/99",
        title="Unconfirmed older open Issue", state="open",
        created_at=NOW-timedelta(days=400),
        updated_at=NOW-timedelta(days=50), labels=[]))
    db.commit()
    result = sync_open_backlog(
        db, DateShardClient(make_rows(), cap=3), repo, cfg, now=NOW)
    assert result["status"] == "partial"
    existing = db.get(Issue, 1099)
    assert existing.state == "open"
    assert existing.closed_at is None
    assert db.get(SyncCheckpoint, (101, "open_backlog")).status == "partial"
