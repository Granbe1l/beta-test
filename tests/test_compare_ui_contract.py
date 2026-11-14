"""Single comparison tab preserves 28-day verified evidence boundaries."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_two_project_comparison_uses_verified_28_day_metrics():
    source = (ROOT / "src/ui/trend_panels.py").read_text(encoding="utf-8")
    section = source.split("def compare_two_repositories(reports):", 1)[1]
    assert "comparison_rows(chosen, days=28)" in section
    assert "PRs merged · 28-day verified window" in section
    assert "Completed checks · 28-day verified window" in section
    assert "30+ · full-inventory share" in section
    assert '"Merged PRs · 90 days (retrieved)"' not in section
    assert "not zero activity" in section


def test_explorer_combines_compare_tabs_and_export_is_read_only():
    source = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    section = source.split("def project_details(reports):", 1)[1].split(
        "def issues_backlog(reports):", 1)[0]
    assert 'a, compare_tab, c = st.tabs(["Activity history", "Compare projects",' in section
    assert 'with compare_tab:' in section
    assert "compare_two_repositories(reports)" in section
    assert "comparison(reports, embedded=True)" in section
    assert '"Compare two projects"' not in section
    inspector = (ROOT / "src/ui/repo_lookup.py").read_text(encoding="utf-8")
    assert "Download this inspection (CSV)" in inspector
    assert "inspection_csv(data, analysis)" in inspector
