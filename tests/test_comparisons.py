"""Regression: do not infer trends from unequal cohorts or mismatched periods."""
from datetime import datetime, timedelta, timezone
from src.analytics.comparisons import comparable_observation_pair, checks_in_period

NOW = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)


def snapshot(name, data):
    return {"repository": {"full_name": name},
            "observations": [
                {"measured_at": NOW - timedelta(days=days, hours=hour),
                 "open_issues_observed": issues,
                 "open_prs_observed": prs}
                for days, hour, issues, prs in data]}


def test_pair_uses_exactly_matching_cohort():
    a = snapshot("org/A", [(0, 0, 10, 4), (1, 0, 12, 5)])
    b = snapshot("org/B", [(0, 0, 100, 90)])  # No prior observation
    pair = comparable_observation_pair([a, b])
    assert pair["matched_count"] == 1
    assert pair["repositories"] == ["org/A"]
    assert pair["previous_issues"] == 12
    assert pair["current_issues"] == 10
    assert pair["previous_prs"] == 5
    assert pair["current_prs"] == 4


def test_pair_uses_latest_measurement_on_each_day():
    r = snapshot("org/A", [
        (0, 0, 5, 2),
        (0, 2, 200, 100),
        (1, 0, 7, 3),
    ])
    pair = comparable_observation_pair([r])
    assert pair["current_issues"] == 5
    assert pair["previous_issues"] == 7


def test_one_snapshot_does_not_invent_a_trend():
    assert comparable_observation_pair([snapshot("org/A", [(0, 0, 5, 2)])]) is None
    assert comparable_observation_pair([]) is None


def ci(days, conclusion, status="completed"):
    return {"created_at": NOW - timedelta(days=days),
            "status": status, "conclusion": conclusion}


def test_ci_period_and_denominator_match_graph():
    runs = [
        ci(2, "success"),
        ci(3, "failure"),
        ci(4, "skipped"),
        ci(5, None),
        ci(6, "cancelled"),
        ci(55, "success"),
        ci(1, "success", status="in_progress"),
    ]
    recent = checks_in_period(runs, days=30, now=NOW)
    assert recent["total"] == 5
    assert recent["known"] == 4
    assert recent["unknown"] == 1
    assert recent["success"] == 1
    assert recent["failure"] == 1
    assert recent["success_percent"] == 25
    assert sum(recent["counts"].values()) == recent["known"]
    assert len(recent["daily"]) == recent["known"]

    old = checks_in_period(runs, days=90, now=NOW)
    assert old["total"] == 6
    assert old["known"] == 5
    assert old["success_percent"] == 40
    assert sum(old["counts"].values()) == len(old["daily"]) == old["known"]


def test_no_known_ci_results_is_not_100_or_zero_percent():
    result = checks_in_period([ci(1, None)], now=NOW)
    assert result["success_percent"] is None
    assert result["known"] == 0
    assert result["total"] == 1



def test_open_issue_collection_method_change_blocks_false_matched_growth():
    latest = NOW
    report = {"repository": {"full_name": "org/A"}, "observations": [
        {"measured_at": latest - timedelta(days=1),
         "open_issues_observed": 12, "open_prs_observed": 5,
         "collection_basis": "sampled_updated_events"},
        {"measured_at": latest,
         "open_issues_observed": 140, "open_prs_observed": 5,
         "collection_basis": "verified_open_inventory"},
    ]}
    assert comparable_observation_pair([report]) is None


def test_matched_cohort_allows_same_basis_on_both_days():
    report = {"repository": {"full_name": "org/A"}, "observations": [
        {"measured_at": NOW-timedelta(days=1),
         "open_issues_observed": 140, "open_prs_observed": 5,
         "collection_basis": "verified_open_inventory"},
        {"measured_at": NOW,
         "open_issues_observed": 132, "open_prs_observed": 4,
         "collection_basis": "verified_open_inventory"},
    ]}
    pair = comparable_observation_pair([report])
    assert pair["matched_count"] == 1
    assert pair["current_issues"] == 132
    assert pair["previous_issues"] == 140
    assert "same collection method" in pair["definition"]


def test_legacy_missing_basis_is_not_matched_to_explicit_new_basis():
    report = {"repository": {"full_name": "org/A"}, "observations": [
        {"measured_at": NOW-timedelta(days=1),
         "open_issues_observed": 12, "open_prs_observed": 5},
        {"measured_at": NOW,
         "open_issues_observed": 132, "open_prs_observed": 4,
         "collection_basis": "sampled_updated_events"},
    ]}
    assert comparable_observation_pair([report]) is None
