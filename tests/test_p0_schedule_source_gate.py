"""The operational P0 gate must not accept three green runs without source proof."""
from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from scripts.schedule_source_gate import (read_receipt, validate_source_receipt,
                                          evaluate_gate, fetch_run_receipt)


def fixtures(n=50):
    sources = ("issues", "pull_requests", "workflow_runs")
    return {
        "snapshot-audit.json": {
            "repositories": [
                {"name": f"owner/repo-{i}", "status": {s: "complete" for s in sources},
                 "open_backlog_status": "complete"} for i in range(n)
            ],
            "coverage_summary": {
                **{s: {"total_repositories": n, "complete": n,
                      "verified_28d": n, "partial": 0, "stale": 0,
                      "failed": 0, "unavailable": 0} for s in sources},
                "open_backlog": {"complete": n, "total_repositories": n},
            },
        },
        "coverage-readiness.json": {
            "tracked": n, "verified_joint_28d": n, "window_days": 28,
            "stale_hours": 12, "source_verified_28d": {s: n for s in sources},
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
