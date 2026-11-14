"""Guard the first-mobile-screen order without diluting data limitations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_reviewer_summary_is_placed_above_optional_filters_and_has_early_evidence():
    body = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8").split(
        "def overview(reports,", 1)[1].split("def project_details(reports):", 1)[0]
    assert body.index("lead_position = st.container()") < body.index(
        'chosen = _scope(reports, "v2_scope")')
    assert body.index("with lead_position:") < body.index(
        'st.caption("Additional observed dataset totals')
    # The original-record action now belongs to the finding, not the
    # secondary evidence-denominator column, and remains data gated.
    assert body.index('st.link_button(label, action["url"]') < body.index(
        'with st.expander("Why this finding merits a closer look")')
    assert body.index("What should we inspect?") < body.index(
        "What happened in the last 7 days?")
    assert body.index('How complete is the evidence?') > body.index(
        'What happened in the last 7 days?')


def test_gallery_screenshots_reset_scroll_and_hover_before_capture():
    code = (ROOT / "scripts/capture_ui.py").read_text(encoding="utf-8")
    assert 'desktop.mouse.move(1434, 48)' in code
    assert 'window.scrollTo(0, 0)' in code
    assert code.index('desktop.mouse.move(1434, 48)') < code.index(
        'desktop.screenshot(path=str(OUT / file), full_page=False)')
