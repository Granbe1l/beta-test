"""No future schedule is faked: only controlled stale/ongoing run decisions."""
from datetime import datetime, timedelta, timezone
import gzip
from pathlib import Path

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


def test_stale_snapshot_dispatches_once_if_no_collector_recently_attempted():
    result = watchdog_decision(NOW-timedelta(hours=11), NOW, [_run(180)])
    assert result["action"] == "dispatch"
    assert result["reason"] == "snapshot_exceeds_age_threshold"
    assert result["snapshot_age_hours"] == 11


def test_in_progress_stale_collector_prevents_parallel_rescue():
    for status in ("queued", "in_progress", "waiting", "requested"):
        result = watchdog_decision(NOW-timedelta(hours=11), NOW,
                                   [_run(200, status)])
        assert result["reason"] == "collector_already_running"
        assert result["action"] == "skip"


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
