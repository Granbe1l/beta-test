"""P2: PR page cannot display 90-day insight as if 28-day history were complete."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.analytics.metrics import calculate_prs
from src.ui.charts import observed_merge_times

ROOT = Path(__file__).resolve().parents[1]


def test_pr_page_recomputes_kpis_and_chart_for_selected_period():
    code = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    part = code.split("def pull_request_review(", 1)[1].split(
        "def cicd_activity(", 1)[0]
    assert 'key="v3_pr_period"' in part
    assert 'qualified_reports([r], "pull_requests", days=period, now=now)' in part
    assert 'info = calculate_prs(' in part
    assert 'observation_days=period' in part
    assert 'summary([r], now=now, observation_days=period)' in part
    assert 'observed_merge_times(r["pr_rows"], now=now, days=period)' in part
    assert '"Merged · 90 days"' not in part
    assert "missing records are unknown" in part
    assert 'if verified else "exploratory sample"' in part


def test_duration_buckets_and_verified_median_share_selected_period():
    now = datetime.now(timezone.utc)
    prs = []
    for delta in (2, 3, 4, 5, 6):
        merged = now - timedelta(days=delta)
        prs.append({"state": "closed", "draft": False,
                    "created_at": merged - timedelta(days=2),
                    "merged_at": merged})
    prs.append({"state": "closed", "draft": False,
                "created_at": now-timedelta(days=72),
                "merged_at": now-timedelta(days=55)})
    m = calculate_prs(prs, now, observation_days=28, complete=True,
                      coverage_start=now-timedelta(days=31))
    chart = observed_merge_times(prs, now=now, days=28)
    assert m["merged_in_period"] == 5
    assert m["median_merge_days"] == 2.0
    assert sum(chart.values()) == m["merge_duration_n"] == 5
    assert m["merge_distribution"] == {
        "<1 day": 0, "1–7 days": 5, "7–30 days": 0, ">30 days": 0
    }


def test_no_verified_median_without_full_period():
    now = datetime.now(timezone.utc)
    p = [{"state": "closed", "draft": False,
          "created_at": now-timedelta(days=3),
          "merged_at": now-timedelta(days=1)} for _ in range(10)]
    r = calculate_prs(p, now, observation_days=28, complete=True,
                      coverage_start=now-timedelta(days=7))
    assert r["median_merge_days"] is None
    assert r["merged_in_period"] is None
