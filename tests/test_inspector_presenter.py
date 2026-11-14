"""Regression tests for evidence-grounded on-demand presentation."""
from datetime import datetime, timezone

from src.analytics.inspector_presenter import (
    ci_breakdown, pr_breakdown, inspection_summary, preview_review_plan,
)


def example():
    return {
        "sample_issues": [{"id": 101}, {"id": 102}],
        "sample_old_issues": 1,
        "sample_open_issues": 1,
        "old_issue_url": "https://github.com/psf/requests/issues/12",
        "sample_prs": [
            {"state": "open", "draft": False},
            {"state": "open", "draft": True},
            {"state": "closed", "merged_at": "2026-11-13T10:00:00Z"},
            {"state": "closed", "merged_at": None},
        ],
        "sample_runs": [
            {"status": "completed", "conclusion": "success"},
            {"status": "completed", "conclusion": "failure"},
            {"status": "completed", "conclusion": "timed_out"},
            {"status": "completed", "conclusion": "cancelled"},
            {"status": "completed", "conclusion": "neutral"},
            {"status": "in_progress", "conclusion": None},
        ],
        "sample_ci_failed": 2,
        "sample_ci_completed": 5,
        "last_failed_run_url": "https://github.com/psf/requests/actions/runs/9",
        "issues_error": None, "prs_error": None, "ci_error": None,
    }


def test_ci_chart_includes_non_success_outcomes_without_relabeling_as_success():
    data = example()
    rows = ci_breakdown(data)
    counts = {row["label"]: row["count"] for row in rows}
    assert sum(counts.values()) == len(data["sample_runs"])
    assert counts == {
        "Succeeded": 1,
        "Failed / timed out": 2,
        "Cancelled": 1,
        "Skipped / neutral": 1,
        "Pending": 1,
    }


def test_pr_chart_is_mutually_exclusive_and_draft_is_not_merged():
    data = example()
    counts = {row["label"]: row["count"] for row in pr_breakdown(data)}
    assert counts == {"Open": 1, "Draft": 1, "Merged": 1,
                      "Closed without merge": 1}
    assert sum(counts.values()) == len(data["sample_prs"])


def test_review_plan_is_evidence_linked_and_does_not_diagnose_project_quality():
    data = example()
    result = inspection_summary(data)
    assert result["external"] is True
    assert result["verified_28d"] is False
    assert result["ci_observed"] == 6
    assert result["pr_observed"] == 4
    assert result["issue_observed"] == 2
    assert result["source_gaps"] == 0
    checks = result["review_plan"]
    assert checks[0]["title"] == "Inspect unsuccessful automated checks"
    assert checks[0]["url"] == data["last_failed_run_url"]
    assert checks[1]["title"] == "Review older open Issues"
    assert checks[1]["url"] == data["old_issue_url"]
    assert "failed or timed out" in checks[0]["explanation"]
    assert "not a full 28-day history" in result["limitations"]


def test_partial_source_is_unknown_not_an_observed_zero_or_full_28_days():
    data = example()
    data["issues_error"] = "rate-limited or restricted"
    data["ci_error"] = "HTTP 503"
    result = inspection_summary(data)
    assert result["source_gaps"] == 2
    assert result["ci"] == []
    assert all(row["tag"] != "Review next" for row in result["review_plan"])
    assert result["review_plan"][0]["tag"] == "Evidence gap"
    assert "not zero activity" in result["review_plan"][0]["explanation"]
    assert result["verified_28d"] is False


def test_empty_successful_pages_do_not_become_full_source_coverage():
    data = example()
    data.update({
        "sample_runs": [], "sample_prs": [], "sample_issues": [],
        "sample_ci_failed": 0, "sample_ci_completed": 0,
        "sample_old_issues": 0, "sample_open_issues": 0,
        "last_failed_run_url": None,
        "old_issue_url": None,
    })
    output = inspection_summary(data)
    assert output["ci"] == []
    assert output["prs"] == []
    assert output["review_plan"][0]["tag"] == "No sample signal"
    assert output["verified_28d"] is False


def test_ui_no_dataset_mutation_and_clear_external_label():
    from pathlib import Path
    ui = (Path(__file__).resolve().parents[1] /
          "src/ui/repo_lookup.py").read_text(encoding="utf-8")
    assert "separate from the 50-project dataset" in ui
    assert "Search results never change its members" in ui
    assert "_cached_public_preview.clear(repo_name)" in ui
    assert "disabled=disabled" in ui
    assert "st.plotly_chart" in ui
    assert "st.dataframe" in ui
    assert "st.link_button" in ui
