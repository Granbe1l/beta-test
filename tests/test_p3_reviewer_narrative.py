"""P3: portfolio entry points describe current UI, verified data and limits."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_recruiter_links_actual_source_cases_and_mobile_evidence():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for value in (
        "docs/EVIDENCE_CASE_STUDIES.md",
        "5,067 to 3,180 pixels",
        "**37% shorter**",
        "technical appendix",
        "75-repository figures describe archived experiments",
        "not website speed or a human comprehension score",
    ):
        assert value in readme


def test_current_case_study_does_not_describe_obsolete_three_column_layout():
    doc = (ROOT / "docs/PORTFOLIO_CASE_STUDY.md").read_text(
        encoding="utf-8")
    assert "two-column Quick reading" in doc
    assert "three-column Quick reading" not in doc
    assert "EVIDENCE_CASE_STUDIES.md" in doc
    assert "No client deadline" in doc


def test_cv_example_does_not_invent_real_maintainer_action():
    cv = (ROOT / "docs/CV_EVIDENCE.md").read_text(encoding="utf-8")
    assert "conditional source-backed case walkthroughs" in cv
    assert "does **not**" in cv
    assert "EVIDENCE_CASE_STUDIES.md" in cv
