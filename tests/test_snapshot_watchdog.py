"""No future schedule is faked: only controlled stale/ongoing run decisions."""
from datetime import datetime, timedelta, timezone
import gzip
from pathlib import Path

import pytest
import scripts.snapshot_watchdog as watchdog

from scripts.snapshot_watchdog import (
    parse_time, snapshot_generated, watchdog_decision,
)

NOW = datetime(2026, 11, 13, 18, tzinfo=timezone.utc)


def _run(minutes_ago=120, status="completed", branch="main"):
    return {
        "event": "schedule",
        "head_branch": branch, "status": status,
        "created_at": (NOW-timedelta(minutes=minutes_ago)).isoformat(),
    }


def test_real_header_decoding_does_not_read_records_into_memory(tmp_path):
    file = tmp_path / "record.json.gz"
    with gzip.open(file, "wt", encoding="utf-8") as handle:
        handle.write('{"schema_version":1, "generated_at":"2026-11-13T09:00:00Z", "reports":[')
        handle.write('{"repository":{"full_name":"public/test"}}' * 100)
        handle.write("]}")
    assert snapshot_generated(file).isoformat() == "2026-11-13T09:00:00+00:00"


def test_fresh_snapshot_never_dispatches():
    result = watchdog_decision(NOW-timedelta(hours=5), NOW, [])
    assert result["action"] == "skip"
    assert result["reason"] == "snapshot_fresh"
    assert result["max_age_hours"] == 6


def test_exact_six_hour_boundary_is_not_over_eager():
    result = watchdog_decision(NOW-timedelta(hours=6), NOW, [])
    assert result["action"] == "skip"
    assert result["reason"] == "snapshot_fresh"


def test_six_hour_threshold_triggers_rescue_only_after_limit():
    result = watchdog_decision(NOW-timedelta(hours=6, minutes=1), NOW, [_run(180)])
    assert result["action"] == "dispatch"
    assert result["reason"] == "snapshot_exceeds_age_threshold"


def test_stale_snapshot_dispatches_once_if_no_collector_recently_attempted():
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [_run(180)])
    assert result["action"] == "dispatch"
    assert result["reason"] == "snapshot_exceeds_age_threshold"
    assert result["snapshot_age_hours"] == 11


def test_in_progress_stale_collector_prevents_parallel_rescue():
    # Even very old in-progress jobs block; never launch a competing collector.
    result = watchdog_decision(NOW-timedelta(hours=11), NOW,
                               [_run(200, "in_progress")])
    assert result["reason"] == "collector_already_running"
    assert result["action"] == "skip"


@pytest.mark.parametrize("status", ("queued", "requested", "waiting", "pending"))
def test_recent_pending_collector_blocks_rescue(status):
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [_run(20, status)])
    assert result["action"] == "skip"
    assert result["reason"] == "collector_already_running"


def test_abandoned_queued_collector_no_longer_blocks_rescue():
    old = _run(200, "queued")
    old["id"] = 43096556666
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [old])
    assert result["action"] == "dispatch"
    assert result["ignored_stale_pending_run_ids"] == [43096556666]


def test_updated_pending_collector_still_blocks_rescue():
    old = _run(200, "queued")
    old["updated_at"] = (NOW-timedelta(minutes=3)).isoformat()
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [old])
    assert result["action"] == "skip"
    assert result["reason"] == "collector_already_running"


def test_missing_pending_timestamp_fails_closed():
    old = _run(200, "queued")
    old.pop("created_at")
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [old])
    assert result["action"] == "skip"


def test_invalid_pending_timestamp_fails_closed():
    old = _run(200, "queued")
    old["updated_at"] = "broken"
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [old])
    assert result["action"] == "skip"


def test_exact_two_hour_pending_boundary_can_be_ignored():
    pending = _run(120, "waiting")
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [pending])
    assert result["action"] == "dispatch"


def test_backoff_prevents_hourly_dispatch_storm_after_real_attempt():
    for minutes in (5, 60, 89):
        result = watchdog_decision(NOW-timedelta(hours=16), NOW,
                                   [_run(minutes)])
        assert result["reason"] == "recent_attempt_backoff"
    assert watchdog_decision(NOW-timedelta(hours=16), NOW, [_run(90)])[
        "action"] == "dispatch"


def test_old_run_on_other_branch_does_not_block_rescue():
    assert watchdog_decision(NOW-timedelta(hours=12), NOW,
                             [_run(15, branch="feature")])["action"] == "dispatch"


def test_future_snapshot_is_an_error_not_fresh():
    result = watchdog_decision(NOW+timedelta(hours=3), NOW, [])
    assert result["action"] == "error"


def test_workflow_cannot_falsely_count_manual_dispatch_as_schedule():
    root = Path(__file__).resolve().parents[1]
    workflow = (root/".github/workflows/snapshot-watchdog.yml").read_text()
    audit = (root/"scripts/schedule_reliability.py").read_text()
    assert "cron: '47 * * * *'" in workflow
    assert "actions: write" in workflow
    assert "snapshot_watchdog.py" in workflow
    assert 'r.get("event") == "schedule"' in audit


def test_main_push_quality_success_is_an_extra_non_cron_watchdog_entry():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/snapshot-watchdog.yml").read_text()
    assert "workflow_run:" in workflow
    assert "workflows: [Quality checks]" in workflow
    assert "types: [completed]" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    # A rescue is still gated on committed snapshot age, not every push.
    assert "run: python scripts/snapshot_watchdog.py" in workflow
    assert watchdog_decision(NOW - timedelta(hours=1), NOW, [])["action"] == "skip"


def test_incomplete_workflow_history_refuses_dispatched_refresh(monkeypatch, tmp_path):
    """A missing API runs field must not be treated as an empty job list."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-test-only")
    monkeypatch.setattr(watchdog, "snapshot_generated",
                        lambda: datetime.now(timezone.utc)-timedelta(hours=7))
    class Response:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"message": "incomplete response"}
    monkeypatch.setattr(watchdog.requests, "get", lambda *args, **kwargs: Response())
    called = []
    monkeypatch.setattr(watchdog.requests, "post", lambda *args, **kwargs: called.append(True))
    with pytest.raises(RuntimeError, match="Cannot inspect current collector runs"):
        watchdog.main()
    assert called == []


def test_successful_rescue_requires_204_acknowledgement(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-test-only")
    monkeypatch.setattr(watchdog, "snapshot_generated",
                        lambda: datetime.now(timezone.utc)-timedelta(hours=7))
    class Response:
        def __init__(self, value=None, status=200):
            self.value, self.status_code = value, status
        def raise_for_status(self):
            pass
        def json(self):
            return self.value
    seen = []
    def get(*args, **kwargs):
        seen.append(kwargs.get("params"))
        return Response({"workflow_runs": []})
    monkeypatch.setattr(watchdog.requests, "get", get)
    monkeypatch.setattr(watchdog.requests, "post",
                        lambda *args, **kwargs: Response(status=200))
    with pytest.raises(RuntimeError, match="not acknowledged"):
        watchdog.main()
    assert seen == [{"branch": "main", "per_page": 50}]



@pytest.mark.parametrize("elapsed,expected", [
    (14, "normal"), (15, "warning"), (30, "warning"),
    (53, "warning"), (60, "incident"), (90, "incident"),
    (119, "incident"),
])
def test_pending_queue_age_exposed_while_dispatch_still_blocked(elapsed, expected):
    queued = _run(elapsed, "queued")
    queued["id"] = 43891870604
    result = watchdog_decision(NOW-timedelta(hours=10), NOW, [queued])
    assert result["action"] == "skip"
    assert result["reason"] == "collector_already_running"
    assert result["blocking_run"]["queue_wait_minutes"] == elapsed
    assert result["blocking_run"]["queue_severity"] == expected
    assert result["blocking_run"]["id"] == 43891870604


def test_120min_queue_updated_recently_stays_protected_and_escalated():
    queued = _run(121, "queued")
    queued["updated_at"] = (NOW-timedelta(minutes=3)).isoformat()
    result = watchdog_decision(NOW-timedelta(hours=10), NOW, [queued])
    assert result["action"] == "skip"
    assert result["blocking_run"]["queue_severity"] == "escalation"
    assert result["blocking_run"]["queue_wait_minutes"] == 121


def test_stale_old_queue_retains_proven_abandoned_queue_recovery():
    queued = _run(121, "queued")
    queued["id"] = 43096556666
    result = watchdog_decision(NOW-timedelta(hours=10), NOW, [queued])
    assert result["action"] == "dispatch"
    assert result["ignored_stale_pending_run_ids"] == [43096556666]


def test_pending_age_unknown_when_run_created_at_missing():
    queued = _run(20, "queued")
    queued.pop("created_at")
    result = watchdog_decision(NOW-timedelta(hours=10), NOW, [queued])
    assert result["action"] == "skip"
    assert result["blocking_run"]["queue_wait_minutes"] is None
    assert result["blocking_run"]["queue_severity"] == "unknown"


def test_collector_workflow_records_queue_evidence_before_ingestion():
    workflow = (Path(__file__).resolve().parents[1] /
                ".github/workflows/public-snapshot.yml").read_text()
    assert "run: python scripts/audit_collector_queue.py" in workflow
    assert workflow.index("run: python scripts/audit_collector_queue.py") < (
        workflow.index("python scripts/run_sync.py")
    )
    assert "collector-queue-audit.json" in workflow
    assert "group: public-snapshot-main" in workflow
    assert "cancel-in-progress: false" in workflow
