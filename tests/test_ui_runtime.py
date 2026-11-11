"""Actual Streamlit AppTest checks (run on CI with Streamlit installed).

Uses an isolated EMPTY SQLite fixture, never demo records as live data.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("destination", [
    "◫  Overview", "▣  Project details", "☷  Issues & backlog",
    "⇄  Pull request review", "◎  CI/CD activity", "△  Risks & recommendations",
])
def test_dashboard_routes_render_without_live_data(tmp_path, monkeypatch, destination):
    streamlit = pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from src.database.store import make_engine, init_db
    path = tmp_path / "ui.sqlite3"
    engine = make_engine(f"sqlite:///{path}")
    init_db(engine)
    engine.dispose()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path}")
    # Each route is executed in a real Streamlit script runner, not in mocks.
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    assert not at.exception, f"Dashboard boot error: {at.exception}"
    at.sidebar.radio[0].set_value(destination).run()
    assert not at.exception, f"{destination}: {at.exception}"
