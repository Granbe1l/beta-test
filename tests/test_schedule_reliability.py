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
