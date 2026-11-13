"""Candidate pool proves real 28d sources; it must not replace the curated set."""
from datetime import timedelta
from dataclasses import replace
from types import SimpleNamespace

from scripts.audit_candidate_pool import (
    discover_candidates, probe_candidate, audit_candidates, SOURCES,
)
from .conftest import NOW
from .test_discovery import candidate
from src.collectors.client import PageResult


class SearchOnlyClient:
    max_requests = 220
    request_count = 0

    def get(self, path, params):
        assert path == "/search/repositories"
        self.request_count += 1
        language = params["q"].split("language:")[1].split()[0]
        found = [candidate(200 + self.request_count, language=language)]
        found[0]["created_at"] = (NOW - timedelta(days=120)).isoformat()
        found[0]["pushed_at"] = (NOW - timedelta(days=2)).isoformat()
        return {"items": found, "incomplete_results": False}, None


def test_candidate_discovery_excludes_current_cohort_and_diversifies(cfg):
    client = SearchOnlyClient()
    pool, warnings = discover_candidates(
        client, {201, 203}, cfg, now=NOW, max_candidates=12)
    assert all(item["id"] not in {201, 203} for item in pool)
    assert len({item["language"] for item in pool}) >= 3
    assert not warnings
    assert client.request_count == 8


def test_candidate_probe_requires_complete_28d_window_and_real_source_rows(cfg, monkeypatch):
    raw = candidate(999)
    raw["created_at"] = (NOW-timedelta(days=120)).isoformat()
    seen = []

    def complete(client, repo, source, cutoff, settings, now, **kwargs):
        seen.append(source)
        counts = {"issues": 5, "pull_requests": 8, "workflow_runs": 4}
        rows = [{"id": i} for i in range(counts[source])]
        return rows, PageResult(rows, 1, True, False, False), cutoff, 1, 1

    monkeypatch.setattr("scripts.audit_candidate_pool.fetch_source_adaptive", complete)
    client = SimpleNamespace(request_count=0, max_requests=220)
    data = probe_candidate(client, raw, cfg, now=NOW)
    assert data["verdict"] == "verified_candidate"
    assert seen == list(SOURCES)
    assert all(data["sources"][s]["status"] == "verified_28d" for s in SOURCES)


def test_short_fallback_never_verifies_or_probes_ci(cfg, monkeypatch):
    raw = candidate(999)
    called = []

    def partial(client, repo, source, cutoff, settings, now, **kwargs):
        called.append(source)
        return ([{"id": i} for i in range(15)],
                PageResult([], 6, True, False, False),
                cutoff + timedelta(days=21), 2, 6)

    monkeypatch.setattr("scripts.audit_candidate_pool.fetch_source_adaptive", partial)
    client = SimpleNamespace(request_count=0, max_requests=220)
    data = probe_candidate(client, raw, cfg, now=NOW)
    assert data["verdict"] == "not_verified"
    assert called == ["issues"]
    assert data["sources"]["issues"]["status"] == "partial_or_short_window"


def test_sparse_completed_source_is_not_promoted(cfg, monkeypatch):
    raw = candidate(999)
    def tiny(client, repo, source, cutoff, settings, now, **kwargs):
        return ([{"id": 1}], PageResult([], 1, True, False, False),
                cutoff, 1, 1)
    monkeypatch.setattr("scripts.audit_candidate_pool.fetch_source_adaptive", tiny)
    data = probe_candidate(
        SimpleNamespace(request_count=0, max_requests=220),
        raw, cfg, now=NOW)
    assert data["verdict"] == "not_verified"


def test_search_and_probes_do_not_mutate_75_repositories(cfg, monkeypatch):
    raw = candidate(888)
    raw["created_at"] = (NOW-timedelta(days=120)).isoformat()
    def discover(client, known, settings, **kwargs):
        return [raw], []
    monkeypatch.setattr("scripts.audit_candidate_pool.discover_candidates", discover)
    def complete(client, repo, source, cutoff, settings, now, **kwargs):
        return ([{"id": i} for i in range(5)],
                PageResult([], 1, True, False, False),
                cutoff, 1, 1)
    monkeypatch.setattr("scripts.audit_candidate_pool.fetch_source_adaptive", complete)
    client = SimpleNamespace(request_count=0, max_requests=220)
    data = audit_candidates(client, cfg, {101}, now=NOW, max_probes=1)
    assert data["probed"] == 1
    assert data["verified_candidates"] == 1
    assert data["known_repository_count"] == 1
    assert "not an approved" in data["notice"]


def test_daily_rotation_checks_different_real_candidates_without_promotion(cfg, monkeypatch):
    """All four groups can be audited without deleting the fixed cohort."""
    pool = []
    for i in range(10):
        raw = candidate(900 + i)
        raw["created_at"] = (NOW - timedelta(days=100)).isoformat()
        pool.append(raw)
    def discover(client, known, settings, **kwargs):
        return list(pool), []
    seen = []
    def checked(client, raw, settings, **kwargs):
        seen.append(raw["id"])
        return {
            "github_id": raw["id"], "full_name": raw["full_name"],
            "verdict": "not_verified", "sources": {},
        }
    monkeypatch.setattr("scripts.audit_candidate_pool.discover_candidates", discover)
    monkeypatch.setattr("scripts.audit_candidate_pool.probe_candidate", checked)
    client = SimpleNamespace(request_count=0, max_requests=220)
    results = [
        audit_candidates(client, cfg, {101}, now=NOW + timedelta(days=day),
                         max_candidates=10, max_probes=3)
        for day in range(4)
    ]
    assert [r["probed"] for r in results].count(0) == 0
    assert {r["rotation_cycle"] for r in results} == {0, 1, 2, 3}
    assert set(seen) == {r["id"] for r in pool}
    assert all(r["verified_candidates"] == 0 for r in results)
    assert all(r["known_repository_count"] == 1 for r in results)
    assert all("not an approved" in r["notice"] for r in results)


def test_six_hour_rotation_reaches_all_three_candidate_groups(cfg, monkeypatch):
    monkeypatch.setenv("CANDIDATE_ROTATION_HOURS", "6")
    pool = []
    for i in range(12):
        raw = candidate(1500 + i)
        raw["created_at"] = (NOW - timedelta(days=100)).isoformat()
        pool.append(raw)
    monkeypatch.setattr(
        "scripts.audit_candidate_pool.discover_candidates",
        lambda client, known, settings, **kwargs: (list(pool), []),
    )
    inspected = []
    def inspected_candidate(client, raw, settings, **kwargs):
        inspected.append(raw["id"])
        return {"github_id": raw["id"], "full_name": raw["full_name"],
                "verdict": "not_verified", "sources": {}}
    monkeypatch.setattr(
        "scripts.audit_candidate_pool.probe_candidate", inspected_candidate,
    )
    client = SimpleNamespace(request_count=0, max_requests=1000)
    audited = [
        audit_candidates(client, cfg, {111}, now=NOW + timedelta(hours=h),
                         max_candidates=12, max_probes=4)
        for h in (0, 6, 12)
    ]
    assert len({result["rotation_cycle"] for result in audited}) == 3
    assert set(inspected) == {raw["id"] for raw in pool}
    assert all(result["rotation_hours"] == 6 for result in audited)


def test_cheap_first_candidate_fails_without_costly_other_scans(cfg, monkeypatch):
    monkeypatch.setenv("CANDIDATE_CHEAPEST_FIRST", "1")
    raw = candidate(1999)
    called = []
    def no_ci(client, repo, source, cutoff, settings, now, **kwargs):
        called.append(source)
        return [], PageResult([], 1, True, False, False), cutoff, 1, 1
    monkeypatch.setattr("scripts.audit_candidate_pool.fetch_source_adaptive", no_ci)
    result = probe_candidate(
        SimpleNamespace(request_count=0, max_requests=220),
        raw, cfg, now=NOW)
    assert called == ["workflow_runs"]
    assert result["verdict"] == "not_verified"
    assert result["sources"]["workflow_runs"]["records"] == 0
