"""Evidence-first tests for GitHub run-to-job queue latency, no live dispatch."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from scripts import audit_collector_queue as audit

CREATED = datetime(2026, 11, 16, 15, 1, 1, tzinfo=timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def fixture(pre_job_minutes: float, runner_seconds: float = 2):
    job_created = CREATED + timedelta(minutes=pre_job_minutes)
    started = job_created + timedelta(seconds=runner_seconds)
    run = {"id": 43891870604, "event": "workflow_dispatch",
           "created_at": iso(CREATED)}
    jobs = [{"name": "refresh", "id": 133418939242,
             "created_at": iso(job_created), "started_at": iso(started)}]
    return run, jobs


def test_real_41_pre_job_delay_is_distinct_from_collector_runtime():
    run, jobs = fixture(53 + 10/60)
    report = audit.queue_receipt(run, jobs)
    assert report["status"] == "verified"
    assert report["pre_job_queue_minutes"] == 53.17
    assert report["runner_start_wait_seconds"] == 2
    assert report["severity"] == "warning"
    assert report["trigger_event"] == "workflow_dispatch"
    assert report["run_id"] == 43891870604


def test_realistic_fast_runner_is_normal():
    run, jobs = fixture(1/60, runner_seconds=3)
    report = audit.queue_receipt(run, jobs)
    assert report["severity"] == "normal"
    assert report["pre_job_queue_minutes"] == 0.02
    assert report["runner_start_wait_seconds"] == 3


@pytest.mark.parametrize("minutes,expected", [
    (14.99, "normal"), (15, "warning"), (30, "warning"),
    (53, "warning"), (59.99, "warning"), (60, "incident"),
    (90, "incident"), (119.99, "incident"), (120, "escalation"),
    (150, "escalation"),
])
def test_explicit_operational_boundaries(minutes, expected):
    assert audit.queue_severity(minutes) == expected


def test_do_not_claim_verified_queue_if_job_not_yet_created():
    run, jobs = fixture(53)
    with pytest.raises(ValueError, match="expected_exactly_one"):
        audit.queue_receipt(run, [])
    with pytest.raises(ValueError, match="expected_exactly_one"):
        audit.queue_receipt(run, [*jobs, *jobs])


def test_invalid_or_naive_provider_timestamp_refuses_evidence():
    run, jobs = fixture(2)
    run["created_at"] = "2026-11-16T15:01:01"  # UTC offset unknown
    with pytest.raises(ValueError, match="timezone"):
        audit.queue_receipt(run, jobs)
    run["created_at"] = "unknown"
    with pytest.raises(ValueError):
        audit.queue_receipt(run, jobs)


def test_negative_or_reversed_provider_durations_are_rejected():
    run, jobs = fixture(2)
    jobs[0]["created_at"] = iso(CREATED - timedelta(seconds=1))
    with pytest.raises(ValueError, match="inconsistent_provider"):
        audit.queue_receipt(run, jobs)
    run, jobs = fixture(2, runner_seconds=-2)
    with pytest.raises(ValueError, match="inconsistent_provider"):
        audit.queue_receipt(run, jobs)


def test_provider_http_data_only_read_no_dispatch_or_token_leak():
    run, jobs = fixture(53)
    seen = []
    class Response:
        def __init__(self, data):
            self.data = data
        def raise_for_status(self):
            pass
        def json(self):
            return self.data
    class Client:
        def get(self, url, **kwargs):
            seen.append((url, kwargs))
            return Response(run if url.endswith("/43891870604") else {"jobs": jobs})
    result = audit.inspect_current_run(repo="Granbe1l/beta-test",
                                       run_id="43891870604",
                                       token="test-only", client=Client())
    assert result["status"] == "verified"
    assert len(seen) == 2
    assert all(item[1]["timeout"] == 20 for item in seen)
    assert all(item[0].startswith("https://api.github.com/") for item in seen)
    assert "test-only" not in json.dumps(result)


def test_missing_context_fails_closed_for_audit_not_collector():
    with pytest.raises(ValueError, match="missing_or_invalid"):
        audit.inspect_current_run(repo="", run_id="abc", token="")


def test_audit_unavailable_is_explicit_and_never_blocks_collection(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_RUN_ID", "43891870604")
    monkeypatch.setenv("GITHUB_REPOSITORY", "Granbe1l/beta-test")
    monkeypatch.setenv("GITHUB_TOKEN", "test-only")
    def broken(**_kwargs):
        raise ValueError("test failure secret context ignored")
    monkeypatch.setattr(audit, "inspect_current_run", broken)
    audit.main()  # Must NOT throw and must emit an honest audit, not 0 delay.
    result = json.loads((tmp_path / "collector-queue-audit.json").read_text())
    assert result["status"] == "unavailable"
    assert "pre_job_queue_minutes" not in result
    assert result["run_id"] == "43891870604"
    assert "secret" not in json.dumps(result)
