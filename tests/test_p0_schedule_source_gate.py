"""The operational P0 gate must not accept three green runs without source proof."""
from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from scripts.schedule_source_gate import (read_receipt, validate_source_receipt,
                                          evaluate_gate, fetch_run_receipt, selected_cohort)


def fixtures(n=50):
    sources = ("issues", "pull_requests", "workflow_runs")
    at = "2026-11-14T12:00:00+00:00"
    fresh = "2026-11-14T11:55:00+00:00"
    window = "2026-10-16T12:00:00+00:00"  # Older than 28 days.
    rows = [
        {
            "name": f"owner/repo-{i}",
            "status": {s: "complete" for s in sources},
            "open_backlog_status": "complete",
            "source_details": {
                **{s: {"status": "complete", "coverage_start": window,
                       "last_success_at": fresh} for s in sources},
                "open_backlog": {"status": "complete", "last_success_at": fresh},
            },
        }
        for i in range(n)
    ]
    return {
        "snapshot-audit.json": {
            "repositories": rows,
            "coverage_summary": {
                **{s: {"total_repositories": n, "complete": n,
                      "verified_28d": n, "partial": 0, "stale": 0,
                      "failed": 0, "unavailable": 0} for s in sources},
                "open_backlog": {"complete": n, "total_repositories": n},
            },
        },
        "coverage-readiness.json": {
            "as_of_utc": at, "tracked": n, "verified_joint_28d": n,
            "not_joint_verified": 0, "window_days": 28,
            "stale_hours": 12, "source_verified_28d": {s: n for s in sources},
            "per_repository": [
                {"repository": row["name"], "verified_joint_28d": True,
                 "unverified_sources": []} for row in rows
            ],
        },
        "open-inventory-triage.json": {
            "total_selected_repositories": n, "fresh_full_open_inventories": n,
            "all_full_open_inventories_current": True, "gaps": [],
        },
    }


def archive(payload):
    buf = BytesIO()
    with ZipFile(buf, "w") as zipfile:
        for name, data in payload.items():
            zipfile.writestr(name, json.dumps(data))
    return buf.getvalue()


def test_valid_real_shape_and_missing_receipt_fail_closed():
    fields = fixtures()
    assert validate_source_receipt(read_receipt(archive(fields)))["joint_verified_28d"] == 50
    with pytest.raises(ValueError, match="missing_or_ambiguous"):
        read_receipt(archive({"snapshot-audit.json": fields["snapshot-audit.json"]}))


@pytest.mark.parametrize("part,change", [
    ("coverage-readiness.json", ("verified_joint_28d", 49)),
    ("coverage-readiness.json", ("stale_hours", 24)),
    ("open-inventory-triage.json", ("fresh_full_open_inventories", 49)),
    ("open-inventory-triage.json", ("gaps", [{"repository": "x"}])),
])
def test_partial_data_or_weakened_freshness_is_not_verified(part, change):
    fields = fixtures()
    fields[part][change[0]] = change[1]
    with pytest.raises(ValueError):
        validate_source_receipt(fields)


def test_repository_source_status_and_duplicate_ids_never_pass():
    x = fixtures()
    x["snapshot-audit.json"]["repositories"][0]["status"]["issues"] = "stale"
    with pytest.raises(ValueError, match="repository_source_not_complete"):
        validate_source_receipt(x)
    x = fixtures()
    x["snapshot-audit.json"]["repositories"][1]["name"] = "owner/repo-0"
    with pytest.raises(ValueError, match="identity"):
        validate_source_receipt(x)


def test_green_schedule_without_three_individual_artifacts_is_blocked():
    schedule = {"status": "verified_recent_cycles", "run_ids": [101, 102, 103]}
    two = [{"run_id": 101, "status": "verified"},
           {"run_id": 102, "status": "verified"}]
    assert evaluate_gate(schedule, two)["status"] == "blocked_source_evidence"
    assert evaluate_gate(schedule, two + [{"run_id": 103, "status": "unverified"}])[
        "status"] == "blocked_source_evidence"
    assert evaluate_gate(schedule, two + [{"run_id": 103, "status": "verified"}])[
        "status"] == "verified_operational_cycles"
    assert evaluate_gate({"status": "stale_schedule", "run_ids": [101, 102, 103]},
                         two + [{"run_id": 103, "status": "verified"}])["status"] == "blocked_schedule"


def test_manual_or_push_run_does_not_supply_a_third_real_schedule_id():
    schedule = {"status": "verified_recent_cycles", "run_ids": [101, 102]}
    receipts = [{"run_id": i, "status": "verified"} for i in (101, 102, 103)]
    assert evaluate_gate(schedule, receipts)["status"] == "blocked_source_evidence"


def test_fetch_is_scoped_to_actual_run_id_not_arbitrary_artifact():
    zipped = archive(fixtures())
    class Response:
        def __init__(self, json_data=None, data=b""):
            self.value, self.data = json_data, data
        def raise_for_status(self): pass
        def json(self): return self.value
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, chunk_size):
            yield self.data
    class Session:
        def __init__(self): self.calls = []
        def get(self, url, **kw):
            self.calls.append((url, kw))
            if url.endswith("/artifacts"):
                return Response({"artifacts": [{
                    "name": "github-50-repo-source-audit", "expired": False,
                    "size_in_bytes": len(zipped), "id": 505,
                }]})
            if url.endswith("/505/zip"):
                return Response(data=zipped)
            raise AssertionError(url)
    session = Session()
    result = fetch_run_receipt(
        session, api_base="https://api.github.com/repos/test/r",
        run_id=100, headers={"Authorization": "Bearer omitted"})
    assert result["full_open_inventories"] == 50
    assert "/actions/runs/100/artifacts" in session.calls[0][0]


def test_manifest_must_match_selected_fixed_50_even_if_summary_says_50():
    fields = fixtures()
    names = {r["name"] for r in fields["snapshot-audit.json"]["repositories"]}
    assert validate_source_receipt(fields, expected_names=names)["tracked"] == 50
    # A new repo is not allowed to silently replace a curated repo.
    fields["snapshot-audit.json"]["repositories"][0]["name"] = "unaudited/new-repo"
    with pytest.raises(ValueError, match="cohort_does_not_match_manifest"):
        validate_source_receipt(fields, expected_names=names)


def test_selected_manifest_rejects_missing_or_duplicate_members(tmp_path):
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps({"target_repositories": 50,
                                "selected": ["same/repo"] * 50}))
    with pytest.raises(ValueError, match="manifest_invalid"):
        selected_cohort(file)


def test_per_repository_readiness_must_not_disagree_with_green_summary():
    fields = fixtures()
    fields["coverage-readiness.json"]["per_repository"][3][
        "verified_joint_28d"] = False
    with pytest.raises(ValueError, match="per_repository_readiness"):
        validate_source_receipt(fields)


def test_source_checkpoint_must_cover_full_28_days_with_fresh_success():
    fields = fixtures()
    fields["snapshot-audit.json"]["repositories"][0]["source_details"][
        "issues"]["coverage_start"] = "2026-11-13T00:00:00+00:00"
    with pytest.raises(ValueError, match="window_short"):
        validate_source_receipt(fields)
    fields = fixtures()
    fields["snapshot-audit.json"]["repositories"][0]["source_details"][
        "pull_requests"]["last_success_at"] = "2026-11-13T00:00:00+00:00"
    with pytest.raises(ValueError, match="checkpoint_not_fresh"):
        validate_source_receipt(fields)


def test_open_inventory_must_be_fresh_even_when_status_claims_complete():
    fields = fixtures()
    fields["snapshot-audit.json"]["repositories"][0]["source_details"][
        "open_backlog"]["last_success_at"] = "2026-11-13T00:00:00+00:00"
    with pytest.raises(ValueError, match="checkpoint_not_fresh"):
        validate_source_receipt(fields)


def test_missing_checkpoint_timestamp_cannot_be_certified():
    fields = fixtures()
    fields["snapshot-audit.json"]["repositories"][2]["source_details"][
        "workflow_runs"].pop("last_success_at")
    with pytest.raises(ValueError, match="checkpoint_not_verified"):
        validate_source_receipt(fields)
