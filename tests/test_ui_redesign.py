"""UI view-model regression and non-Streamlit responsive style checks."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.ui.filters import filter_work_items, filter_pull_requests, filter_workflow_runs, issue_age_days, page_slice

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)


def issue(number, age, *, state="open", label="bug", title="Improve reporting"):
    created = NOW - timedelta(days=age)
    return {"number": number, "title": title, "state": state, "labels": [label],
            "created_at": created, "closed_at": NOW - timedelta(days=1) if state == "closed" else None}


def test_issue_register_filters_and_age_bands():
    records = [issue(1, 2), issue(2, 18, label="feature"), issue(3, 64), issue(4, 130)]
    assert [r["number"] for r in filter_work_items(records, state="Open", age="30–89 days", now=NOW)] == [3]
    assert [r["number"] for r in filter_work_items(records, label="feature", now=NOW)] == [2]
    assert [r["number"] for r in filter_work_items(records, search="4", now=NOW)] == [4]
    assert filter_work_items(records, search="nonexistent", now=NOW) == []


def test_closed_issue_lifetime_not_open_age():
    row = issue(8, 70, state="closed")
    assert issue_age_days(row, NOW) == 69


def test_pr_state_draft_and_sort():
    records = [
        {**issue(1, 30, title="Fix login"), "draft": True},
        {**issue(2, 4, title="Improve build"), "draft": False},
        {**issue(3, 18, state="closed", title="Fix build"), "draft": False},
    ]
    assert [r["number"] for r in filter_pull_requests(records, state="Open", draft="Draft only", now=NOW)] == [1]
    assert [r["number"] for r in filter_pull_requests(records, search="build", now=NOW)] == [2, 3]
    assert filter_pull_requests(records, sort="Longest open", now=NOW)[0]["number"] == 1


def test_ci_filters_and_pagination():
    runs = [{"workflow_name": "Test build", "branch": "main", "conclusion": "success", "created_at": NOW},
            {"workflow_name": "Deploy", "branch": "dev", "conclusion": "failure", "created_at": NOW-timedelta(days=1)}]
    assert len(filter_workflow_runs(runs, search="test", branch="main")) == 1
    assert len(filter_workflow_runs(runs, outcome="failure")) == 1
    assert page_slice(list(range(23)), 3, 10) == [20,21,22]


def test_six_view_navigation_and_purple_mobile_theme():
    app = (ROOT / "streamlit_app.py").read_text()
    page = (ROOT / "src/ui/pages.py").read_text()
    style = (ROOT / "src/ui/theme.py").read_text()
    config = (ROOT / ".streamlit/config.toml").read_text()
    for name in ("Dashboard", "Explore repositories", "Open issues", "Changes & reviews", "Build activity", "Key findings"):
        assert name in app
    assert '"Compare repositories"' in page
    assert '"Methodology & limitations"' in page
    assert '@media(max-width:700px)' in style
    assert 'prefers-reduced-motion' in style
    assert '#6F3FDF' in config
    assert 'No verified data' in style
    assert 'Insufficient Data' in page
    v2 = (ROOT / 'src/ui/dashboard_v2.py').read_text()
    v2_css = (ROOT / 'src/ui/theme_v2.py').read_text()
    assert 'observed_age_bands' in v2
    assert 'observed_outcomes' in v2
    assert '@media(max-width:700px)' in v2_css
    assert 'type="primary" if st.session_state["main_nav"] == label' in app
    assert 'st.radio(' not in app
    assert 'All displayed totals use retrieved records only' in v2
    assert 'portfolio_findings(reports, max_findings=max(limit, 10))' in v2
    assert 'comparable_observation_pair(chosen)' in v2
    assert 'checks_in_period(r["ci_rows"], days=period)' in v2
    assert 'Bounded source scans complete / tracked:' in v2
    trend = (ROOT / 'src/ui/trend_panels.py').read_text()
    assert 'trend_panel(chosen)' in v2
    assert 'coverage_progress(chosen)' in v2
    assert 'compare_two_repositories(reports)' in v2
    assert 'st.download_button(' in trend
    assert 'go.Scatter(' in trend
    assert 'Only a bounded collection is available' in trend
    assert 'Source completeness, periods and technical terms' in v2
    # Visual diversity must match analytic questions and real data contracts.
    assert 'go.Pie(' in v2  # part-to-whole
    assert 'go.Scatter(' in v2  # matched two-date comparison
    assert 'def _duration_columns' in v2  # PR distribution
    assert 'name="PR events"' in v2  # stacked source activity
    assert 'checks_in_period(rows, days=period)' in v2
    # A visual-first dashboard cannot make its primary line chart wait below
    # summary paragraphs, coverage ribbons, or a long glossary.
    overview = v2[v2.index('def overview('):v2.index('def project_details(')]
    assert overview.index('trend_panel(chosen)') < overview.index('Quick reading')
    assert overview.index('trend_panel(chosen)') < overview.index('_coverage_banner(chosen)')
    assert overview.index('trend_panel(chosen)') < overview.index('_findings_view(')
    assert '_finding_visual(f)' in v2
    assert 'st.metric(' in v2
    assert 'help=f.get("evidence")' in v2
    assert 'title="{esc(label)}: {esc(context)}"' in v2

    assert 'Show observed sample instead' in trend
    assert 'No repositories qualify for the verified' in trend
    assert 'd-trend-caveat' in trend
    assert 'disabled=not any_usable' in trend
    capture = (ROOT / 'scripts/capture_ui.py').read_text()
    assert 'capture_scrolling_main(' in capture
    assert 'desktop-dashboard-full.png' in capture
    assert 'mobile-dashboard-full.png' in capture
  # CI denominator



def test_no_hardcoded_example_kpis_as_live():
    app = (ROOT / "streamlit_app.py").read_text()
    page = (ROOT / "src/ui/pages.py").read_text()
    assert "no repository counts, charts or findings will be invented" in page
    assert "st.cache_data(ttl=600" in app
    assert "run_sync.py" not in app
