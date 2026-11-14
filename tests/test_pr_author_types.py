"""Actual source-reported PR account types are never guessed or backfilled."""
from sqlalchemy import inspect
from src.analytics.pr_authors import pr_account_evidence, pr_account_type_counts
from src.collectors.normalize import pull_request
from src.database.store import init_db, make_engine


def raw(user):
    return {
        "id": 42, "number": 4,
        "html_url": "https://github.com/example/project/pull/4",
        "state": "open", "created_at": "2026-11-12T00:00:00Z",
        "updated_at": "2026-11-13T00:00:00Z", "user": user,
    }


def test_known_github_account_types_and_missing_types_preserved():
    assert pull_request(raw({"type": "Bot"}), 1)["author_type"] == "Bot"
    assert pull_request(raw({"type": "User"}), 1)["author_type"] == "User"
    assert pull_request(raw({"type": "Organization"}), 1)["author_type"] == "Organization"
    assert pull_request(raw({}), 1)["author_type"] is None
    assert pull_request(raw(None), 1)["author_type"] is None
    assert pull_request(raw({"type": "untrusted"}), 1)["author_type"] is None


def test_old_snapshots_without_author_type_remain_unknown():
    found = [{"author_type": "Bot"}, {"author_type": "User"},
             {"author_type": "Organization"}, {}]
    data = pr_account_evidence(found)
    assert data["counts"] == {
        "GitHub User-type account": 1,
        "GitHub Bot-type account": 1,
        "Other / unknown": 2,
    }
    assert data["observed"] == 4
    assert data["known"] == 2
    assert data["coverage"] == 50.0
    assert "does not prove a human" in data["scope"]
    assert pr_account_evidence([])["coverage"] is None


def test_existing_sqlite_schema_receives_additive_author_type_column():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE pull_requests (id INTEGER PRIMARY KEY)")
        init_db(engine)
        init_db(engine)  # migration is idempotent
        with engine.connect() as connection:
            columns = {
                item["name"] for item in inspect(connection).get_columns("pull_requests")
            }
        assert "author_type" in columns
    finally:
        engine.dispose()
