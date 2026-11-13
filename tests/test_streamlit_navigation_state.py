"""Real Streamlit AppTest navigation with an isolated two-repo SQLite test fixture.

This fixture never replaces the public GitHub source dataset.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_repository_selection_survives_cross_page_navigation(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from src.database.store import make_engine, init_db, session_factory
    from src.database.models import Repository

    db_path = tmp_path / "navigation.sqlite3"
    url = f"sqlite:///{db_path}"
    engine = make_engine(url)
    init_db(engine)
    with session_factory(engine)() as session:
        for idx, name in enumerate(("alpha", "beta"), 1):
            session.add(Repository(
                id=800 + idx, full_name=f"sample/{name}",
                name=name, owner="sample",
                url=f"https://github.com/sample/{name}",
                language="Python", category="Data & backend",
                selected=True, stars=idx,
            ))
        session.commit()
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", url)
    at = AppTest.from_file(str(ROOT / "streamlit_app.py"),
                           default_timeout=60).run()
    assert not at.exception, f"Dashboard failed: {at.exception}"

    def navigate(name):
        btn = next(b for b in at.sidebar.button if b.label == name)
        btn.click().run()
        assert not at.exception, f"{name} failed: {at.exception}"

    def repo(key):
        return next(x for x in at.selectbox if x.key == key)

    navigate("Explore repositories")
    repo("v2_details_repo").set_value("sample/beta").run()
    assert not at.exception, at.exception

    navigate("Open issues")
    assert repo("v2_issues_repo").value == "sample/beta"

    repo("v2_issues_repo").set_value("sample/alpha").run()
    assert not at.exception, at.exception
    navigate("Changes & reviews")
    assert repo("v2_pr_repo").value == "sample/alpha"

    navigate("Explore repositories")
    assert repo("v2_details_repo").value == "sample/alpha"
