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
