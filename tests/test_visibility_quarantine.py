from sqlalchemy import select, func
import pytest

from src.collectors.sync import synchronize, refresh_repo_metadata
from src.collectors.client import PageResult
from src.database.models import Repository, Issue, SyncCheckpoint
from src.analytics.read import load_reports
from src.analytics.snapshot import export_snapshot
from .conftest import NOW


class VisibilityClient:
    def __init__(self, metadata):
        self.metadata = metadata
        self.calls = []

    def get(self, *args, **kwargs):
        if isinstance(self.metadata, Exception):
            raise self.metadata
        return self.metadata, None

    def paginate(self, path, *args, **kwargs):
        self.calls.append(path)
        return PageResult([], 1, True, False, False)


@pytest.mark.parametrize('visibility', [
    {'private': True}, {'visibility': 'private'}, {'visibility': 'internal'},
])
def test_private_transition_blocks_collection_and_export_preserves_history(db, cfg, tmp_path, visibility):
    db.add(Issue(id=4001, repo_id=101, number=1, title='Previously public',
                 url='https://github.com/sample/project/issues/1', state='closed',
                 created_at=NOW, updated_at=NOW))
    db.commit()
    client = VisibilityClient({'id': 101, **visibility})
    result = synchronize(db, client, cfg, run_at=NOW, audit_open_backlog=True)
    assert client.calls == []
    assert all(row['status'] == 'failed' for row in result)
    assert db.get(Repository, 101).selected
    assert db.scalar(select(func.count()).select_from(Issue)) == 1
    output = tmp_path / 'public.gz'
    output.write_bytes(b'previous published snapshot')
    with pytest.raises(ValueError, match='visibility'):
        export_snapshot(output, load_reports(db, now=NOW), None, generated_at=NOW)
    assert output.read_bytes() == b'previous published snapshot'


@pytest.mark.parametrize('retry', [RuntimeError('metadata unavailable'), {'id': 101}])
def test_private_quarantine_survives_unknown_visibility(db, cfg, retry):
    synchronize(db, VisibilityClient({'id':101, 'private':True}), cfg, run_at=NOW)
    client = VisibilityClient(retry)
    synchronize(db, client, cfg, run_at=NOW, audit_open_backlog=True)
    assert client.calls == []


def test_positive_public_revalidation_releases_quarantine(db, cfg, tmp_path):
    synchronize(db, VisibilityClient({'id':101, 'private':True}), cfg, run_at=NOW)
    repo = db.get(Repository, 101)
    assert refresh_repo_metadata(db, VisibilityClient({'id':101, 'private':False, 'visibility':'public'}), repo)
    assert db.get(SyncCheckpoint, (101, 'public_visibility')).status == 'complete'
    export_snapshot(tmp_path/'public.gz', load_reports(db, now=NOW), None, generated_at=NOW)


@pytest.mark.parametrize('metadata', [RuntimeError('metadata unavailable'), {'id':101}])
def test_fresh_runner_without_quarantine_marker_requires_public_proof(db, cfg, metadata):
    # A rejected export cannot carry quarantine into the next ephemeral
    # runner. Restoring an older snapshot must not authorize unknown visibility.
    assert db.get(SyncCheckpoint, (101, 'public_visibility')) is None
    client = VisibilityClient(metadata)
    result = synchronize(db, client, cfg, run_at=NOW, audit_open_backlog=True)
    assert client.calls == []
    assert all(r['status'] == 'failed' for r in result)


def test_rejected_export_then_restore_old_snapshot_cannot_bypass_visibility(db, cfg, tmp_path):
    from src.database.store import make_engine, init_db, session_factory
    from src.collectors.restore import hydrate_snapshot
    repo = db.get(Repository, 101)
    refresh_repo_metadata(db, VisibilityClient({'id':101, 'private':False}), repo, now=NOW)
    old = tmp_path/'old-public.gz'
    export_snapshot(old, load_reports(db, now=NOW), {'id':1}, generated_at=NOW)
    synchronize(db, VisibilityClient({'id':101, 'private':True}), cfg, run_at=NOW)
    with pytest.raises(ValueError, match='visibility'):
        export_snapshot(old, load_reports(db, now=NOW), {'id':1}, generated_at=NOW)
    engine = make_engine('sqlite:///:memory:')
    init_db(engine)
    try:
        with session_factory(engine)() as restored:
            assert hydrate_snapshot(restored, old)['restored'] == 1
            client = VisibilityClient(RuntimeError('metadata outage'))
            synchronize(restored, client, cfg, run_at=NOW, audit_open_backlog=True)
            assert client.calls == []
            with pytest.raises(ValueError, match='visibility'):
                export_snapshot(tmp_path/'new.gz', load_reports(restored, now=NOW), {'id':1}, generated_at=NOW)
            assert restored.get(Repository, 101).selected
    finally:
        engine.dispose()
