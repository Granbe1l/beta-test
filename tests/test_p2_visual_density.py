"""P2.3 grounded layout checks: no data deletion or concealed caveats."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_page_reduces_intro_copy_without_removing_evidence():
    app = (ROOT/"streamlit_app.py").read_text(encoding="utf-8")
    dashboard = (ROOT/"src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    assert "**ANALYSIS COHORT:**" in app
    assert "**PUBLIC GITHUB SNAPSHOT:**" in app
    assert "Unverified projects are not counted as inactive" in app
    assert "read-only, not a live connection" in app
    assert "Evidence coverage · verified vs exploratory" in dashboard
    assert "Evidence-ready cohorts within this selection" in dashboard
    assert "for 28 days" in dashboard
    assert "remain accessible as explicitly exploratory observations" in dashboard
    assert dashboard.index('with st.expander("Evidence coverage') < dashboard.index('_section("01 / Activity over time"')


def test_sidebar_credit_is_after_scope_and_native_toolbar_does_not_cover_charts():
    app = (ROOT/"streamlit_app.py").read_text(encoding="utf-8")
    assert app.index('st.caption("ANALYSIS EVIDENCE SCOPE")') < app.index(
        '<div class="side-footer">')
    dashboard = (ROOT/"src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    trends = (ROOT/"src/ui/trend_panels.py").read_text(encoding="utf-8")
    assert '"displayModeBar": False' in dashboard
    assert '"displayModeBar":False' in trends
    assert 'st.plotly_chart(' in dashboard
    assert 'st.plotly_chart(' in trends
