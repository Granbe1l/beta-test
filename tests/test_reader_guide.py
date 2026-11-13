"""Recruiter-facing definitions must be concise, reachable, and nonmisleading."""
from pathlib import Path

from src.ui.reader_guide import TERMS, NAV_HELP, HOW_TO_READ, guide_text

ROOT = Path(__file__).resolve().parents[1]


def test_glossary_is_plain_and_never_claims_data_as_delivery_sla():
    terms = dict(TERMS)
    assert set(terms) == {
        "Repository", "Issue", "Pull request (PR)", "CI/CD check",
        "Verified period", "Exploratory"}
    assert "not automatically overdue" in terms["Issue"]
    assert "not proof" in terms["CI/CD check"]
    assert "not a project-quality rating" in terms["Verified period"]
    assert "not a complete lifetime history" in terms["Verified period"]
    assert "cannot be counted as zero" in terms["Exploratory"]
    assert guide_text().count("**") == 12


def test_each_page_has_a_useful_non_technical_tooltip():
    source = (ROOT/"streamlit_app.py").read_text(encoding="utf-8")
    assert len(NAV_HELP) == 6
    for page in ("Dashboard", "Explore repositories", "Open issues",
                 "Changes & reviews", "Build activity", "Key findings"):
        assert page in NAV_HELP
        assert len(NAV_HELP[page]) < 120
        assert len(NAV_HELP[page]) > 30
    assert "help=NAV_HELP[label]" in source
    assert 'st.expander("Reading guide · 1 minute")' in source
    assert "for title, meaning in TERMS" in source
    assert "for instruction in HOW_TO_READ" in source
    assert "does not certify the full" in source
    assert len(HOW_TO_READ) == 3


def test_three_steps_are_actionable_not_fabricated_conclusions():
    joined = " ".join(HOW_TO_READ)
    assert "number of qualifying projects" in joined
    assert "measured finding" in joined
    assert "original GitHub record" in joined
    assert "decide what to check next" in joined
    assert "health score" in joined
