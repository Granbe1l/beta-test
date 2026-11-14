"""Local accessibility and performance probes are checks, not certification."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_kpi_readable_names_have_values_context_and_no_icon_noise():
    code = (ROOT / "src/ui/dashboard_v2.py").read_text(encoding="utf-8")
    section = code.split("def _kpis(cards):", 1)[1].split(
        "def _chart(", 1)[0]
    assert 'role="group"' in section
    assert 'aria-label="{esc(label)}: {esc(value)}. {esc(context)}"' in section
    assert 'aria-hidden="true"' in section


def test_both_dark_sidebar_and_light_surface_have_visible_focus():
    css = (ROOT / "src/ui/theme_v2.py").read_text(encoding="utf-8")
    assert ".stButton button:focus-visible" in css
    assert ".stLinkButton a:focus-visible" in css
    assert '[data-testid="stTabs"] button:focus-visible' in css
    assert '[data-testid="stSidebar"] button:focus-visible' in css
    assert "outline:3px solid #563590!important;" in css
    assert "outline:3px solid #DCC7FF!important;" in css
    assert "min-height:44px!important;" in css


def test_local_timing_is_observed_not_fabricated_hosting_benchmark():
    browser = (ROOT / "scripts/capture_ui.py").read_text(encoding="utf-8")
    assert "desktop_started = time.perf_counter()" in browser
    assert "mobile_started = time.perf_counter()" in browser
    assert '"local_first_chart_ms"' in browser
    assert "local GitHub Actions Chrome/Streamlit only, not hosted Cloud" in browser
    assert 'wait_for(timeout=45000)' in browser
