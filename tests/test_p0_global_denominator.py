"""P0.1: denominator never changes when the UI filters a 75-repo dataset."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.ui.reviewer_cohort import decision_brief_cohort

NOW = datetime(2026, 11, 13, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def _repo(name, eligible_days=0):
    status = "complete" if eligible_days else "partial"
    coverage = ({
        key: {"coverage_start": NOW-timedelta(days=eligible_days),
              "last_success_at": NOW-timedelta(minutes=30)}
        for key in ("issues", "pull_requests", "workflow_runs")
    } if eligible_days else {})
    return {"repository": {"full_name": f"public/{name}"},
            "status": {k: status for k in ("issues", "pull_requests", "workflow_runs")},
            "coverage": coverage}


def test_reviewer_brief_always_uses_global_75_repos_not_22_in_current_view():
    all_reports = ([_repo(f"verified-{i}", eligible_days=40) for i in range(22)]
                   + [_repo(f"partial-{i}") for i in range(53)])
    assert decision_brief_cohort(all_reports, all_reports[:22], NOW) == {
        "tracked": 75, "verified_28d": 22, "in_view": 22}
    assert decision_brief_cohort(all_reports, all_reports[:1], NOW) == {
        "tracked": 75, "verified_28d": 22, "in_view": 1}
    assert decision_brief_cohort(all_reports, all_reports, NOW) == {
        "tracked": 75, "verified_28d": 22, "in_view": 75}


def test_7day_verified_does_not_inflate_global_28day_count():
    reports = [_repo("both", eligible_days=40),
               _repo("seven", eligible_days=8),
               _repo("partial")]
    assert decision_brief_cohort(reports, reports[:2], NOW) == {
        "tracked": 3, "verified_28d": 1, "in_view": 2}


def test_app_passes_original_population_to_overview():
    app = (ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    ui = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert "overview(reports, selection, all_reports=all_reports)" in app
    assert "global_cohort = all_reports if all_reports is not None else reports" in ui
    assert "cohort = decision_brief_cohort(global_cohort, chosen)" in ui
    assert 'cohort["verified_28d"]' in ui and 'cohort["tracked"]' in ui
    assert "This current filtered view contains" in ui
    assert "entire = evidence_readiness(reports)" not in ui
