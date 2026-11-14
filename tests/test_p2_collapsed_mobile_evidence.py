"""P2: reduce default mobile overview height while preserving traceable reviews."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lead_finding_and_primary_chart_stay_visible_before_collapsed_checks():
    ui = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    overview = ui.split("def overview(", 1)[1].split(
        "def project_details(", 1)[0]
    for label in ("What should we inspect?", "Open an original GitHub record",
                  "trend_panel(chosen)",
                  'st.expander("02 / Inspect all evidence-backed checks", expanded=False)'):
        assert label in overview
    assert overview.index("What should we inspect?") < overview.index(
        "trend_panel(chosen)")
    assert overview.index("trend_panel(chosen)") < overview.index(
        'st.expander("02 / Inspect all evidence-backed checks"')
    assert overview.index('st.expander("02 / Inspect all evidence-backed checks"') < overview.index(
        "_findings_view(finding_cards)")
    assert overview.index("_findings_view(finding_cards)") < overview.index(
        'if st.toggle(')


def test_full_evidence_remains_in_source_and_browser_expands_it():
    capture = (ROOT / "scripts/capture_ui.py").read_text(encoding="utf-8")
    ui = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert 'desktop.get_by_text("CHECK 1/", exact=False).first.wait_for' in capture
    assert "Verified collapsed evidence details expand" in capture
    assert 'st.link_button(action["button"], action["url"]' in ui
    assert 'with st.expander("Evidence and limitations")' in ui
