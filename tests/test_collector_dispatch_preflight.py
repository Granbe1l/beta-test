"""No-source-mutation tests for P0.3 late-dispatch and duplicate-request safety."""
from datetime import datetime, timedelta, timezone
import gzip
import json
from pathlib import Path

import pytest

from scripts import collector_dispatch_preflight as gate

NOW = datetime(2026, 11, 17, 3, 50, tzinfo=timezone.utc)


def choose(event="workflow_dispatch", *, age_hours=1, force=False):
    generated = NOW - timedelta(hours=age_hours)
    return gate.decide(event=event, force_refresh=force,
                       generated_at=generated, now=NOW)


@pytest.mark.parametrize("age_hours", [0, 0.25, 1, 3, 4, 5.9, 6])
def test_fresh_dispatch_is_skipped_instead_of_collecting_twice(age_hours):
    result = choose(age_hours=age_hours)
    assert result["should_collect"] is False
    assert result["reason"] == "fresh_current_main_snapshot"
    assert result["source_freshness_checked"] is True


@pytest.mark.parametrize("age_hours", [6.001, 7, 12, 36])
def test_stale_dispatch_collects_without_changing_six_hour_rescue_policy(age_hours):
    result = choose(age_hours=age_hours)
    assert result["should_collect"] is True
    assert result["reason"] == "stale_current_main_snapshot"
    assert result["threshold_minutes"] == 360


def test_race_two_rescue_dispatches_second_checks_new_published_snapshot():
    # The first accepted rescue can collect; the second gets the NEWEST
    # committed main snapshot once admitted to existing workflow concurrency.
    first = choose(age_hours=8)
    second = choose(age_hours=0.05)
    assert first["should_collect"] is True
    assert second["should_collect"] is False
    assert second["reason"] == "fresh_current_main_snapshot"


def test_original_53_min_queued_rescue_skips_when_another_collector_publishes():
    requested = NOW - timedelta(minutes=53)
    # Old requested-at snapshot age was 8h, but the CURRENT snapshot is 2min.
    old_age_at_request = 8
    updated_at_runner_start = NOW - timedelta(minutes=2)
    result = gate.decide(event="workflow_dispatch", force_refresh=False,
                         generated_at=updated_at_runner_start, now=NOW)
    assert old_age_at_request > gate.EMERGENCY_AGE_HOURS
    assert requested < updated_at_runner_start
    assert result["should_collect"] is False


@pytest.mark.parametrize("event", ["schedule", "push"])
def test_native_schedule_and_workflow_push_are_not_skipped_by_fresh_snapshot(event):
    result = choose(event, age_hours=0.01)
    assert result["should_collect"] is True
    assert result["reason"] == "native_or_workflow_change_always_collects"
    assert result["source_freshness_checked"] is False


def test_manual_force_refresh_requires_explicit_true():
    result = gate.decide(event="workflow_dispatch", force_refresh=True,
                         generated_at=None, now=NOW)
    assert result["should_collect"] is True
    assert result["reason"] == "explicit_operator_force_refresh"


def test_missing_snapshot_is_not_guessed_fresh_or_stale():
    with pytest.raises(ValueError, match="freshness_cannot_be_verified"):
        gate.decide(event="workflow_dispatch", force_refresh=False,
                    generated_at=None, now=NOW)


def test_impossible_future_snapshot_fails_closed():
    with pytest.raises(ValueError, match="unreasonably_in_future"):
        choose(age_hours=-1)


def test_small_clock_skew_is_conservatively_handled():
    result = choose(age_hours=-(3/60))
    assert result["should_collect"] is False
    assert result["snapshot_age_minutes"] == 0


def test_naive_timestamp_rejected_instead_of_assuming_utc():
    with pytest.raises(ValueError, match="no_timezone"):
        gate.utc_time("2026-11-16T20:50:45")


def test_missing_generated_at_and_corrupt_snapshot_raise(tmp_path):
    bad = tmp_path / "invalid.gz"
    bad.write_bytes(b"not gzip")
    with pytest.raises(OSError):
        gate.read_generated_at(bad)
    with gzip.open(bad, "wt", encoding="utf-8") as f:
        f.write('{"reports":[]}')
    with pytest.raises(ValueError, match="missing_committed"):
        gate.read_generated_at(bad)


def test_reads_only_committed_header_not_full_records(tmp_path):
    sample = tmp_path / "snapshot.json.gz"
    with gzip.open(sample, "wt", encoding="utf-8") as f:
        f.write('{"generated_at":"2026-11-17T03:50:45Z","reports":[')
        f.write('{"sample":"abc"},' * 1500)
        f.write("{}]}")
    assert gate.read_generated_at(sample) == datetime(
        2026, 11, 17, 3, 50, 45, tzinfo=timezone.utc)


def test_exact_source_snapshot_does_not_need_github_api_or_token(tmp_path, monkeypatch):
    sample = tmp_path / "snapshot.json.gz"
    with gzip.open(sample, "wt", encoding="utf-8") as f:
        f.write(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat()}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_dispatch")
    monkeypatch.setenv("FORCE_REFRESH", "false")
    monkeypatch.setenv("P0_CURRENT_MAIN_SNAPSHOT", str(sample))
    output = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    gate.main()
    receipt = json.loads((tmp_path / "collector-dispatch-preflight.json").read_text())
    assert receipt["reason"] == "fresh_current_main_snapshot"
    assert receipt["should_collect"] is False
    assert output.read_text() == "should_collect=false\n"
    assert "GITHUB_TOKEN" not in json.dumps(receipt)


def test_unknown_trigger_refuses_to_silently_skip():
    with pytest.raises(ValueError, match="unexpected_collector_trigger"):
        choose("workflow_run")


def test_workflow_keeps_six_hour_backup_and_native_schedule_audit():
    root = Path(__file__).resolve().parents[1]
    wf = (root / ".github/workflows/public-snapshot.yml").read_text()
    watchdog = (root / "scripts/snapshot_watchdog.py").read_text()
    assert "cron: '23 1,5,9,13,17,21 * * *'" in wf
    assert "group: public-snapshot-main" in wf
    assert "cancel-in-progress: false" in wf
    assert "if: github.event_name == 'workflow_dispatch' && inputs.force_refresh != true" in wf
    assert "git fetch --no-tags --depth=1 origin refs/heads/main" in wf
    assert "git show FETCH_HEAD:data/github_public_snapshot.json.gz" in wf
    assert "needs: dispatch-preflight" in wf
    assert "if: needs.dispatch-preflight.outputs.should_collect == 'true'" in wf
    assert "name: collector-dispatch-preflight" in wf
    assert "name: github-50-repo-source-audit" in wf
    assert "python scripts/verify_collection.py" in wf
    assert "MAX_AGE_HOURS = 6" in watchdog
    assert "BACKOFF_MINUTES = 90" in watchdog
    assert "STALE_PENDING_MINUTES = 120" in watchdog
