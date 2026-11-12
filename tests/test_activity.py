"""Tests for recent activity: no fake trend, no assumption that a repo is finished."""
from datetime import datetime, timedelta, timezone

from src.analytics.activity import (
    activity_label, recent_activity, sample_activity, weekly_activity, within_window,
)

NOW = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)


def repo(push_days, issues=None, prs=None):
    return {
        "repository": {"full_name": "sample/repo", "pushed_at": NOW - timedelta(days=push_days)},
        "issue_rows": issues or [],
        "pr_rows": prs or [],
    }


def test_recent_push_is_a_signal_not_an_issue_or_pr_event():
    r = repo(2)
    a = recent_activity(r, NOW)
    assert a["pushed_recently"]
    assert not a["recent_issue_or_pr_event"]
    assert activity_label(r, NOW) == "Recent code push"


def test_recent_events_and_weekly_count_come_only_from_recorded_timestamps():
    r = repo(
        19,
        issues=[{"created_at": NOW - timedelta(days=1), "closed_at": None},
                {"created_at": NOW - timedelta(days=30),
                 "closed_at": NOW - timedelta(days=2)}],
        prs=[{"created_at": NOW - timedelta(days=3),
              "merged_at": NOW - timedelta(days=1)}],
    )
    a = recent_activity(r, NOW)
    assert not a["pushed_recently"]
    assert a["recent_issue_or_pr_event"]
    assert [a[k] for k in ("new_issues", "closed_issues", "new_prs", "merged_prs")] == [1, 1, 1, 1]
    assert activity_label(r, NOW) == "Recent issue/PR activity"
    s = sample_activity([r], NOW)
    assert s["with_issue_or_pr_events"] == 1
    assert s["pushed_recently"] == 0
    series = weekly_activity([r], NOW)
    assert sum(row["Issues opened"] for row in series) == 2
    assert sum(row["Issues closed"] for row in series) == 1
    assert sum(row["PRs opened"] for row in series) == 1
    assert sum(row["PRs merged"] for row in series) == 1


def test_no_recent_signal_does_not_label_repository_finished():
    r = repo(32)
    a = recent_activity(r, NOW)
    assert not a["pushed_recently"]
    assert not a["recent_issue_or_pr_event"]
    assert "No recent signal" in activity_label(r, NOW)
    assert not within_window(NOW + timedelta(days=2), NOW)


def test_aggregate_does_not_infer_missing_events():
    a = repo(2)
    b = repo(14, issues=[{"created_at": NOW - timedelta(days=1)}])
    s = sample_activity([a, b], NOW)
    assert s["repositories"] == 2
    assert s["pushed_recently"] == 1
    assert s["with_issue_or_pr_events"] == 1
    assert s["new_issues"] == 1
    assert s["new_prs"] == 0
