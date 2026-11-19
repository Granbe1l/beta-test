"""Real GitHub IDs exceed PostgreSQL int32; SQLite must keep working too."""
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from src.database.models import Base, Issue
from src.database.store import write_records
from src.collectors.normalize import issue
from .conftest import issue_payload


def test_external_identifiers_fit_postgres_bigint():
    external_pks = {"repositories", "issues", "pull_requests", "workflow_runs"}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.name == "repo_id" or (table.name in external_pks and column.name == "id"):
                assert column.type.compile(dialect=postgresql.dialect()) == "BIGINT", (
                    table.name, column.name, str(CreateTable(table).compile(dialect=postgresql.dialect())))


def test_large_external_issue_id_roundtrips_sqlite_without_truncation(db):
    payload = issue_payload()
    payload["id"] = 6456404873
    write_records(db, "issues", [issue(payload, 101)])
    db.commit()
    assert db.scalar(select(Issue.id)) == 6456404873
