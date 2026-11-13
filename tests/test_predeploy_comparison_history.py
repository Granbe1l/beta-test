"""Critical predeployment review: comparison does not make up eligibility."""
from datetime import datetime, timedelta, timezone

from src.analytics.comparison_views import (
    comparison_rows, metric_options, metric_disclosure, preferred_metric,
    current_history_evidence,
)

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)


def repo(name="sample/alpha", complete=True, full_backlog=True):
    status = "complete" if complete else "partial"
    return {
        "repository": {"full_name": name, "category": "Backend"},
        "status": {s: status for s in ("issues", "pull_requests", "workflow_runs")},
        "coverage": {
            source: {
                "coverage_start": NOW-timedelta(days=40),
                "last_success_at": NOW-timedelta(hours=1),
            }
            for source in ("issues", "pull_requests", "workflow_runs", "open_backlog")
        },
        "open_backlog_status": "complete" if full_backlog else "partial",
        "issue_rows": [
            {"state": "closed", "closed_at": NOW-timedelta(days=3),
             "created_at": NOW-timedelta(days=50)},
            {"state": "open", "created_at": NOW-timedelta(days=35)},
        ],
        "pr_rows": [
            {"state": "closed", "created_at": NOW-timedelta(days=7),
             "merged_at": NOW-timedelta(days=2)},
        ],
        "ci_rows": [
            {"created_at": NOW-timedelta(days=1), "status": "completed",
             "conclusion": "success"}
        ],
        "issues": {"aged_denominator": 9 if full_backlog else None,
                   "aged_open": 5 if full_backlog else None},
        "observations": [],
    }


def test_period_defaults_to_28_and_all_measurements_obey_coverage():
    r = repo()
    row = comparison_rows([r], now=NOW)[0]
    assert row["Issues closed · 28d"] == 1
    assert row["PRs merged · 28d"] == 1
    assert row["Completed CI checks · 28d"] == 1
    assert row["Median PR merge days · 28d"] is None  # fewer than five
    assert row["Open issues aged 30+ (%) · full inventory"] == 55.6
    assert row["Event coverage"] == "3/3 sources · 28d"
    assert "PRs merged · 28d" in metric_options(28)
    assert comparison_rows([r], days=90, now=NOW)[0]["PRs merged · 90d"] is None


def test_incomplete_sources_are_not_zero_but_sample_is_visible():
    r = repo(complete=False, full_backlog=False)
    row = comparison_rows([r], now=NOW)[0]
    assert row["Issues closed · 28d"] is None
    assert row["PRs merged · 28d"] is None
    assert row["Completed CI checks · 28d"] is None
    assert row["Open issues aged 30+ (%) · full inventory"] is None
    assert row["Issue records retrieved · exploratory"] == 2
    assert row["PR records retrieved · exploratory"] == 1
    assert row["Event coverage"] == "0/3 sources · 28d"
    assert preferred_metric([row, row], 28) == "Issue records retrieved · exploratory"
    assert "not comparable productivity" in metric_disclosure([row], "Issue records retrieved · exploratory", 28)


def test_7_day_scans_do_not_certify_28_day_metric():
    r = repo()
    for item in r["coverage"].values():
        item["coverage_start"] = NOW-timedelta(days=8)
    row7 = comparison_rows([r], days=7, now=NOW)[0]
    row28 = comparison_rows([r], days=28, now=NOW)[0]
    assert row7["Issues closed · 7d"] == 1
    assert row28["Issues closed · 28d"] is None


def test_preferred_metric_uses_available_verified_measures_for_real_chart():
    r1 = repo()
    r2 = repo("sample/beta")
    rows = comparison_rows([r1, r2], days=28, now=NOW)
    assert preferred_metric(rows, 28) == "PRs merged · 28d"
    r2["status"] = {s: "partial" for s in r2["status"]}
    filtered = comparison_rows([r1, r2], days=28, now=NOW)
    # Full-open inventory verification is independent of Issue event-window
    # scans; do not discard this genuine verified metric.
    assert preferred_metric(filtered, 28) == "Open issues aged 30+ (%) · full inventory"
    r2["open_backlog_status"] = "partial"
    fallback = comparison_rows([r1, r2], days=28, now=NOW)
    assert preferred_metric(fallback, 28) == "Issue records retrieved · exploratory"


def test_one_verified_inventory_is_not_a_fake_historical_trend():
    r = repo(full_backlog=True)
    value = current_history_evidence(r)
    assert value["verified"]
    assert value["count"] == 9
    assert value["measured_at"] == NOW-timedelta(hours=1)
    assert "full inventory" in value["label"]


def test_no_full_inventory_shows_observed_sample_but_not_full_backlog():
    r = repo(full_backlog=False)
    value = current_history_evidence(r)
    assert not value["verified"]
    assert value["count"] == 1
    assert "not the project's verified backlog" in value["scope"]
    r["issue_rows"] = []
    assert current_history_evidence(r)["count"] is None


def test_invalid_comparison_window_rejected():
    from pytest import raises
    with raises(ValueError):
        comparison_rows([repo()], days=30, now=NOW)
