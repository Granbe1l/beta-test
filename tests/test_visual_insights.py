"""Visual findings must derive their numbers from existing sampled records."""
from src.analytics.findings import findings_for_repo


def test_visual_insight_metrics_have_truthful_denominators():
    report = {
        "repository": {"full_name": "sample/project",
                       "url": "https://github.com/sample/project"},
        "issues": {
            "aged_denominator": 20, "aged_percent": 40,
            "aged_open": 8,
        },
        "prs": {
            "median_merge_days": 0.5,
            "merge_duration_n": 10,
            "merged_evidence": [
                "https://github.com/sample/project/pull/20"],
        },
        "closure": None,
        "ci": {
            "known_conclusion_denominator": 20,
            "success_percent": 70,
            "success": 14,
        },
    }
    cards = {item["type"]: item for item in findings_for_repo(report)}
    issue = cards["issue-aging"]
    assert issue["metric_value"] == "40%"
    assert issue["observed"] == 8
    assert issue["denominator"] == 20
    assert issue["observed"] / issue["denominator"] == .4
    ci = cards["ci"]
    assert ci["metric_value"] == "70%"
    assert ci["observed"] == 14
    assert ci["denominator"] == 20
    duration = cards["merge-duration"]
    assert duration["metric_value"] == "12.0 hours"
    assert duration.get("denominator") is None
    assert duration.get("observed") is None
    assert "10" in duration["metric_context"]
    assert all(item.get("url", "").startswith("https://github.com/sample/project")
               for item in cards.values())


def test_ui_does_not_show_fictitious_percentage_when_sample_is_empty():
    report = {
        "repository": {"full_name": "sample/empty",
                       "url": "https://github.com/sample/empty"},
        "issues": {"aged_denominator": 0, "aged_percent": None, "aged_open": 0},
        "prs": {"median_merge_days": None, "merge_duration_n": 0},
        "closure": None,
        "ci": {"known_conclusion_denominator": 0, "success_percent": None,
               "success": 0},
    }
    assert findings_for_repo(report) == []
