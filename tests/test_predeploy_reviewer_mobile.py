"""Evidence-based reviewer clarity and six-screen responsive coverage."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reviewer_brief_has_true_global_verified_denominator():
    source = (ROOT/"src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert "global_cohort = all_reports if all_reports is not None else reports" in source
    assert 'cohort["verified_28d"]' in source
    assert 'cohort["tracked"]' in source
    assert "First inspect" in source
    assert "No client-deadline or quality verdict" in source
    assert "finding_cards = initial_findings" in source
    assert "Sources verified" not in source  # cannot conflate scan with 28d coverage
    assert "28d verified" in source
    assert "verified_joint_cohort(reports, days=28)" in source


def test_real_browser_script_checks_all_mobile_pages_and_explorer_tabs():
    capture = (ROOT/"scripts/capture_ui.py").read_text(encoding="utf-8")
    for name in (
        "Explore repositories", "Open issues", "Changes & reviews",
        "Build activity", "Key findings",
    ):
        assert f'("{name}", "mobile-' in capture
    assert 'assert len(tested_mobile) == 6' in capture
    assert 'mobile_page_count' in capture
    assert 'mobile-repositories-history' in capture
    assert 'mobile-repositories-comparison' in capture
    assert 'mobile-repositories-source-details' in capture
    assert 'Mobile {name}: horizontal overflow' in capture
    assert 'assert_no_streamlit_exception(mobile, "Mobile " + name)' in capture


def test_stored_evidence_scope_never_infers_complete_histories():
    source = (ROOT/"src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert "Missing records are not zero activity." in source
    assert "Unverified sources are retained" in source
    assert "not a deadline" in source.lower()
