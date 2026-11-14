"""Guard the distinction between event windows and Issue aging thresholds.

28 days is the four-week default; 30+ days remains an aging band.
The two metrics deliberately have different meanings.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.analytics.comparisons import checks_in_period
from src.ui.charts import observed_outcomes


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def test_default_ci_period_is_28_days_not_30():
    runs = [
        {"created_at": NOW - timedelta(days=27, hours=23),
         "status": "completed", "conclusion": "success"},
        {"created_at": NOW - timedelta(days=29),
         "status": "completed", "conclusion": "failure"},
    ]
    actual = checks_in_period(runs, now=NOW)
    assert actual["period_days"] == 28
    assert actual["total"] == 1
    assert actual["success"] == 1
    assert checks_in_period(runs, days=30, now=NOW)["total"] == 2


def test_dashboard_activity_filters_use_four_weeks_and_age_stays_30_days():
    ui = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert '"Code pushed · last 28 days"' in ui
    assert '"Issue or PR events · last 28 days"' in ui
    assert '"No recent signal · last 28 days"' in ui
    assert '"Code pushed · last 30 days"' not in ui
    assert '"Issue or PR events · last 30 days"' not in ui
    assert '"No recent signal · last 30 days"' not in ui
    assert 'period = 28 if "28 days" in mode else 7' in ui
    assert "open issues 30+ days old" in ui
    assert "a 28-day activity filter requires its own verified" in ui


def test_default_chart_and_legacy_ui_period_are_aligned():
    charts = (ROOT / "src/ui/charts.py").read_text(encoding="utf-8")
    legacy = (ROOT / "src/ui/pages.py").read_text(encoding="utf-8")
    assert "def observed_outcomes(runs,now=None,days=28):" in charts
    assert "Workflow results · recent 28 days" in legacy
    assert "Workflow results · recent 30 days" not in legacy
    assert "since = now - timedelta(days=28)" in legacy
    assert "for i in range(29) for cat in" in legacy
