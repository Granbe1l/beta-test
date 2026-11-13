"""Executive readout is a truthful view model, not a quality score."""
from datetime import timedelta

from src.analytics.executive import executive_brief
from .conftest import NOW


def sample(now=NOW):
    base = "https://github.com/sample/project"
    return {
        "repository": {
            "full_name": "sample/project", "url": base,
            "pushed_at": now - timedelta(days=1),
        },
        "status": {
            "issues": "complete", "pull_requests": "partial",
            "workflow_runs": "complete",
        },
        "coverage": {
            "issues": {"coverage_start": now - timedelta(days=40)},
            "pull_requests": {"coverage_start": now - timedelta(days=40)},
            "workflow_runs": {"coverage_start": now - timedelta(days=3)},
        },
        "issue_rows": [{
            "number": 42, "url": base + "/issues/42",
            "title": "Observed older report", "state": "open",
            "created_at": now - timedelta(days=65), "closed_at": None,
        }],
        "pr_rows": [],
        "ci_rows": [],
        "issues": {
            "aged_denominator": 12, "aged_open": 9, "aged_percent": 75,
        },
        "prs": {
            "median_merge_days": None, "merge_duration_n": 0,
            "merged_evidence": [],
        },
        "ci": {
            "known_conclusion_denominator": None,
            "success_percent": None, "success": None,
        },
        "closure": None,
    }


def test_recruiter_brief_uses_source_coverage_and_original_record():
    report = sample()
    result = executive_brief([report], now=NOW)
    assert result["repositories"] == 1
    assert result["activity"]["recent_pushes"] == 1
    assert result["activity"]["opened_issues"] == 0
    assert result["coverage_28d"] == {
        "issues": 1, "pull_requests": 0, "workflow_runs": 0,
    }
    assert result["finding"]["title"] == "Older open tasks worth reviewing"
    assert result["finding"]["metric_value"] == "75%"
    assert result["source_url"] == "https://github.com/sample/project/issues/42"
    assert "ownership" in result["next_check"]


def test_recruiter_brief_does_not_infer_no_activity_is_project_health():
    report = sample()
    report["repository"]["pushed_at"] = None
    report["issue_rows"] = []
    report["issues"] = {
        "aged_denominator": None, "aged_open": None, "aged_percent": None}
    report["status"] = {
        "issues": "partial", "pull_requests": "partial", "workflow_runs": "stale"}
    result = executive_brief([report], now=NOW)
    assert result["activity"]["recent_pushes"] == 0
    assert result["coverage_28d"] == {
        "issues": 0, "pull_requests": 0, "workflow_runs": 0}
    assert result["finding"] is None
    assert result["source_url"] is None
    assert "score" not in result
    assert executive_brief([], now=NOW)["activity"] is None


def test_technical_terminology_is_not_required_in_main_executive_readout():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] /
              "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert "What should we inspect?" in source
    assert "How complete is the evidence?" in source
    assert "Open an original GitHub record" in source
    assert "not client deadlines" in source
    assert "executive_brief(chosen, findings=finding_cards)" in source
