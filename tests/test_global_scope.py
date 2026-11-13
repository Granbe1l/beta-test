"""Regression: verified-first semantics must apply to all six UI pages."""
from pathlib import Path

from src.ui.observed import verified_joint_cohort, evidence_readiness


def test_main_entrypoint_scopes_all_pages_from_one_global_verified_cohort():
    source = (Path(__file__).resolve().parents[1] /
              "streamlit_app.py").read_text(encoding="utf-8")
    assert "Verified · 28 days" in source
    assert "Verified · 7 days" in source
    assert "All tracked · exploratory" in source
    assert "verified_28 = verified_joint_cohort(all_reports, days=28)" in source
    assert "verified_7 = verified_joint_cohort(all_reports, days=7)" in source
    assert "reports = verified_28" in source
    assert "reports = verified_7" in source
    assert "reports = all_reports" in source
    assert "risks_recommendations(reports, selection)" in source
    assert "MENU[nav](reports)" in source
    assert "status = status_for(all_reports)" in source


def test_exploratory_is_opt_in_without_erasing_repository_data():
    entry = (Path(__file__).resolve().parents[1] /
             "streamlit_app.py").read_text(encoding="utf-8")
    assert "Unverified sources are retained" in entry
    assert "Exploratory source scope:" in entry
    assert "samples, not full " in entry
    assert "project totals or confirmed backlog changes" in entry
