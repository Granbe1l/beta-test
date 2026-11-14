"""Regressions for truthful UTC calendar summaries and short PR durations."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.analytics.trends import calendar_activity, daily_event_series, observed_event_totals
from src.analytics.comparison_views import comparison_rows, format_merge_days

NOW = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def test_calendar_summary_matches_chart_and_excludes_earlier_rolling_day():
    report = {
        "repository": {"full_name": "open/project",
                       "pushed_at": "2026-11-07T12:00:00Z"},
        "issue_rows": [
            {"created_at": "2026-11-07T12:00:00Z", "closed_at": None},
            {"created_at": "2026-11-08T00:00:00Z", "closed_at": None},
            {"created_at": "2026-11-14T09:00:00Z", "closed_at": None},
            {"created_at": "2026-11-14T11:00:00Z", "closed_at": None},
        ],
        "pr_rows": [{
            "created_at": "2026-11-14T08:00:00Z",
            "merged_at": "2026-11-14T09:00:00Z",
        }],
    }
    result = calendar_activity([report], days=7, now=NOW)
    chart = observed_event_totals(daily_event_series([report], days=7, now=NOW))
    assert result["utc_first_date"] == "2026-11-08"
    assert result["utc_last_date"] == "2026-11-14"
    assert result["new_issues"] == chart["Issues opened"] == 2
    assert result["merged_prs"] == chart["PRs merged"] == 1
    assert result["pushed_recently"] == 0
    report["repository"]["pushed_at"] = "2026-11-14T11:00:00Z"
    assert calendar_activity([report], now=NOW)["pushed_recently"] == 0
    report["repository"]["pushed_at"] = "2026-11-08T00:00:00Z"
    assert calendar_activity([report], now=NOW)["pushed_recently"] == 1


def test_four_minute_median_is_not_zero_days_on_comparison():
    prs = []
    for minute in (2, 3, 4, 5, 6):
        created = NOW - timedelta(days=1, hours=2)
        prs.append({"created_at": created,
                    "merged_at": created + timedelta(minutes=minute),
                    "state": "closed"})
    report = {
        "repository": {"full_name": "open/project", "category": "Other"},
        "status": {s: "complete" for s in
                   ("issues", "pull_requests", "workflow_runs")},
        "coverage": {s: {"coverage_start": NOW - timedelta(days=32)}
                     for s in ("issues", "pull_requests", "workflow_runs")},
        "open_backlog_status": "partial",
        "issue_rows": [], "pr_rows": prs, "ci_rows": [],
        "issues": {"aged_denominator": None, "aged_open": None},
    }
    value = comparison_rows([report], days=28, now=NOW)[0][
        "Median PR merge days · 28d"]
    assert 0 < value < .01 and abs(value * 1440 - 4) < .01
    assert format_merge_days(value) == "4 min"
    assert format_merge_days(1.5 / 24) == "1.5 hours"
    assert format_merge_days(3.0) == "3.0 days"
    assert format_merge_days(None) == "—"


def test_reader_links_csv_and_pr_chart_explain_scope():
    app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    trend = (ROOT / "src/ui/trend_panels.py").read_text(encoding="utf-8")
    ui = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    comparison = (ROOT / "src/ui/pages.py").read_text(encoding="utf-8")
    assert "#data-snapshot" not in app
    assert "docs/REVIEWER_QUICK_GUIDE.md" in app
    assert "UTC day status" in trend and "partial (today)" in trend
    assert "The last point is partial" in trend
    assert "calendar_activity(chosen, days=7)" in ui
    assert "First inspect" in ui
    assert 'fig.update_traces(text=[format_merge_days(v)' in comparison
