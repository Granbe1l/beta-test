"""P1 reviewer-first UI remains evidence-gated and mobile-friendly."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_first_screen_has_one_decision_path_before_charts():
    code = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    overview = code.split("def overview(reports,", 1)[1].split(
        "def project_details(reports):", 1)[0]
    assert overview.index('Quick reading') < overview.index('trend_panel(chosen)')
    # Recruiter-first on mobile: actual finding precedes descriptive KPI cards.
    assert overview.index('What should we inspect?') < overview.index(
        '("Projects in analysis"')
    assert overview.index('("Projects pushed · 7d"') < overview.index(
        'trend_panel(chosen)')
    assert overview.index('What should we inspect?') < overview.index(
        'What happened in the last 7 days?')
    assert overview.index('What should we inspect?') < overview.index(
        'How complete is the evidence?')
    assert overview.index('trend_panel(chosen)') < overview.index(
        '_findings_view(finding_cards)')
    assert overview.count('brief = executive_brief(chosen, findings=finding_cards)') == 1
    assert 'Open an original GitHub record' in overview
    assert 'Open GitHub source listing' in overview
    assert 'action["record_level"]' in overview


def test_full_open_issue_inventory_is_independently_gated():
    code = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    start = code.index("def overview(")
    end = code.index("def project_details(")
    body = code[start:end]
    assert 'r.get("open_backlog_status") == "complete"' in body
    assert 'independently verified and fresh' in body
    assert 'not the same' in body and '28-day event window' in body
    assert "Missing records are not zero activity." in body


def test_supporting_charts_are_lazy_without_removing_original_evidence():
    code = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    body = code.split("def overview(", 1)[1].split("def project_details(", 1)[0]
    gate = body.index('if st.toggle(')
    assert 'key="overview_supporting_charts"' in body
    assert gate < body.index('_section("03 / Delivery activity"')
    assert gate < body.index('_matched_snapshot_chart(chosen)')
    assert gate < body.index('_coverage_details(chosen)')
    # Baseline daily chart and source-linked review checks must always load.
    assert body.index('trend_panel(chosen)') < gate
    assert body.index('_findings_view(finding_cards)') < gate
    browser = (ROOT / "scripts/capture_ui.py").read_text(encoding="utf-8")
    assert 'deep.click(timeout=12000)' in browser
    assert '"04 / Matched snapshot change"' in browser
    assert 'state="detached"' in browser
