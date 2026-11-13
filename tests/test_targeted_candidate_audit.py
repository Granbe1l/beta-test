from datetime import timedelta
from types import SimpleNamespace

from scripts.audit_targeted_candidates import TARGETS, audit_targets
from .conftest import NOW
from .test_discovery import candidate


def test_targets_explicit_and_unique():
    assert len(TARGETS) == 11
    assert len(set(TARGETS)) == 9


def test_target_audit_uses_real_metadata_and_source_probe(cfg, monkeypatch):
    raw = candidate(14567, language="Python")
    raw["full_name"] = "acme/project"
    raw["created_at"] = (NOW - timedelta(days=120)).isoformat()
    raw["pushed_at"] = (NOW - timedelta(days=2)).isoformat()
    seen = []
    class Client:
        request_count = 1
        def get(self, path):
            assert path == "/repos/acme/project"
            return raw, None
    def verified(client, actual, settings, **kwargs):
        seen.append(actual["id"])
        return {"full_name": "acme/project",
                "verdict": "verified_candidate", "sources": {}}
    monkeypatch.setattr("scripts.audit_targeted_candidates.probe_candidate", verified)
    report = audit_targets(Client(), cfg, now=NOW, target_names=("acme/project",))
    assert seen == [14567]
    assert report["verified_candidates"] == 1
    assert report["results"][0]["verdict"] == "verified_candidate"


def test_metadata_ineligible_target_is_not_probed(cfg, monkeypatch):
    raw = candidate(14568, language="Python")
    raw["full_name"] = "acme/project"
    raw["created_at"] = (NOW - timedelta(days=120)).isoformat()
    raw["pushed_at"] = (NOW - timedelta(days=2)).isoformat()
    raw["fork"] = True
    class Client:
        request_count = 1
        def get(self, path):
            return raw, None
    def no_probe(*args, **kwargs):
        raise AssertionError("Ineligible candidate should never be probed")
    monkeypatch.setattr("scripts.audit_targeted_candidates.probe_candidate", no_probe)
    report = audit_targets(Client(), cfg, now=NOW, target_names=("acme/project",))
    assert report["verified_candidates"] == 0
    assert report["results"][0]["reason"] == "current_metadata_or_eligibility"
