"""Source-backed reasoning remains available while mobile finding cards stay concise."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/ui/dashboard_v2.py"


def test_review_threshold_is_in_details_not_repeated_on_initial_card():
    content = SOURCE.read_text(encoding="utf-8")
    body = content.split("def _findings_view(", 1)[1].split(
        "def _weekly(", 1)[0]
    details = body.index('with st.expander("Evidence and limitations")')
    assert body.index('st.caption("Why inspect: " + plan["trigger"])') > details
    assert 'st.caption(f\'Next check: {f["review"]}\')' in body
    assert 'st.link_button(action["button"], action["url"]' in body
    assert 'st.caption(action["disclosure"])' in body


def test_dashboard_hero_clarifies_github_without_long_buzzwords():
    content = SOURCE.read_text(encoding="utf-8")
    intro = content.split("def overview(", 1)[1].split(
        "def project_details(", 1)[0]
    assert "<h1>GitHub activity at a glance.</h1>" in intro
    assert "original source links" in intro
    assert "Public development signals, not client deadlines." in intro
