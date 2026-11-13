"""Visual findings must derive their numbers from existing sampled records."""
from datetime import datetime, timedelta, timezone

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



def test_adjacent_month_comparison_requires_complete_56_day_source_window():
    """Do not claim a 100% decline when older issue activity is undercollected."""
    now = datetime.now(timezone.utc)
    report = {
        "repository": {
            "full_name": "example/repo",
            "url": "https://github.com/example/repo",
        },
        "issues": {"aged_denominator": 0, "aged_percent": None,
                   "aged_open": 0},
        "prs": {"median_merge_days": None, "merge_duration_n": 0},
        "ci": {"known_conclusion_denominator": 0, "success_percent": None,
               "success": 0},
        "closure": {"denominator": 21, "change_percent": -100,
                    "recent": 0, "previous": 21},
        "status": {"issues": "partial"},
        "coverage": {"issues": {"coverage_start": now - timedelta(days=90)}},
    }
    assert not any(x["type"] == "closure-change" for x in findings_for_repo(report))
    report["status"]["issues"] = "complete"
    report["coverage"]["issues"]["coverage_start"] = now - timedelta(days=14)
    assert not any(x["type"] == "closure-change" for x in findings_for_repo(report))
    report["coverage"]["issues"]["coverage_start"] = now - timedelta(days=57)
    found = [x for x in findings_for_repo(report) if x["type"] == "closure-change"]
    assert len(found) == 1
    assert found[0]["metric_value"] == "0"
    assert found[0]["recent_count"] == 0
    assert found[0]["previous_count"] == 21
    assert "0 in the latest 28 days" in found[0]["headline"]
    assert "-100%" not in found[0]["headline"]


def test_all_four_finding_categories_remain_eligible_for_portfolio_triage():
    """An early per-repository cap must not hide the fourth insight category."""
    now = datetime.now(timezone.utc)
    base = "https://github.com/example/project"
    report = {
        "repository": {"full_name": "example/project", "url": base},
        "issues": {"aged_denominator": 20, "aged_percent": 60, "aged_open": 12},
        "prs": {"median_merge_days": 7.0, "merge_duration_n": 8,
                "merged_evidence": [base + "/pull/31"]},
        "ci": {"known_conclusion_denominator": 20, "success_percent": 50,
               "success": 10},
        "closure": {"denominator": 10, "change_percent": -50,
                    "recent": 5, "previous": 10},
        "status": {"issues": "complete"},
        "coverage": {"issues": {"coverage_start": now - timedelta(days=70)}},
        "issue_rows": [
            {"number": 11, "url": base + "/issues/11", "title": "Old open task",
             "state": "open", "created_at": now - timedelta(days=95)},
            {"number": 12, "url": base + "/issues/12", "title": "New task",
             "state": "open", "created_at": now - timedelta(days=2)},
            {"number": 13, "url": base + "/issues/13", "title": "Closed item",
             "state": "closed", "created_at": now - timedelta(days=45),
             "closed_at": now - timedelta(days=4)},
        ],
        "pr_rows": [
            {"number": 31, "url": base + "/pull/31", "title": "Change in code",
             "created_at": now - timedelta(days=15),
             "merged_at": now - timedelta(days=3)},
        ],
        "ci_rows": [
            {"url": base + "/actions/runs/50", "workflow_name": "Build",
             "status": "completed", "conclusion": "failure",
             "created_at": now - timedelta(days=2)},
            {"url": base + "/actions/runs/51", "workflow_name": "Build",
             "status": "completed", "conclusion": "success",
             "created_at": now - timedelta(days=1)},
        ],
    }
    found = {item["type"]: item for item in findings_for_repo(report)}
    assert set(found) == {"issue-aging", "merge-duration", "closure-change", "ci"}
    assert found["issue-aging"]["examples"][0]["url"] == base + "/issues/11"
    assert found["merge-duration"]["examples"][0]["url"] == base + "/pull/31"
    assert found["ci"]["examples"][0]["url"] == base + "/actions/runs/50"
    assert found["closure-change"]["examples"][0]["url"] == base + "/issues/13"
    assert all(item["url"].startswith(base + "/") for f in found.values()
               for item in f["examples"])


def test_evidence_shortlist_rejects_unrelated_url_and_unobserved_records():
    from src.analytics.findings import evidence_examples
    now = datetime.now(timezone.utc)
    base = "https://github.com/example/project"
    report = {
        "repository": {"full_name": "example/project", "url": base},
        "issue_rows": [
            {"number": 1, "title": "not our repo",
             "url": "https://github.com/another/project/issues/1",
             "state": "open", "created_at": now - timedelta(days=200)},
            {"number": 2, "title": "valid",
             "url": base + "/issues/2",
             "state": "open", "created_at": now - timedelta(days=50)},
            {"number": 3, "title": "too new",
             "url": base + "/issues/3",
             "state": "open", "created_at": now - timedelta(days=1)},
        ],
    }
    assert [x["url"] for x in evidence_examples(report, "issue-aging", now=now)] == [
        base + "/issues/2"]
    assert evidence_examples(report, "ci", now=now) == []
    assert evidence_examples(report, "unknown", now=now) == []
