"""Scheduled-run reliability requires actual cron events at plausible intervals."""
from datetime import datetime, timedelta, timezone

from scripts.schedule_reliability import schedule_health

NOW = datetime(2026, 11, 13, tzinfo=timezone.utc)


def run(hours_ago, *, event="schedule", conclusion="success", branch="main"):
    return {
        "event": event, "conclusion": conclusion, "status": "completed",
        "head_branch": branch,
        "created_at": (NOW - timedelta(hours=hours_ago)).isoformat(),
        "html_url": "https://github.com/sample/project/actions/runs/123",
    }


def test_only_real_cron_runs_count_toward_reliability():
    rows = [run(0, event="push"), run(6, event="workflow_dispatch"),
            run(12, branch="feature"), run(18)]
    result = schedule_health(rows)
    assert result["status"] == "insufficient_history"
    assert result["actual_scheduled_runs"] == 1


def test_three_successful_four_hour_cron_runs_verify_cycle():
    result = schedule_health([run(12), run(8), run(4)], now=NOW)
    assert result["status"] == "verified_recent_cycles"
    assert result["successful_scheduled_runs"] == 3
    assert result["observed_intervals_hours"] == [4, 4]


def test_missing_or_failed_scheduled_run_never_passes():
    assert schedule_health([run(4), run(8, conclusion="failure"), run(12)], now=NOW)[
        "status"] == "needs_review"
    assert schedule_health([run(4), run(25), run(29)], now=NOW)[
        "status"] == "needs_review"


def test_three_old_successful_runs_do_not_prove_current_scheduling():
    result = schedule_health(
        [run(72), run(76), run(80)], now=NOW)
    assert result["successful_scheduled_runs"] == 3
    assert result["observed_intervals_hours"] == [4, 4]
    assert result["status"] == "stale_schedule"
    assert result["latest_scheduled_run_age_hours"] == 72
    assert not result["latest_schedule_is_recent"]


def test_last_scheduled_run_must_be_recent_and_not_in_future():
    result = schedule_health(
        [run(4), run(8), run(12)], now=NOW)
    assert result["status"] == "verified_recent_cycles"
    assert result["latest_schedule_is_recent"]
    future = schedule_health(
        [run(-2), run(2), run(6)], now=NOW)
    assert future["status"] == "stale_schedule"
    assert future["latest_scheduled_run_age_hours"] == -2


def test_insufficient_schedule_evidence_retains_last_known_age():
    result = schedule_health([run(120), run(126)], now=NOW)
    assert result["status"] == "insufficient_history"
    assert result["actual_scheduled_runs"] == 2
    assert result["latest_scheduled_run_age_hours"] == 120
    assert not result["latest_schedule_is_recent"]
    empty = schedule_health([], now=NOW)
    assert empty["status"] == "insufficient_history"
    assert empty["latest_scheduled_run_age_hours"] is None


def test_user_triggered_successes_cannot_rescue_failed_scheduled_runs():
    rows = [run(0, event="push"), run(1, event="workflow_dispatch"),
            run(4, conclusion="failure"), run(8), run(12)]
    assert schedule_health(rows, now=NOW)["status"] == "needs_review"


def test_six_hour_cycle_is_not_proof_of_four_hour_cadence():
    result = schedule_health([run(18), run(12), run(6)], now=NOW)
    assert result["successful_scheduled_runs"] == 3
    assert result["observed_intervals_hours"] == [6, 6]
    assert result["status"] == "needs_review"



# Strict slot audit: spacing alone can conceal a missing official cron slot.
from scripts.schedule_reliability import (
    configured_four_hour_cron, parse_four_hour_cron,
    slot_delivery_report, schedule_health_with_slots,
)

FOUR_HOUR_CRON = "23 1,5,9,13,17,21 * * *"
SLOT_NOW = datetime(2026, 11, 16, 7, 30, tzinfo=timezone.utc)


def slot_run(at, *, event="schedule", status="completed",
             conclusion="success", branch="main", run_id=100):
    return {
        "id": run_id, "event": event, "status": status,
        "conclusion": conclusion, "head_branch": branch,
        "created_at": at, "html_url": "https://github.com/example/actions/runs/100",
    }


def test_slots_use_the_checked_in_four_hour_utc_workflow_cron():
    assert configured_four_hour_cron() == FOUR_HOUR_CRON
    assert parse_four_hour_cron(FOUR_HOUR_CRON) == (23, (1, 5, 9, 13, 17, 21))


def test_actual_three_consecutive_expected_slots_can_pass():
    rows = [
        slot_run("2026-11-15T21:53:00Z", run_id=11),
        slot_run("2026-11-16T01:32:00Z", run_id=12),
        slot_run("2026-11-16T05:35:00Z", run_id=13),
    ]
    report = slot_delivery_report(rows, cron=FOUR_HOUR_CRON, now=SLOT_NOW,
                                  lookback_hours=13)
    assert report["eligible_slots"] == 3
    assert report["successful_slots"] == 3
    assert report["slot_success_percent"] == 100
    assert report["recent_required_slots_passed"]
    assert report["slots"][-1]["delay_minutes"] == 12


def test_manual_dispatch_and_push_never_fill_missing_native_schedule_slots():
    rows = [
        slot_run("2026-11-15T21:25:00Z", run_id=10),
        slot_run("2026-11-16T01:25:00Z", run_id=11),
        slot_run("2026-11-16T05:25:00Z", event="workflow_dispatch", run_id=12),
        slot_run("2026-11-16T05:29:00Z", event="push", run_id=13),
        slot_run("2026-11-16T05:31:00Z", branch="feature", run_id=14),
    ]
    result = slot_delivery_report(rows, cron=FOUR_HOUR_CRON, now=SLOT_NOW,
                                  lookback_hours=13)
    assert result["successful_slots"] == 2
    assert result["missing_slots"] == ["2026-11-16T05:23:00+00:00"]
    assert not result["recent_required_slots_passed"]


def test_three_spaced_runs_at_wrong_clock_phase_cannot_pass_merged_audit():
    rows = [
        slot_run("2026-11-15T22:59:00Z", run_id=11),
        slot_run("2026-11-16T02:59:00Z", run_id=12),
        slot_run("2026-11-16T06:59:00Z", run_id=13),
    ]
    assert schedule_health(rows, now=SLOT_NOW)["status"] == "verified_recent_cycles"
    strict = schedule_health_with_slots(rows, now=SLOT_NOW, cron=FOUR_HOUR_CRON)
    assert strict["status"] == "needs_review"
    assert strict["slot_gate_reason"] == "real_expected_slots_not_verified"
    assert not strict["slot_delivery"]["recent_required_slots_passed"]


def test_delayed_schedule_run_is_reported_not_falsely_matched_to_next_slot():
    rows = [
        slot_run("2026-11-15T21:25:00Z", run_id=11),
        slot_run("2026-11-16T01:25:00Z", run_id=12),
        slot_run("2026-11-16T06:53:00Z", run_id=13),
    ]
    report = slot_delivery_report(rows, cron=FOUR_HOUR_CRON,
                                  now=datetime(2026, 11, 16, 7, 55, tzinfo=timezone.utc),
                                  lookback_hours=13)
    assert report["missing_slots"] == ["2026-11-16T05:23:00+00:00"]
    assert report["unmatched_schedule_runs"] == [
        {"run_id": 13, "created_at_utc": "2026-11-16T06:53:00+00:00"}
    ]


def test_maturity_grace_does_not_prematurely_fail_a_current_slot():
    report = slot_delivery_report([], cron=FOUR_HOUR_CRON,
                                  now=datetime(2026, 11, 16, 6, 0, tzinfo=timezone.utc),
                                  lookback_hours=13)
    assert "2026-11-16T05:23:00+00:00" not in report["missing_slots"]


def test_duplicate_or_failed_slot_is_not_accepted_as_success():
    rows = [
        slot_run("2026-11-15T21:25:00Z", run_id=11),
        slot_run("2026-11-16T01:25:00Z", run_id=12, conclusion="failure"),
        slot_run("2026-11-16T05:25:00Z", run_id=13),
        slot_run("2026-11-16T05:29:00Z", run_id=14),
    ]
    report = slot_delivery_report(rows, cron=FOUR_HOUR_CRON,
                                  now=SLOT_NOW, lookback_hours=13)
    assert [s["status"] for s in report["slots"]] == [
        "success", "failed", "duplicate"
    ]
    assert not report["recent_required_slots_passed"]


def test_unknown_or_non_four_hour_cron_fails_closed():
    import pytest
    for cron in ["0 * * * *", "23 1,5,9 * * *", "23 1,5,9,13,17,21 * * 1",
                 "23 1,5,9,13,17,22 * * *", "@hourly"]:
        with pytest.raises(ValueError):
            parse_four_hour_cron(cron)

def test_newly_started_slot_can_pass_immediately_when_real_run_finished():
    now = datetime(2026, 11, 16, 5, 34, tzinfo=timezone.utc)
    rows = [
        slot_run("2026-11-15T21:25:00Z", run_id=11),
        slot_run("2026-11-16T01:25:00Z", run_id=12),
        slot_run("2026-11-16T05:31:00Z", run_id=13),
    ]
    report = slot_delivery_report(rows, cron=FOUR_HOUR_CRON, now=now,
                                  lookback_hours=13)
    assert report["slots"][-1]["status"] == "success"
    assert report["recent_required_slots_passed"]
    strict = schedule_health_with_slots(rows, now=now, cron=FOUR_HOUR_CRON)
    assert strict["status"] == "verified_recent_cycles"
    assert strict["run_ids"] == [13, 12, 11]


def test_current_absent_slot_is_awaiting_not_prematurely_missing():
    now = datetime(2026, 11, 16, 5, 34, tzinfo=timezone.utc)
    rows = [slot_run("2026-11-15T21:25:00Z", run_id=11),
            slot_run("2026-11-16T01:25:00Z", run_id=12)]
    report = slot_delivery_report(rows, cron=FOUR_HOUR_CRON, now=now,
                                  lookback_hours=13)
    assert report["slots"][-1]["status"] == "awaiting_window"
    assert "2026-11-16T05:23:00+00:00" not in report["missing_slots"]
    assert report["successful_slots"] == 2
    assert not report["recent_required_slots_passed"]
