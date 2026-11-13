"""Regression tests for source-grounded, irreversible 75->50 curation."""
from __future__ import annotations

from datetime import datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from scripts import curate_verified_50 as curator

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "data/curated_50_manifest.json"


def source_fixture():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    names = manifest["selected"]
    at = curator.dt(manifest["source_snapshot_generated_at"])
    extras_verified = [
        "Akascape/Rembg-Fuse",
        "LuoDi-Nate/financial-management",
        "OpenOLAT/OpenOLAT",
        "SysAdminDoc/HushFeed",
        "p-gueguen/Spatial_transcriptomics_tools",
        "rehmatworks/gplaydl",
    ]
    extras_unverified = [f"example-archive/sample-{i:02d}" for i in range(19)]
    all_names = sorted(names + extras_verified + extras_unverified)
    assert len(all_names) == 75
    reports = []
    for idx, name in enumerate(all_names, 1):
        eligible = name in names or name in extras_verified
        cps = {
            source: {
                "repo_id": idx,
                "source": source,
                "status": "complete" if eligible or source != "issues" else "partial",
                "coverage_start": (at - timedelta(days=29)).isoformat(),
                "last_success_at": (at - timedelta(minutes=20)).isoformat(),
            }
            for source in curator.SOURCES
        }
        reports.append({
            "repository": {
                "id": idx, "full_name": name,
                "owner": name.split("/")[0], "name": name.split("/")[1],
                "url": "https://github.com/" + name,
                "stars": 200 + idx, "category": "Systems & tooling",
                "selected": True, "selection_run_id": 5,
                "language": "Python" if idx % 2 else "Go",
            },
            "coverage": cps,
            "issue_rows": [{"id": idx * 10 + 1, "repo_id": idx}],
            "pr_rows": [
                {"id": idx * 10 + 2, "repo_id": idx},
                {"id": idx * 10 + 3, "repo_id": idx},
            ] if name in names else [],
            "ci_rows": [
                {"id": idx * 10 + 4, "repo_id": idx},
                {"id": idx * 10 + 5, "repo_id": idx},
            ] if name in names else [],
        })
    payload = {
        "schema_version": 1,
        "generated_at": at.isoformat(),
        "source": "Public GitHub REST API",
        "reports": reports,
        "selection": {"id": 5, "status": "complete", "selected": 75,
                      "parameters": {"method": "historical"}, "decisions": []},
    }
    manifest["source_snapshot_generated_at"] = payload["generated_at"]
    return payload, manifest


def test_manifest_is_pinned_50_unique_identities():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert len(curator.validate_manifest(manifest)) == 50
    assert manifest["source_verified_joint_28d"] == 56
    assert manifest["source_snapshot_sha256"] == (
        "01dc463d828406c802ec055cf374ff11be4b3e64a318c2a2cf18785fc2c02f7f"
    )


def test_transition_keeps_original_evidence_and_archives_every_exclusion():
    original, manifest = source_fixture()
    updated, archived, receipt = curator.transition(
        original, manifest,
        actual_snapshot_sha256=manifest["source_snapshot_sha256"],
        now=curator.dt(manifest["source_snapshot_generated_at"]),
    )
    assert len(updated["reports"]) == 50
    assert len(archived["removed_reports"]) == 25
    assert len(archived["original_selection"]["decisions"]) == 0
    assert {r["repository"]["id"] for r in updated["reports"]}.isdisjoint(
        {r["repository"]["id"] for r in archived["removed_reports"]}
    )
    assert len(updated["selection"]["decisions"]) == 75
    assert len([x for x in updated["selection"]["decisions"]
                if x["decision"] == "selected"]) == 50
    assert all(r["repository"]["selection_run_id"] == 6 for r in updated["reports"])
    for r in updated["reports"]:
        match = next(x for x in original["reports"] if x["repository"]["id"] == r["repository"]["id"])
        assert r["pr_rows"] == match["pr_rows"]
        assert r["ci_rows"] == match["ci_rows"]
    assert receipt["original_verified_28d"] == 56
    assert receipt["selected_verified_28d_at_audit"] == 50
    assert receipt["future_verified_is_dynamic"] is True


def test_transition_aborts_on_unverified_inclusion_or_changed_snapshot():
    original, manifest = source_fixture()
    with pytest.raises(ValueError, match="source snapshot changed"):
        curator.transition(original, manifest, actual_snapshot_sha256="bad")
    chosen = manifest["selected"][0]
    row = next(r for r in original["reports"] if r["repository"]["full_name"] == chosen)
    row["coverage"]["issues"]["status"] = "partial"
    with pytest.raises(ValueError, match="Original strict Verified count"):
        curator.transition(original, manifest,
                           actual_snapshot_sha256=manifest["source_snapshot_sha256"])


def test_source_archive_is_lossless_and_rerun_has_no_second_migration(
    tmp_path, monkeypatch
):
    original, manifest = source_fixture()
    snap = tmp_path / "current.json.gz"
    archived = tmp_path / "excluded.json.gz"
    receipt = tmp_path / "receipt.json"
    config = tmp_path / "manifest.json"
    raw = gzip.compress(json.dumps(original).encode("utf-8"))
    snap.write_bytes(raw)
    manifest["source_snapshot_sha256"] = hashlib.sha256(raw).hexdigest()
    config.write_text(json.dumps(manifest))
    monkeypatch.setattr(curator, "SNAPSHOT", snap)
    monkeypatch.setattr(curator, "ARCHIVE", archived)
    monkeypatch.setattr(curator, "RECEIPT", receipt)
    monkeypatch.setattr(curator, "MANIFEST", config)
    curator.main()
    with gzip.open(snap, "rt", encoding="utf-8") as source:
        selected = json.load(source)
    with gzip.open(archived, "rt", encoding="utf-8") as source:
        saved = json.load(source)
    assert len(selected["reports"]) == 50
    assert len(saved["removed_reports"]) == 25
    assert json.loads(receipt.read_text())["selected_count"] == 50
    expected_archive = archived.read_bytes()
    curator.main()
    assert archived.read_bytes() == expected_archive
