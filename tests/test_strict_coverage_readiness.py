"""The real collector audit distinguishes short complete windows from true verified 28d."""
from datetime import datetime, timedelta, timezone

from scripts.audit_coverage_readiness import strict_readiness

NOW = datetime(2026, 11, 13, 16, tzinfo=timezone.utc)


def checkpoint(days, age_hours, *, error=None):
    return {
        "coverage_start": (NOW-timedelta(days=days)).isoformat() if days else None,
        "last_success_at": (NOW-timedelta(hours=age_hours)).isoformat() if age_hours is not None else None,
        "last_error": error,
        "pages_fetched": 18,
    }


def repo(name, *, ci="complete", ci_days=40, ci_age=1,
         issues_days=40, issues_age=1):
    return {
        "name": name,
        "status": {"issues": "complete", "pull_requests": "complete",
                   "workflow_runs": ci},
        "source_details": {
            "issues": checkpoint(issues_days, issues_age),
            "pull_requests": checkpoint(40, 1),
            "workflow_runs": checkpoint(ci_days, ci_age,
                                         error="Page cap" if ci == "partial" else None),
        },
    }


def test_strict_cohort_separates_source_cap_short_fallback_and_stale():
    audited = {"repositories": [
        repo("public/all"),
        repo("public/partial-ci", ci="partial"),
        repo("public/short-issues", issues_days=7),
        repo("public/stale-ci", ci_age=14),
    ]}
    out = strict_readiness(audited, now=NOW)
    assert out["tracked"] == 4
    assert out["verified_joint_28d"] == 1
    assert out["not_joint_verified"] == 3
    assert out["source_verified_28d"] == {
        "issues": 3, "pull_requests": 4, "workflow_runs": 2}
    blocker = {
        r["repository"]: r["unverified_sources"]
        for r in out["per_repository"]
    }
    assert blocker["public/partial-ci"][0]["reason"] == "api_page_cap_or_partial"
    assert blocker["public/short-issues"][0]["reason"] == "complete_short_window_only"
    assert blocker["public/stale-ci"][0]["reason"] == "stale_checkpoint"
    assert "UTC" not in out["as_of_utc"] or out["as_of_utc"].endswith("+00:00")


def test_verified_freshness_not_artificially_extended_to_24_hours():
    sample = {"repositories": [repo("a", ci_age=13)]}
    assert strict_readiness(sample, now=NOW)["verified_joint_28d"] == 0
    assert strict_readiness(sample, now=NOW, stale_hours=24)["verified_joint_28d"] == 1
    # The configured application and collector production default is twelve
    # hours; the audit never silently chooses the less stringent horizon.
    assert strict_readiness(sample, now=NOW)["stale_hours"] == 12


def test_unavailable_is_not_zero_or_verified():
    r = repo("missing")
    r["status"]["workflow_runs"] = "unavailable"
    r["source_details"]["workflow_runs"] = {}
    result = strict_readiness({"repositories":[r]}, now=NOW)
    assert result["verified_joint_28d"] == 0
    assert result["per_repository"][0]["unverified_sources"][0][
        "reason"] == "unavailable_or_failed"


def test_production_pipeline_exposes_actual_per_repo_triage_artifact():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] /
              ".github/workflows/public-snapshot.yml").read_text()
    assert "scripts/audit_coverage_readiness.py" in source
    assert "coverage-readiness.json" in source
