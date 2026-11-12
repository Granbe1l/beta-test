"""Real, timestamped line-chart events—no synthetic days, counts or trends."""
from datetime import datetime, timedelta, timezone
from src.analytics.trends import daily_event_series, observed_event_totals

NOW = datetime(2026, 11, 12, 15, 30, tzinfo=timezone.utc)


def repo():
    return {
        "issue_rows": [
            {"created_at": NOW - timedelta(days=1),
             "closed_at": None},
            {"created_at": NOW - timedelta(days=4),
             "closed_at": NOW - timedelta(days=1)},
            {"created_at": NOW - timedelta(days=40),
             "closed_at": None},
        ],
        "pr_rows": [
            {"created_at": NOW - timedelta(days=2),
             "merged_at": NOW - timedelta(days=1)},
            {"created_at": NOW - timedelta(days=29),
             "merged_at": None},
        ],
    }


def test_true_daily_events_and_zero_filled_calendar():
    rows = daily_event_series([repo()], days=7, now=NOW)
    assert len(rows) == 7
    assert rows[0]["Date"] == "2026-11-06"
    assert rows[-1]["Date"] == "2026-11-12"
    total = observed_event_totals(rows)
    assert total == {"Issues opened": 2, "Issues closed": 1,
                     "PRs opened": 1, "PRs merged": 1}
    assert rows[-2]["Issues opened"] == 1
    assert rows[-2]["Issues closed"] == 1
    assert rows[-2]["PRs merged"] == 1
    assert rows[0]["Issues opened"] == 0  # zero in retrieved data only


def test_missing_dates_are_not_invented():
    empty = daily_event_series([{"issue_rows": [], "pr_rows": []}],
                               days=28, now=NOW)
    assert len(empty) == 28
    assert all(not row["Issues opened"] and not row["PRs opened"] for row in empty)


def test_older_events_excluded_by_period():
    short = observed_event_totals(daily_event_series([repo()], days=7, now=NOW))
    long = observed_event_totals(daily_event_series([repo()], days=28, now=NOW))
    assert short == long
    assert long["Issues opened"] == 2


def test_event_timestamp_timezone_normalization():
    offset_row = {"issue_rows":[{"created_at": "2026-11-12T00:20:00+07:00"}],
                  "pr_rows":[]}
    results = daily_event_series([offset_row], days=7, now=NOW)
    assert results[-2]["Issues opened"] == 1  # UTC Nov 11


def test_invalid_period_rejected():
    try:
        daily_event_series([], days=0, now=NOW)
        assert False, "Expected bounded period validation"
    except ValueError:
        pass
