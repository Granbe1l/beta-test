"""P2.5: professional portfolio copy must be traceable and safe to reuse."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_recruiter_entrypoint_and_source_links_exist():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    card = ROOT / "docs/PORTFOLIO_CARD.md"
    assert card.is_file()
    assert "## Start here — 60-second reviewer tour" in readme
    assert "[one-page case study](docs/PORTFOLIO_CARD.md)" in readme
    assert "[CV-safe wording](docs/CV_EVIDENCE.md)" in readme
    assert "## What SQL is used for" in readme
    assert "scripts/sql_insights.py" in readme
    assert "src/ui/dashboard_v2.py" in readme
    for doc in ("docs/CV_EVIDENCE.md", "docs/PUBLIC_DEPLOYMENT.md",
                "docs/PORTFOLIO_CASE_STUDY.md"):
        assert (ROOT / doc).is_file()


def test_no_old_fixed_snapshot_counts_or_unverified_live_demo():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    cv = (ROOT / "docs/CV_EVIDENCE.md").read_text(encoding="utf-8")
    card = (ROOT / "docs/PORTFOLIO_CARD.md").read_text(encoding="utf-8")
    assert "11,652 observed Issue records" not in cv
    assert "87,122 observed" not in cv
    assert "python scripts/cv_evidence.py" in cv
    assert "query-count reduction" in cv
    assert "Live demo:" in readme
    assert "**not yet publicly verified**" in readme
    assert "Public hosted Streamlit URL: not yet verified" in card
    assert "376 to 6" in readme
    assert "not a claimed browser speedup" in readme


def test_case_study_does_not_invent_recruiter_validation():
    card = (ROOT / "docs/PORTFOLIO_CARD.md").read_text(encoding="utf-8")
    case = (ROOT / "docs/PORTFOLIO_CASE_STUDY.md").read_text(encoding="utf-8")
    assert "source-linked" in card
    assert "not a claimed" in card
    assert "three genuinely successful scheduled collection events" in case.lower() or (
        "Three genuinely successful scheduled collection events" in case)
    assert "A formal human nontechnical participant study has not been performed" in case
    for number in ("15", "16", "17", "18"):
        assert f"https://github.com/Granbe1l/beta-test/pull/{number}" in case
