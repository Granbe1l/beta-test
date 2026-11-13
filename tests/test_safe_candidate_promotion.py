from datetime import datetime, timedelta, timezone
import gzip
import json

import pytest

from scripts import promote_verified_candidates as promotion

NOW = datetime(2026, 11, 13, 18, 7, tzinfo=timezone.utc)


def _audit(when=NOW, *, bad_source=None):
    return {
        "generated_at_utc": when.isoformat(),
        "results": [{
            "github_id": 123,
            "full_name": "acme/real",
            "verdict": "verified_candidate",
            "sources": {
                source: {
                    "status": ("partial_or_short_window"
                               if bad_source == source else "verified_28d"),
                    "records": 5,
                    "source_start_utc": (when - timedelta(days=28)).isoformat(),
                }
                for source in promotion.SOURCES
            },
        }],
    }


def _swap():
    return {"candidate_name": "acme/real", "candidate_github_id": 123}


def test_proof_requires_all_three_complete_28d_sources():
    assert promotion.candidate_has_verified_proof(_swap(), _audit(), NOW)
    for source in promotion.SOURCES:
        assert not promotion.candidate_has_verified_proof(
            _swap(), _audit(bad_source=source), NOW)
    assert not promotion.candidate_has_verified_proof(
        _swap(), _audit(when=NOW - timedelta(hours=13)), NOW)


def test_proof_rejects_short_fallback_and_missing_real_rows():
    a = _audit()
    a["results"][0]["sources"]["issues"]["source_start_utc"] = (
        NOW - timedelta(days=7)).isoformat()
    assert not promotion.candidate_has_verified_proof(_swap(), a, NOW)
    a = _audit()
    a["results"][0]["sources"]["pull_requests"]["records"] = 0
    assert not promotion.candidate_has_verified_proof(_swap(), a, NOW)


def test_archival_preserves_original_rows_and_refuses_duplicate(tmp_path, monkeypatch):
    snapshot = tmp_path / "source.json.gz"
    archive = tmp_path / "archive.json.gz"
    monkeypatch.setattr(promotion, "SNAPSHOT_PATH", snapshot)
    monkeypatch.setattr(promotion, "ARCHIVE", archive)
    payload = {
        "generated_at": NOW.isoformat(),
        "reports": [{
            "repository": {"id": 111, "full_name": "old/repo"},
            "issue_rows": [{"id": 901, "title": "Original issue"}],
            "pr_rows": [{"id": 902}],
            "ci_rows": [{"id": 903}],
        }],
    }
    with gzip.open(snapshot, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)
    changes = [{"old_id": 111, "new_id": 123}]
    promotion.archive_originals(changes, NOW)
    with gzip.open(archive, "rt", encoding="utf-8") as fh:
        historical = json.load(fh)
    assert historical["archived"][0]["full_original_report"] == payload["reports"][0]
    with pytest.raises(ValueError):
        promotion.archive_originals(changes, NOW)
